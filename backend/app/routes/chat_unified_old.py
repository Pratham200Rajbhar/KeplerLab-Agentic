"""Unified chat route - clean streaming architecture.

Single endpoint for all chat intents using StreamManager for consistent
streaming, state management, and persistence.
"""

import json
import logging
import time
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional

from app.services.auth import get_current_user
from app.services.material_service import filter_completed_material_ids
from app.models.shared_enums import IntentOverride
from app.services.stream import ChatStorage
from .utils import require_material

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])

# SSE headers
SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
    "Content-Type": "text/event-stream",
}


class ChatRequest(BaseModel):
    material_id: Optional[str] = None
    material_ids: Optional[List[str]] = None
    message: str = Field(..., min_length=1, max_length=50000)
    notebook_id: str
    session_id: Optional[str] = None
    stream: Optional[bool] = True
    intent_override: Optional[IntentOverride] = None


@router.post("")
async def chat_endpoint(
    request: ChatRequest,
    current_user=Depends(get_current_user),
):
    """Unified chat endpoint - all intents use StreamManager."""
    start_time = time.time()
    
    # Resolve material IDs
    ids = request.material_ids or ([request.material_id] if request.material_id else [])
    
    if ids:
        # Validate materials belong to user
        for mid in ids:
            material = await require_material(mid, current_user.id)
            if material.notebookId and material.notebookId != request.notebook_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Material {mid} does not belong to the current notebook.",
                )
        
        # Filter to completed materials only
        ids = await filter_completed_material_ids(ids, str(current_user.id))
        if not ids:
            raise HTTPException(
                status_code=400,
                detail=(
                    "None of the selected materials have finished processing yet. "
                    "Please wait for their status to reach 'completed' before chatting."
                ),
            )
    
    # Ensure session exists
    storage = ChatStorage()
    session_id = await storage.ensure_session(
        notebook_id=request.notebook_id,
        user_id=str(current_user.id),
        session_id=request.session_id,
        title=request.message[:30] + ("..." if len(request.message) > 30 else ""),
    )
    
    # Determine intent
    intent = request.intent_override.value if request.intent_override else "RAG"
    
    try:
        if request.stream:
            # Route to appropriate streaming pipeline
            if intent == "RAG":
                return await _stream_rag(request, ids, session_id, current_user)
            elif intent == "AGENT":
                return await _stream_agent(request, ids, session_id, current_user)
            elif intent == "WEB_RESEARCH":
                return await _stream_research(request, ids, session_id, current_user)
            elif intent == "CODE_EXECUTION":
                return await _stream_code(request, ids, session_id, current_user)
            elif intent == "WEB_SEARCH":
                return await _stream_web_search(request, ids, session_id, current_user)
            else:
                raise HTTPException(status_code=400, detail=f"Unknown intent: {intent}")
        else:
            # Non-streaming not implemented in unified architecture
            # Clients should use streaming
            raise HTTPException(
                status_code=400,
                detail="Non-streaming mode not supported. Please use stream=true."
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate response")


async def _stream_rag(request, ids, session_id, current_user):
    """Stream RAG pipeline."""
    from app.services.rag.pipeline_unified import stream_rag_unified
    
    async def generate():
        try:
            async for event in stream_rag_unified(
                query=request.message,
                material_ids=ids,
                notebook_id=request.notebook_id,
                user_id=str(current_user.id),
                session_id=session_id,
            ):
                yield event
        except Exception as e:
            logger.error(f"RAG streaming failed: {e}")
            from app.services.stream import format_error
            yield format_error(e)
    
    return StreamingResponse(generate(), media_type="text/event-stream", headers=SSE_HEADERS)


async def _stream_agent(request, ids, session_id, current_user):
    """Stream agent pipeline."""
    from app.services.agent.pipeline import stream_agent
    from app.services.stream import StreamManager
    
    async def generate():
        try:
            manager = StreamManager(
                user_id=str(current_user.id),
                notebook_id=request.notebook_id,
                session_id=session_id,
                user_message=request.message,
                intent="AGENT",
            )
            
            # Use existing stream_agent wrapped in manager
            async for event in manager.stream_with_pipeline(
                stream_agent,
                message=request.message,
                notebook_id=request.notebook_id,
                material_ids=ids,
                session_id=session_id,
                user_id=str(current_user.id),
            ):
                yield event
        except Exception as e:
            logger.error(f"Agent streaming failed: {e}")
            from app.services.stream import format_error
            yield format_error(e)
    
    return StreamingResponse(generate(), media_type="text/event-stream", headers=SSE_HEADERS)


async def _stream_research(request, ids, session_id, current_user):
    """Stream research pipeline."""
    from app.services.research.pipeline import stream_research
    from app.services.stream import StreamManager
    
    async def generate():
        try:
            manager = StreamManager(
                user_id=str(current_user.id),
                notebook_id=request.notebook_id,
                session_id=session_id,
                user_message=request.message,
                intent="WEB_RESEARCH",
            )
            
            async for event in manager.stream_with_pipeline(
                stream_research,
                query=request.message,
                user_id=str(current_user.id),
                notebook_id=request.notebook_id,
                session_id=session_id,
            ):
                yield event
        except Exception as e:
            logger.error(f"Research streaming failed: {e}")
            from app.services.stream import format_error
            yield format_error(e)
    
    return StreamingResponse(generate(), media_type="text/event-stream", headers=SSE_HEADERS)


async def _stream_code(request, ids, session_id, current_user):
    """Stream code execution pipeline."""
    from app.services.stream import StreamManager, format_error
    from app.services.llm_service.llm import get_llm
    from app.prompts import get_code_generation_prompt
    from app.services.rag.secure_retriever import secure_similarity_search_enhanced
    from app.services.rag.context_builder import build_context
    from app.core.config import settings
    
    async def generate():
        try:
            manager = StreamManager(
                user_id=str(current_user.id),
                notebook_id=request.notebook_id,
                session_id=session_id,
                user_message=request.message,
                intent="CODE_EXECUTION",
            )
            
            await manager.initialize()
            
            # Optional RAG for context
            rag_context = ""
            if ids:
                try:
                    yield await manager.emit_step("retrieval", "running", "Fetching context...")
                    chunks = await secure_similarity_search_enhanced(
                        query=request.message,
                        material_ids=ids,
                        user_id=str(current_user.id),
                        k=settings.INITIAL_VECTOR_K,
                    )
                    if chunks:
                        rag_context = build_context(chunks, max_tokens=settings.MAX_CONTEXT_TOKENS)
                    yield await manager.emit_step("retrieval", "done")
                except Exception:
                    pass
            
            # Generate code
            yield await manager.emit_step("code_generation", "running", "Generating code...")
            
            llm = get_llm(temperature=settings.LLM_TEMPERATURE_CODE)
            prompt = get_code_generation_prompt(request.message)
            if rag_context:
                prompt = f"{prompt}\n\nAvailable context:\n{rag_context}"
            
            code_response = await llm.ainvoke(prompt)
            code = getattr(code_response, "content", str(code_response)).strip()
            
            # Strip markdown fences
            if code.startswith("```python"):
                code = code[len("```python"):].strip()
            if code.startswith("```"):
                code = code[3:].strip()
            if code.endswith("```"):
                code = code[:-3].strip()
            
            yield await manager.emit_code_block(code, "python")
            yield await manager.emit_step("code_generation", "done", "Code ready")
            
            # Emit done_generation event
            yield await manager.emit_event("done_generation", {
                "message": "Code ready. Review and run.",
                "code": code
            })
            
            async for event in manager.finalize({"phase": "generated", "original_code": code}):
                yield event
        
        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            yield format_error(e)
    
    return StreamingResponse(generate(), media_type="text/event-stream", headers=SSE_HEADERS)


async def _stream_web_search(request, ids, session_id, current_user):
    """Stream web search pipeline."""
    from app.services.stream import StreamManager, format_error
    from app.services.llm_service.llm import get_llm
    from app.core.config import settings
    
    async def generate():
        try:
            manager = StreamManager(
                user_id=str(current_user.id),
                notebook_id=request.notebook_id,
                session_id=session_id,
                user_message=request.message,
                intent="WEB_SEARCH",
            )
            
            await manager.initialize()
            
            # Step 1: Query formulation
            yield await manager.emit_step("query_planning", "running", "Planning searches...")
            
            llm_planner = get_llm(temperature=0.1)
            query_prompt = (
                f"Generate 1-3 optimized web search queries. "
                f"Return ONLY a JSON array of strings.\n\n"
                f"Question: {request.message}\n\nQueries:"
            )
            query_response = await llm_planner.ainvoke(query_prompt)
            query_text = getattr(query_response, "content", str(query_response)).strip()
            
            queries = [request.message]
            try:
                import json as _json
                parsed = _json.loads(query_text.strip().strip("```json").strip("```"))
                if isinstance(parsed, list) and len(parsed) > 0:
                    queries = [str(q) for q in parsed[:3]]
            except Exception:
                pass
            
            yield await manager.emit_event("web_start", {"queries": queries})
            yield await manager.emit_step("query_planning", "done", f"Generated {len(queries)} queries")
            
            # Step 2: Search
            yield await manager.emit_step("web_search", "running", "Searching web...")
            
            import httpx
            from urllib.parse import urlparse
            
            all_results = []
            seen_urls = set()
            
            for q in queries:
                try:
                    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                        resp = await client.post(
                            f"{settings.SEARCH_SERVICE_URL}/api/search",
                            json={"query": q, "engine": "duckduckgo"},
                        )
                        resp.raise_for_status()
                        data = resp.json()
                        for r in data.get("organic_results", []):
                            url = r.get("link", "")
                            if url and url not in seen_urls:
                                seen_urls.add(url)
                                all_results.append({
                                    "title": r.get("title", ""),
                                    "url": url,
                                    "snippet": r.get("snippet", ""),
                                })
                except Exception:
                    pass
            
            yield await manager.emit_step("web_search", "done", f"Found {len(all_results)} results")
            
            # Step 3: Scrape top 5
            yield await manager.emit_step("web_scraping", "running", "Fetching content...")
            
            scraped = []
            for r in all_results[:5]:
                url = r["url"]
                yield await manager.emit_event("web_scraping", {"url": url, "status": "fetching"})
                try:
                    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                        resp = await client.post(
                            f"{settings.SEARCH_SERVICE_URL}/api/scrape",
                            json={"url": url},
                        )
                        resp.raise_for_status()
                        scrape_data = resp.json()
                        inner = scrape_data.get("content", scrape_data)
                        if isinstance(inner, dict):
                            title = inner.get("title", r["title"])
                            raw_content = inner.get("content", r["snippet"])
                            body = (" ".join(raw_content) if isinstance(raw_content, list) else str(raw_content))[:4000]
                        else:
                            title = r["title"]
                            body = str(inner)[:4000]
                        domain = urlparse(url).netloc
                        
                        yield await manager.emit_event("web_scraping", {"url": url, "status": "done"})
                        scraped.append({
                            "title": title, "url": url, "domain": domain,
                            "content": body, "snippet": r["snippet"],
                        })
                except Exception:
                    yield await manager.emit_event("web_scraping", {"url": url, "status": "failed"})
                    scraped.append({
                        "title": r["title"], "url": url,
                        "domain": urlparse(url).netloc,
                        "content": r["snippet"], "snippet": r["snippet"],
                    })
            
            yield await manager.emit_step("web_scraping", "done", f"Fetched {len(scraped)} sources")
            
            # Step 4: Synthesize
            yield await manager.emit_step("synthesis", "running", "Generating answer...")
            
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
                f"Provide a clear answer with inline citations:"
            )
            
            async for chunk in llm.astream(synth_prompt):
                content = getattr(chunk, "content", str(chunk))
                if content:
                    yield await manager.emit_token(content)
            
            yield await manager.emit_step("synthesis", "done", "Answer complete")
            
            # Emit sources
            sources = [
                {"title": s["title"], "url": s["url"], "index": i + 1}
                for i, s in enumerate(scraped)
            ]
            yield await manager.emit_event("web_sources", {"sources": sources})
            
            async for event in manager.finalize({
                "queries_used": queries,
                "sources": sources,
                "sources_count": len(sources),
            }):
                yield event
        
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            yield format_error(e)
    
    return StreamingResponse(generate(), media_type="text/event-stream", headers=SSE_HEADERS)
