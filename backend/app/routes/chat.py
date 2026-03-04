"""Chat route — Direct-routed conversation with materials.

Routing is ALWAYS set explicitly by the frontend slash command.
The backend NEVER calls an LLM to guess or classify intent.

Routing logic (strict, no inference):
  - intent_override == "AGENT"          → agentic loop (Section 5)
  - intent_override == "WEB_RESEARCH"   → deep research pipeline (Section 6)
  - intent_override == "CODE_EXECUTION" → python sandbox directly
  - intent_override == "WEB_SEARCH"     → quick web search + LLM summarize
  - No intent_override                  → RAG pipeline (default, fastest path)
"""

import json
import logging
import time
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

from app.services.auth import get_current_user
from app.services.material_service import filter_completed_material_ids
from app.services.token_counter import estimate_token_count, track_token_usage, get_model_token_limit
from app.services.audit_logger import log_api_usage
from app.core.config import settings
from app.db.prisma_client import prisma
from app.services.chat import service as chat_service
from app.models.shared_enums import IntentOverride
from .utils import require_material

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    material_id: Optional[str] = None
    material_ids: Optional[List[str]] = None
    message: str = Field(..., min_length=1, max_length=50000)
    notebook_id: str
    session_id: Optional[str] = None
    stream: Optional[bool] = True
    intent_override: Optional[IntentOverride] = None  # Set by frontend slash command ONLY


class BlockFollowupRequest(BaseModel):
    block_id: str
    question: str = Field(..., min_length=1, max_length=10000)
    action: str = "ask"  # ask, simplify, translate, explain


class SuggestionRequest(BaseModel):
    partial_input: str = Field(..., min_length=1, max_length=1000)
    notebook_id: str

class CreateSessionRequest(BaseModel):
    notebook_id: str
    title: Optional[str] = "New Chat"


@router.post("")
async def chat_endpoint(
    request: ChatRequest,
    current_user=Depends(get_current_user),
    debug: bool = Query(False, description="Enable debug mode"),
):
    start_time = time.time()

    # Resolve material IDs
    ids = request.material_ids or ([request.material_id] if request.material_id else [])
    if not ids:
        raise HTTPException(status_code=400, detail="No material selected")

    # Validate all materials belong to user
    for mid in ids:
        material = await require_material(mid, current_user.id)
        if material.notebookId and material.notebookId != request.notebook_id:
            raise HTTPException(
                status_code=400,
                detail=f"Material {mid} does not belong to the current notebook.",
            )

    # Guard: only search materials that have finished processing
    ids = await filter_completed_material_ids(ids, str(current_user.id))
    if not ids:
        raise HTTPException(
            status_code=400,
            detail=(
                "None of the selected materials have finished processing yet. "
                "Please wait for their status to reach 'completed' before chatting."
            ),
        )

    # Use provided session_id or create a new session
    session_id = request.session_id
    if not session_id:
        title = request.message[:30] + "..." if len(request.message) > 30 else request.message
        session_id = await chat_service.create_chat_session(request.notebook_id, str(current_user.id), title)
    else:
        # Auto-title untitled sessions on first real message
        try:
            from app.db.prisma_client import prisma
            existing = await prisma.chatsession.find_unique(where={"id": session_id})
            if existing and (not existing.title or existing.title in ("", "New Chat")):
                new_title = request.message[:30] + ("..." if len(request.message) > 30 else "")
                await prisma.chatsession.update(where={"id": session_id}, data={"title": new_title})
        except Exception:
            pass  # non-critical — don't fail the chat request

    try:
        # ── DIRECT ROUTING — no LLM intent classification ──────────
        intent = request.intent_override.value if request.intent_override else "RAG"

        if intent == "AGENT":
            return await _route_agent(request, ids, session_id, current_user, start_time)
        elif intent == "WEB_RESEARCH":
            return await _route_web_research(request, ids, session_id, current_user, start_time)
        elif intent == "CODE_EXECUTION":
            return await _route_code_execution(request, ids, session_id, current_user, start_time)
        elif intent == "WEB_SEARCH":
            return await _route_web_search(request, ids, session_id, current_user, start_time)
        else:
            # Default: RAG pipeline — fastest path, zero classification overhead
            return await _route_rag(request, ids, session_id, current_user, start_time, debug)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate response")


