"""Chat route — Direct-routed conversation with materials.

Routing is ALWAYS set explicitly by the frontend slash command.
The backend NEVER calls an LLM to guess or classify intent.

Routing logic (strict, no inference):
  - intent_override == "WEB_RESEARCH"   → deep research pipeline
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

    if ids:
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
    """Multi-step autonomous agent pipeline."""
    from app.services.agent.pipeline import stream_agent

    async def generate():
        try:
            full_response = []
            tools_used = []
            steps_count = 0

            async for event in stream_agent(
                message=request.message,
                notebook_id=request.notebook_id,
                material_ids=ids,
                session_id=session_id,
                user_id=str(current_user.id),
            ):
                yield event
                # Capture tokens for persistence
                if event.startswith("event: token\n"):
                    for line in event.split("\n"):
                        if line.startswith("data: "):
                            try:
                                payload = json.loads(line[len("data: "):])
                                full_response.append(payload.get("content", ""))
                            except json.JSONDecodeError:
                                pass
                elif event.startswith("event: done\n"):
                    for line in event.split("\n"):
                        if line.startswith("data: "):
                            try:
                                payload = json.loads(line[len("data: "):])
                                tools_used = payload.get("tools_used", [])
                                steps_count = payload.get("steps", 0)
                            except json.JSONDecodeError:
                                pass

            complete = "".join(full_response)
            if complete:
                meta = {
                    "intent": "AGENT",
                    "tools_used": tools_used,
                    "steps_count": steps_count,
                }
                msg_id, blocks = await _persist_and_finalize(
                    request, session_id, current_user, start_time, complete, meta
                )
                if blocks:
                    yield f"event: blocks\ndata: {json.dumps({'blocks': blocks})}\n\n"
        except Exception as e:
            logger.error("Agent pipeline failed: %s", e)
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
                # pipeline emits: event: token\ndata: {"content": "..."}\n\n
                # and:            event: citations\ndata: {"citations": [...]}\n\n
                if event.startswith("event: token\n") or event.startswith("event: citations\n"):
                    for line in event.split("\n"):
                        if line.startswith("data: "):
                            try:
                                payload = json.loads(line[len("data: "):])
                                if event.startswith("event: token\n"):
                                    full_response.append(payload.get("content", ""))
                                else:
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
    """Two-phase code mode: Phase 1 = generate code only, Phase 2 = user clicks Run."""
    from app.services.llm_service.llm import get_llm
    from app.prompts import get_code_generation_prompt
    from app.services.rag.secure_retriever import secure_similarity_search_enhanced
    from app.services.rag.context_builder import build_context

    async def generate():
        try:
            # Phase 1: Optional RAG for context
            rag_context = ""
            if ids:
                try:
                    chunks = await secure_similarity_search_enhanced(
                        query=request.message,
                        material_ids=ids,
                        user_id=str(current_user.id),
                        k=settings.INITIAL_VECTOR_K,
                    )
                    if chunks:
                        rag_context = build_context(chunks, max_tokens=settings.MAX_CONTEXT_TOKENS)
                except Exception:
                    pass

            # Phase 1: LLM generates code
            llm = get_llm(temperature=settings.LLM_TEMPERATURE_CODE)
            prompt = get_code_generation_prompt(request.message)
            if rag_context:
                prompt = f"{prompt}\n\nAvailable context from uploaded materials:\n{rag_context}"

            code_response = await llm.ainvoke(prompt)
            code = getattr(code_response, "content", str(code_response)).strip()

            # Strip markdown fences
            if code.startswith("```python"):
                code = code[len("```python"):].strip()
            if code.startswith("```"):
                code = code[3:].strip()
            if code.endswith("```"):
                code = code[:-3].strip()

            # Emit code_block (the generated code for user review)
            yield f"event: code_block\ndata: {json.dumps({'code': code, 'language': 'python', 'session_id': session_id})}\n\n"

            # Emit done_generation (Phase 1 complete — waiting for user action)
            yield f"event: done_generation\ndata: {json.dumps({'message': 'Code ready. Review and run.'})}\n\n"

            # Save the initial code generation as a message
            answer = f"Here is the code to accomplish your task:"
            meta = {"intent": "CODE_EXECUTION", "original_code": code, "phase": "generated"}
            msg_id, blocks = await _persist_and_finalize(
                request, session_id, current_user, start_time, answer, meta
            )

            yield f"event: done\ndata: {json.dumps({'intent': 'CODEEXECUTION', 'code': code})}\n\n"

        except Exception as e:
            logger.error("Code generation failed: %s", e)
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream", headers=_SSE_HEADERS)


# ── ROUTE: WEB_SEARCH (intent_override == "WEB_SEARCH") ──────

async def _route_web_search(request, ids, session_id, current_user, start_time):
    """Multi-query web search + scrape + LLM synthesize with streaming."""
    from app.services.llm_service.llm import get_llm

    async def generate():
        try:
            # Step 1: Query formulation — LLM generates 1-3 search queries
            llm_planner = get_llm(temperature=0.1)
            query_prompt = (
                f"Generate 1-3 optimized web search queries to answer this question. "
                f"Return ONLY a JSON array of strings, nothing else.\n\n"
                f"Question: {request.message}\n\nQueries:"
            )
            query_response = await llm_planner.ainvoke(query_prompt)
            query_text = getattr(query_response, "content", str(query_response)).strip()

            # Parse queries
            queries = [request.message]  # fallback
            try:
                import json as _json
                parsed = _json.loads(query_text.strip().strip("```json").strip("```"))
                if isinstance(parsed, list) and len(parsed) > 0:
                    queries = [str(q) for q in parsed[:3]]
            except Exception:
                pass

            yield f"event: web_start\ndata: {json.dumps({'queries': queries})}\n\n"

            # Step 2: Search via DuckDuckGo
            from app.core.web_search import ddg_search, fetch_url_content
            from urllib.parse import urlparse

            all_results = []
            seen_urls = set()

            for q in queries:
                try:
                    results = await ddg_search(q, max_results=5)
                    for r in results:
                        url = r.get("url", "")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_results.append({
                                "title": r.get("title", ""),
                                "url": url,
                                "snippet": r.get("snippet", ""),
                            })
                except Exception:
                    pass

            # Step 3: Scrape top 5 via trafilatura
            scraped = []
            for r in all_results[:5]:
                url = r["url"]
                yield f"event: web_scraping\ndata: {json.dumps({'url': url, 'status': 'fetching'})}\n\n"
                try:
                    fetched = await fetch_url_content(url)
                    if fetched and fetched.get("text"):
                        title = fetched.get("title") or r["title"]
                        body = fetched["text"][:4000]
                        domain = fetched.get("domain", urlparse(url).netloc)
                    else:
                        title = r["title"]
                        body = r["snippet"]
                        domain = urlparse(url).netloc

                    yield f"event: web_scraping\ndata: {json.dumps({'url': url, 'status': 'done'})}\n\n"
                    scraped.append({
                        "title": title, "url": url, "domain": domain,
                        "content": body, "snippet": r["snippet"],
                    })
                except Exception:
                    yield f"event: web_scraping\ndata: {json.dumps({'url': url, 'status': 'failed'})}\n\n"
                    # Use snippet as fallback content
                    scraped.append({
                        "title": r["title"], "url": url,
                        "domain": urlparse(url).netloc,
                        "content": r["snippet"], "snippet": r["snippet"],
                    })

            # Step 4: Score and filter (keep top 5 by content length * relevance)
            for s in scraped:
                content_score = min(len(s.get("content", "")), 2000) / 2000
                # Simple keyword overlap score
                msg_words = set(request.message.lower().split())
                content_words = set(s.get("content", "").lower().split()[:200])
                overlap = len(msg_words & content_words)
                s["_score"] = content_score * 0.5 + min(overlap / max(len(msg_words), 1), 1.0) * 0.5

            scraped.sort(key=lambda x: x.get("_score", 0), reverse=True)
            scraped = scraped[:5]

            # Step 5: Synthesize with LLM — stream response
            context = "\n\n".join(
                f"[{i+1}] {s['title']}\nURL: {s['url']}\n{s['content'][:2000]}"
                for i, s in enumerate(scraped)
            )

            llm = get_llm(temperature=0.3)
            synth_prompt = (
                f"Based on these web search results, answer the user's question. "
                f"Cite sources inline with [1] [2] [3] format.\n\n"
                f"Search Results:\n{context}\n\n"
                f"User Question: {request.message}\n\n"
                f"Provide a clear, comprehensive answer with inline citations:"
            )

            answer_parts = []
            async for chunk in llm.astream(synth_prompt):
                from app.services.llm_service.llm import extract_chunk_content
                content = extract_chunk_content(chunk)
                if content:
                    answer_parts.append(content)
                    yield f"event: token\ndata: {json.dumps({'content': content})}\n\n"

            # Step 6: Emit sources
            sources = [
                {"title": s["title"], "url": s["url"], "index": i + 1}
                for i, s in enumerate(scraped)
            ]
            yield f"event: web_sources\ndata: {json.dumps({'sources': sources})}\n\n"

            # Step 7: Persist
            answer = "".join(answer_parts)
            elapsed = time.time() - start_time
            meta = {
                "intent": "WEB_SEARCH",
                "queries_used": queries,
                "sources": sources,
                "tokens_used": 0,
                "elapsed": round(elapsed, 2),
            }
            msg_id, blocks = await _persist_and_finalize(
                request, session_id, current_user, start_time, answer, meta
            )
            if blocks:
                yield f"event: blocks\ndata: {json.dumps({'blocks': blocks})}\n\n"

            yield f"event: done\ndata: {json.dumps({'intent': 'WEBSEARCH', 'sources_count': len(sources), 'tokens_used': 0, 'elapsed': round(elapsed, 2)})}\n\n"

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
