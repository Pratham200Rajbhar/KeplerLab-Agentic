from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse

from app.services.auth import get_current_user
from app.services.material_service import filter_completed_material_ids
from app.db.prisma_client import prisma
from app.services.chat_v2.schemas import (
    ChatRequest,
    BlockFollowupRequest,
    SuggestionRequest,
    EmptyStateSuggestionRequest,
    CreateSessionRequest,
    SourceSelectionRequest,
    OptimizePromptsRequest,
)
from app.services.chat_v2.service import (
    chat_stream,
    get_history,
    clear_history,
    get_sessions,
    create_session,
    delete_session,
    block_followup_stream,
    get_suggestions,
    get_empty_state_suggestions,
)
from app.services.chat_v2.streaming import SSE_HEADERS
from app.services.chat_v2 import message_store
from app.routes.utils import require_material

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


async def _require_notebook_access(notebook_id: str, user_id: str) -> None:
    notebook = await prisma.notebook.find_first(
        where={"id": notebook_id, "userId": user_id}
    )
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")


def _dedupe_ids(ids: List[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for mid in ids:
        if mid in seen:
            continue
        seen.add(mid)
        ordered.append(mid)
    return ordered

@router.post("")
async def chat_endpoint(
    request: ChatRequest,
    current_user=Depends(get_current_user),
):
    ids = request.material_ids or ([request.material_id] if request.material_id else [])

    if ids:
        for mid in ids:
            material = await require_material(mid, current_user.id)
            if material.notebookId and material.notebookId != request.notebook_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Material {mid} does not belong to the current notebook.",
                )
        ids = await filter_completed_material_ids(ids, str(current_user.id))
        if not ids:
            raise HTTPException(
                status_code=400,
                detail=(
                    "None of the selected materials have finished processing yet. "
                    "Please wait for their status to reach 'completed' before chatting."
                ),
            )

    session_id = request.session_id
    if not session_id:
        title = request.message[:30] + ("..." if len(request.message) > 30 else "")
        session_id = await message_store.ensure_session(
            request.notebook_id, str(current_user.id), None, title
        )
    else:
        await message_store.ensure_session(
            request.notebook_id, str(current_user.id), session_id, request.message
        )

    try:
        return StreamingResponse(
            chat_stream(
                message=request.message,
                notebook_id=request.notebook_id,
                user_id=str(current_user.id),
                session_id=session_id,
                material_ids=ids,
                intent_override=request.intent_override,
            ),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Chat failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to generate response")

@router.post("/block-followup")
async def block_followup(
    request: BlockFollowupRequest,
    current_user=Depends(get_current_user),
):
    parent_block = await prisma.responseblock.find_unique(
        where={"id": request.block_id},
        include={"chatMessage": {"include": {"notebook": True}}},
    )
    if not parent_block or not parent_block.chatMessage:
        raise HTTPException(status_code=404, detail="Block not found")
    notebook = parent_block.chatMessage.notebook
    if not notebook or str(notebook.userId) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    async def generate():
        accumulated: List[str] = []
        try:
            async for text_chunk in block_followup_stream(
                block_id=request.block_id,
                action=request.action,
                question=request.question,
            ):
                accumulated.append(text_chunk)
                yield f"event: token\ndata: {json.dumps({'content': text_chunk})}\n\n"

            full_response = "".join(accumulated)
            if full_response.strip():
                try:
                    block = await prisma.responseblock.find_unique(
                        where={"id": request.block_id}
                    )
                    if block:
                        max_block = await prisma.responseblock.find_first(
                            where={"chatMessageId": block.chatMessageId},
                            order={"blockIndex": "desc"},
                        )
                        next_idx = (max_block.blockIndex + 1) if max_block else 0
                        prefix = f"[{request.action}:{request.block_id}{f':{request.selection}' if request.selection else ''}]"
                        await prisma.responseblock.create(
                            data={
                                "chatMessageId": block.chatMessageId,
                                "blockIndex": next_idx,
                                "text": f"{prefix} {full_response}",
                            }
                        )
                except Exception as persist_err:
                    logger.warning("Failed to persist block followup: %s", persist_err)

            yield f"event: done\ndata: {{}}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream", headers=SSE_HEADERS)

@router.post("/optimize-prompts")
async def optimize_prompts_endpoint(
    request: OptimizePromptsRequest,
    current_user=Depends(get_current_user),
):
    from app.services.chat_v2.prompt_optimizer import optimize_prompts
    from app.routes.utils import require_material

    context_text = ""
    if request.material_ids:
        materials_text = []
        for mid in request.material_ids:
            try:
                material = await require_material(mid, str(current_user.id))
                if material.originalText:
                    materials_text.append(f"--- Document: {material.title} ---\n{material.originalText[:15000]}")
            except Exception as e:
                logger.warning("Could not load material %s for prompt optimizer: %s", mid, e)
        context_text = "\n\n".join(materials_text)

    try:
        prompts = await optimize_prompts(request.prompt, request.count, context_text)
        return JSONResponse(content={"prompts": prompts})
    except ValueError as e:
        logger.warning("Prompt optimization produced no usable model output: %s", e)
        return JSONResponse(content={"prompts": []})
    except Exception as e:
        logger.error("Prompt optimization failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to optimize prompts")

@router.post("/suggestions")
async def suggestions_endpoint(
    request: SuggestionRequest,
    current_user=Depends(get_current_user),
):
    suggestions = await get_suggestions(
        request.partial_input, request.notebook_id, str(current_user.id)
    )
    return JSONResponse(content={"suggestions": suggestions})

@router.post("/empty-suggestions")
async def empty_suggestions_endpoint(
    request: EmptyStateSuggestionRequest,
    current_user=Depends(get_current_user),
):
    result = await get_empty_state_suggestions(
        request.material_ids, str(current_user.id)
    )
    return JSONResponse(content=result)


@router.get("/source-selection/{notebook_id}")
async def get_source_selection_endpoint(
    notebook_id: str,
    current_user=Depends(get_current_user),
):
    user_id = str(current_user.id)
    await _require_notebook_access(notebook_id, user_id)

    pref = await prisma.notebooksourceselection.find_first(
        where={"notebookId": notebook_id, "userId": user_id}
    )
    material_ids = list(pref.materialIds or []) if pref else []

    if material_ids:
        valid_materials = await prisma.material.find_many(
            where={
                "id": {"in": material_ids},
                "userId": user_id,
                "notebookId": notebook_id,
            }
        )
        valid_set = {str(m.id) for m in valid_materials}
        material_ids = [mid for mid in material_ids if mid in valid_set]

    return JSONResponse(
        content={"notebook_id": notebook_id, "material_ids": material_ids}
    )


@router.put("/source-selection")
async def save_source_selection_endpoint(
    request: SourceSelectionRequest,
    current_user=Depends(get_current_user),
):
    user_id = str(current_user.id)
    notebook_id = request.notebook_id
    await _require_notebook_access(notebook_id, user_id)

    requested_ids = _dedupe_ids([str(mid) for mid in (request.material_ids or []) if mid])
    sanitized_ids: List[str] = []

    if requested_ids:
        valid_materials = await prisma.material.find_many(
            where={
                "id": {"in": requested_ids},
                "userId": user_id,
                "notebookId": notebook_id,
            }
        )
        valid_set = {str(m.id) for m in valid_materials}
        sanitized_ids = [mid for mid in requested_ids if mid in valid_set]

    existing = await prisma.notebooksourceselection.find_first(
        where={"notebookId": notebook_id, "userId": user_id}
    )
    if existing:
        await prisma.notebooksourceselection.update(
            where={"id": str(existing.id)},
            data={"materialIds": sanitized_ids},
        )
    else:
        await prisma.notebooksourceselection.create(
            data={
                "notebookId": notebook_id,
                "userId": user_id,
                "materialIds": sanitized_ids,
            }
        )

    return JSONResponse(
        content={"notebook_id": notebook_id, "material_ids": sanitized_ids}
    )

@router.get("/history/{notebook_id}")
async def get_notebook_chat_history(
    notebook_id: str,
    session_id: Optional[str] = Query(None, description="Optional Chat Session ID"),
    current_user=Depends(get_current_user),
):
    return await get_history(notebook_id, str(current_user.id), session_id)

@router.delete("/history/{notebook_id}")
async def clear_notebook_chat(
    notebook_id: str,
    session_id: Optional[str] = Query(None, description="Optional Chat Session ID"),
    current_user=Depends(get_current_user),
):
    await clear_history(notebook_id, str(current_user.id), session_id)
    return {"cleared": True}

@router.get("/sessions/{notebook_id}")
async def get_chat_sessions_endpoint(
    notebook_id: str,
    current_user=Depends(get_current_user),
):
    sessions = await get_sessions(notebook_id, str(current_user.id))
    return JSONResponse(content={"sessions": sessions})

@router.post("/sessions")
async def create_chat_session_endpoint(
    request: CreateSessionRequest,
    current_user=Depends(get_current_user),
):
    session_id = await create_session(
        notebook_id=request.notebook_id,
        user_id=str(current_user.id),
        title=request.title,
    )
    return JSONResponse(content={"session_id": session_id})

@router.delete("/sessions/{session_id}")
async def delete_chat_session_endpoint(
    session_id: str,
    current_user=Depends(get_current_user),
):
    success = await delete_session(session_id, str(current_user.id))
    if not success:
        raise HTTPException(status_code=404, detail="Session not found or could not be deleted")
    return {"deleted": True}

@router.delete("/message/{message_id}")
async def delete_chat_message_endpoint(
    message_id: str,
    current_user=Depends(get_current_user),
):
    from app.services.chat_v2.service import delete_message
    success = await delete_message(message_id, str(current_user.id))
    if not success:
        raise HTTPException(status_code=404, detail="Message not found or could not be deleted")
    return {"deleted": True}

@router.patch("/message/{message_id}")
async def update_chat_message_endpoint(
    message_id: str,
    request: Dict[str, str],
    current_user=Depends(get_current_user),
):
    from app.services.chat_v2.service import update_message
    content = request.get("content")
    if not content:
        raise HTTPException(status_code=400, detail="Content is required")
    success = await update_message(message_id, str(current_user.id), content)
    if not success:
        raise HTTPException(status_code=404, detail="Message not found or could not be updated")
    return {"updated": True}