# ── Shared SSE helpers ────────────────────────────────────────

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


async def _persist_and_finalize(
    request: ChatRequest, session_id: str, current_user, start_time: float,
    answer: str, agent_meta: dict,
):
    """Save conversation + blocks to DB. Returns (msg_id, blocks)."""
    msg_id = await chat_service.save_conversation(
        notebook_id=request.notebook_id,
        user_id=str(current_user.id),
        user_message=request.message,
        assistant_answer=answer,
        session_id=session_id,
        agent_meta=agent_meta if agent_meta else None,
    )
    blocks = []
    if msg_id:
        blocks = await chat_service.save_response_blocks(msg_id, answer)
    if agent_meta:
        elapsed = time.time() - start_time
        await chat_service.log_agent_execution(
            user_id=str(current_user.id),
            notebook_id=request.notebook_id,
            meta=agent_meta,
            elapsed=elapsed,
        )
    return msg_id, blocks


# ── ROUTE: AGENT (intent_override == "AGENT") ────────────────

async def _route_agent(request, ids, session_id, current_user, start_time):
    """Fully agentic open-loop system via LangGraph."""
    from app.services.agent.agentic_loop import run_agentic_loop

    async def generate():
        try:
            full_response = []
            agent_meta = {}
            async for event in run_agentic_loop(
                query=request.message,
                material_ids=ids,
                notebook_id=request.notebook_id,
                user_id=str(current_user.id),
                session_id=session_id,
            ):
                yield event
                if event.startswith("event: token"):
                    data_line = event.split("data: ", 1)[-1].strip()
                    try:
                        full_response.append(json.loads(data_line).get("content", ""))
                    except json.JSONDecodeError:
                        pass
                elif event.startswith("event: meta"):
                    data_line = event.split("data: ", 1)[-1].strip()
                    try:
                        agent_meta = json.loads(data_line)
                    except json.JSONDecodeError:
                        pass

            complete = "".join(full_response) or agent_meta.get("response", "")
            if complete:
                meta = {**agent_meta, "intent": "AGENT"}
                msg_id, blocks = await _persist_and_finalize(
                    request, session_id, current_user, start_time, complete, meta
                )
                if blocks:
                    yield f"event: blocks\ndata: {json.dumps({'blocks': blocks})}\n\n"
        except Exception as e:
            logger.error("Agent streaming failed: %s", e)
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream", headers=_SSE_HEADERS)


# ── ROUTE: WEB_RESEARCH (intent_override == "WEB_RESEARCH") ──

async def _route_web_research(request, ids, session_id, current_user, start_time):
    """5-step deep web research pipeline."""
    from app.services.research.pipeline import stream_research

    async def generate():
        try:
            full_response = []
            citations = []
            async for event in stream_research(
                query=request.message,
                user_id=str(current_user.id),
                notebook_id=request.notebook_id,
                session_id=session_id,
            ):
                yield event
                # pipeline emits: data: {"type": "token", "content": "..."}\n\n
                if event.startswith("data: "):
                    data_str = event[len("data: "):].strip()
                    try:
                        payload = json.loads(data_str)
                        if payload.get("type") == "token":
                            full_response.append(payload.get("content", ""))
                        elif payload.get("type") == "citations":
                            citations = payload.get("citations", [])
                    except json.JSONDecodeError:
                        pass

            complete = "".join(full_response)
            if complete:
                meta = {"intent": "WEB_RESEARCH", "sources_count": len(citations)}
                msg_id, blocks = await _persist_and_finalize(
                    request, session_id, current_user, start_time, complete, meta
                )
                if blocks:
                    yield f"event: blocks\ndata: {json.dumps({'blocks': blocks})}\n\n"
        except Exception as e:
            logger.error("Research pipeline failed: %s", e)
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream", headers=_SSE_HEADERS)


