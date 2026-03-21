from __future__ import annotations

import json
import logging
from typing import List, Optional

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

    try:
        prompts = await optimize_prompts(request.prompt, request.count)
        return JSONResponse(content={"prompts": prompts})
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