# ── ROUTE: CODE_EXECUTION (intent_override == "CODE_EXECUTION") ──

async def _route_code_execution(request, ids, session_id, current_user, start_time):
    """Direct Python sandbox execution."""
    from app.services.code_execution.sandbox import run_in_sandbox
    from app.services.llm_service.llm import get_llm
    from app.prompts import get_code_generation_prompt

    async def generate():
        try:
            # Generate code from user request
            llm = get_llm(temperature=0.1)
            prompt = get_code_generation_prompt(request.message)
            code_response = await llm.ainvoke(prompt)
            code = getattr(code_response, "content", str(code_response)).strip()

            # Strip markdown fences
            if code.startswith("```python"):
                code = code[len("```python"):].strip()
            if code.startswith("```"):
                code = code[3:].strip()
            if code.endswith("```"):
                code = code[:-3].strip()

            yield f"event: code_generating\ndata: {json.dumps({'code': code})}\n\n"

            # Execute (run_in_sandbox is async)
            result = await run_in_sandbox(code)

            result_dict = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.exit_code,
                "timed_out": result.timed_out,
                "error": result.error,
                "elapsed_seconds": result.elapsed_seconds,
            }
            yield f"event: code_result\ndata: {json.dumps(result_dict)}\n\n"

            answer = f"```python\n{code}\n```\n\n**Output:**\n```\n{result.stdout}\n```"
            if result.error:
                answer += f"\n\n**Error:**\n```\n{result.error}\n```"

            meta = {"intent": "CODE_EXECUTION", "has_error": bool(result.error)}
            msg_id, blocks = await _persist_and_finalize(
                request, session_id, current_user, start_time, answer, meta
            )

            # Stream final response
            for chunk in [answer[i:i+100] for i in range(0, len(answer), 100)]:
                yield f"event: token\ndata: {json.dumps({'content': chunk})}\n\n"
            yield f"event: done\ndata: {{}}\n\n"

        except Exception as e:
            logger.error("Code execution failed: %s", e)
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream", headers=_SSE_HEADERS)


# ── ROUTE: WEB_SEARCH (intent_override == "WEB_SEARCH") ──────

async def _route_web_search(request, ids, session_id, current_user, start_time):
    """Quick web search + LLM summarize."""
    from app.services.llm_service.llm import get_llm

    async def generate():
        try:
            # Quick web search
            try:
                from app.services.agent.tools_registry import _web_search_impl
                search_results = await _web_search_impl(request.message, n_results=5)
            except Exception:
                import httpx
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(
                        f"{settings.SEARCH_SERVICE_URL}/search",
                        params={"q": request.message, "n": 5},
                    )
                    search_results = resp.json().get("results", [])

            yield f"event: search_results\ndata: {json.dumps({'results': search_results})}\n\n"

            # LLM summarize search results
            context = "\n\n".join(
                f"[{i+1}] {r.get('title', '')}\n{r.get('snippet', '')}\nURL: {r.get('url', '')}"
                for i, r in enumerate(search_results)
            )
            llm = get_llm(temperature=0.2)
            prompt = (
                f"Based on these web search results, answer the user's question.\n\n"
                f"Search Results:\n{context}\n\n"
                f"User Question: {request.message}\n\n"
                f"Provide a clear, concise answer with inline [n] citations."
            )
            llm_response = await llm.ainvoke(prompt)
            answer = getattr(llm_response, "content", str(llm_response))

            meta = {"intent": "WEB_SEARCH", "results_count": len(search_results)}
            msg_id, blocks = await _persist_and_finalize(
                request, session_id, current_user, start_time, answer, meta
            )

            # Stream answer
            for chunk in [answer[i:i+100] for i in range(0, len(answer), 100)]:
                yield f"event: token\ndata: {json.dumps({'content': chunk})}\n\n"
            yield f"event: done\ndata: {{}}\n\n"

        except Exception as e:
            logger.error("Web search failed: %s", e)
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream", headers=_SSE_HEADERS)


# ── ROUTE: RAG (no intent_override — default, fastest path) ──

async def _route_rag(request, ids, session_id, current_user, start_time, debug=False):
    """Default RAG pipeline — zero intent classification overhead."""
    from app.services.rag.pipeline import run_rag_pipeline

    if request.stream:
        async def generate():
            try:
                full_response = []
                async for event in run_rag_pipeline(
                    query=request.message,
                    material_ids=ids,
                    notebook_id=request.notebook_id,
                    user_id=str(current_user.id),
                    session_id=session_id,
                ):
                    yield event
                    if event.startswith("event: token"):
                        data_line = event.split("data: ", 1)[-1].strip()
                        try:
                            full_response.append(json.loads(data_line).get("content", ""))
                        except json.JSONDecodeError:
                            pass

                complete = "".join(full_response)
                if complete:
                    meta = {"intent": "RAG", "chunks_used": 0}
                    msg_id, blocks = await _persist_and_finalize(
                        request, session_id, current_user, start_time, complete, meta
                    )
                    if blocks:
                        yield f"event: blocks\ndata: {json.dumps({'blocks': blocks})}\n\n"
            except Exception as e:
                logger.error("RAG streaming failed: %s", e)
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(generate(), media_type="text/event-stream", headers=_SSE_HEADERS)
    else:
        from app.services.rag.pipeline import run_rag_pipeline_sync
        result = await run_rag_pipeline_sync(
            query=request.message,
            material_ids=ids,
            notebook_id=request.notebook_id,
            user_id=str(current_user.id),
            session_id=session_id,
        )
        answer = result.get("response", "")
        metadata = {"intent": "RAG", "chunks_used": result.get("chunks_used", 0)}

        context_tokens = estimate_token_count(request.message)
        response_tokens = estimate_token_count(answer)
        total_tokens = context_tokens + response_tokens
        model_name = settings.OLLAMA_MODEL if settings.LLM_PROVIDER == "OLLAMA" else settings.GOOGLE_MODEL
        model_max_tokens = get_model_token_limit(model_name)

        try:
            await track_token_usage(str(current_user.id), total_tokens)
        except Exception as e:
            logger.error("Token tracking failed: %s", e)

        total_time = time.time() - start_time
        try:
            await log_api_usage(
                user_id=str(current_user.id),
                endpoint="/chat",
                material_ids=ids,
                context_token_count=context_tokens,
                response_token_count=response_tokens,
                model_used=model_name,
                llm_latency=total_time,
                retrieval_latency=0.0,
                total_latency=total_time,
            )
        except Exception as e:
            logger.error("Audit logging failed: %s", e)

        msg_id = await chat_service.save_conversation(
            notebook_id=request.notebook_id,
            user_id=str(current_user.id),
            user_message=request.message,
            assistant_answer=answer,
            session_id=session_id,
        )
        blocks = []
        if msg_id:
            blocks = await chat_service.save_response_blocks(msg_id, answer)

        confidence = chat_service.compute_confidence_score("", answer)
        response_data = {
            "session_id": session_id,
            "answer": answer,
            "confidence": confidence,
            "context_tokens": context_tokens,
            "response_tokens": response_tokens,
            "total_tokens": total_tokens,
            "model_max_tokens": model_max_tokens,
            "truncated": False,
            "agent_metadata": metadata,
            "blocks": blocks,
        }
        if debug:
            response_data["debug"] = {
                "total_time": round(total_time, 3),
                "material_ids": ids,
                "model_used": model_name,
            }
        return JSONResponse(content=response_data)


# ── Block Followup (Phase 4 endpoint, registered early) ──────

@router.post("/block-followup")
async def block_followup(
    request: BlockFollowupRequest,
    current_user=Depends(get_current_user),
):
    """Block-level mini chat — streams a focused LLM response for a single paragraph.
    
    Persists the full follow-up response as a new ResponseBlock after streaming.
    Validates block ownership through the chat message's notebook → user chain.
    """
    try:
        # Validate block ownership — ensure the block belongs to this user
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
            accumulated = []
            try:
                async for text_chunk in chat_service.block_followup_stream(
                    block_id=request.block_id,
                    action=request.action,
                    question=request.question,
                ):
                    accumulated.append(text_chunk)
                    token_data = json.dumps({"content": text_chunk})
                    yield f"event: token\ndata: {token_data}\n\n"

                # Persist the followup response as a child ResponseBlock
                full_response = "".join(accumulated)
                if full_response.strip():
                    try:
                        # Find the parent block to get the chatMessageId
                        parent_block = await prisma.responseblock.find_unique(
                            where={"id": request.block_id}
                        )
                        if parent_block:
                            # Get next block index
                            max_block = await prisma.responseblock.find_first(
                                where={"chatMessageId": parent_block.chatMessageId},
                                order={"blockIndex": "desc"},
                            )
                            next_idx = (max_block.blockIndex + 1) if max_block else 0
                            await prisma.responseblock.create(
                                data={
                                    "chatMessageId": parent_block.chatMessageId,
                                    "blockIndex": next_idx,
                                    "text": f"[{request.action}] {full_response}",
                                }
                            )
                    except Exception as persist_err:
                        logger.warning("Failed to persist block followup: %s", persist_err)

                yield f"event: done\ndata: {{}}\n\n"
            except Exception as e:
                error_data = json.dumps({"error": str(e)})
                yield f"event: error\ndata: {error_data}\n\n"

        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Block followup failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process block followup")


# ── Prompt Suggestions (Phase 4 endpoint, registered early) ──

@router.post("/suggestions")
async def get_suggestions(
    request: SuggestionRequest,
    current_user=Depends(get_current_user),
):
    """Generate smart prompt suggestions based on partial input."""
    suggestions = await chat_service.get_suggestions(
        request.partial_input, 
        request.notebook_id, 
        str(current_user.id)
    )
    return JSONResponse(content={"suggestions": suggestions})


# ── Chat History ──────────────────────────────────────────────

@router.get("/history/{notebook_id}")
async def get_notebook_chat_history(
    notebook_id: str,
    session_id: Optional[str] = Query(None, description="Optional Chat Session ID"),
    current_user=Depends(get_current_user),
):
    """Get all chat messages for a notebook (or specific session)."""
    return await chat_service.get_chat_history(notebook_id, str(current_user.id), session_id)


@router.delete("/history/{notebook_id}")
async def clear_notebook_chat(
    notebook_id: str,
    session_id: Optional[str] = Query(None, description="Optional Chat Session ID"),
    current_user=Depends(get_current_user),
):
    """Clear all chat messages for a notebook (or specific session)."""
    await chat_service.clear_chat_history(
        notebook_id=notebook_id,
        user_id=str(current_user.id),
        session_id=session_id,
    )
    return {"cleared": True}

# ── Chat Sessions ──────────────────────────────────────────────

@router.get("/sessions/{notebook_id}")
async def get_chat_sessions_endpoint(
    notebook_id: str,
    current_user=Depends(get_current_user),
):
    """Get all chat sessions for a notebook."""
    sessions = await chat_service.get_chat_sessions(notebook_id, str(current_user.id))
    return JSONResponse(content={"sessions": sessions})


@router.post("/sessions")
async def create_chat_session_endpoint(
    request: CreateSessionRequest,
    current_user=Depends(get_current_user),
):
    """Create a new chat session."""
    session_id = await chat_service.create_chat_session(
        notebook_id=request.notebook_id,
        user_id=str(current_user.id),
        title=request.title
    )
    return JSONResponse(content={"session_id": session_id})


@router.delete("/sessions/{session_id}")
async def delete_chat_session_endpoint(
    session_id: str,
    current_user=Depends(get_current_user),
):
    """Delete a chat session."""
    success = await chat_service.delete_chat_session(session_id, str(current_user.id))
    if not success:
        raise HTTPException(status_code=404, detail="Session not found or could not be deleted")
    return {"deleted": True}
