"""Default RAG path — lean, fast, no agent overhead.

Used when **no** ``intent_override`` is present (i.e. normal chat).
This must be the fastest path: retrieve → build context → stream LLM → save.

Flow
----
1. Retrieve top-K chunks from selected material_ids via ChromaDB + BGE reranker
2. Build context window respecting MAX_CONTEXT_TOKENS
3. Stream LLM response with inline citations (token SSE events)
4. Save message to DB with agent_meta: ``{intent: "RAG", chunks_used: N}``

No agent loop, no web requests, no tool calls.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, AsyncIterator, Dict, List

from app.core.config import settings
from app.db.prisma_client import prisma

logger = logging.getLogger(__name__)


def _sse(event_type: str, data: Any) -> str:
    # Standard SSE format: event type on its own line, then data payload.
    # Frontend readSSEStream dispatches on the event name directly, and the
    # run_rag_pipeline_sync parser uses the event line to detect token/meta.
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


async def stream_rag(
    query: str,
    material_ids: List[str],
    notebook_id: str,
    user_id: str,
    session_id: str,
    chat_session_id: str | None = None,
) -> AsyncIterator[str]:
    """Run lean RAG pipeline and stream SSE token events.

    Handles edge cases:
    - No materials selected → message asking to select materials
    - No materials uploaded → onboarding message
    - No relevant context found → clear message
    """
    start_time = time.time()

    try:
        # ── Step 1: Retrieve chunks via secure retriever ──────
        from app.services.rag.secure_retriever import secure_similarity_search_enhanced

        context = ""
        chunks_used = 0

        if material_ids:
            context = await asyncio.to_thread(
                secure_similarity_search_enhanced,
                user_id=user_id,
                query=query,
                material_ids=material_ids,
                notebook_id=notebook_id,
                use_mmr=True,
                use_reranker=settings.USE_RERANKER,
                return_formatted=True,
            )

            if not context or context.strip() == "No relevant context found.":
                msg = (
                    "I couldn't find relevant information in your selected materials "
                    "for that question. Try rephrasing your query or selecting different materials."
                )
                yield _sse("token", {"content": msg})
                yield _sse("meta", {"intent": "RAG", "chunks_used": 0, "elapsed": round(time.time() - start_time, 2)})
                yield _sse("done", {"elapsed": round(time.time() - start_time, 2)})
                return

            # Count chunks used
            import re
            chunks_used = len(re.findall(r"\[SOURCE\s+\d+\]", context))

        # ── Step 2: Stream LLM response with citations ────────
        from app.services.chat_v2.message_store import get_history as get_chat_history
        from app.services.llm_service.llm import get_llm, extract_chunk_content
        from app.prompts import get_chat_prompt

        # Build history
        raw_history = await get_chat_history(notebook_id, user_id, session_id)
        history_lines = []
        for msg in raw_history[-10:]:
            role = msg.get("role", "user").capitalize()
            content = msg.get("content", "")
            history_lines.append(f"{role}: {content}")
        formatted_history = "\n".join(history_lines) if history_lines else "None"

        prompt = get_chat_prompt(context, formatted_history, query)
        llm = get_llm()

        full_response: list[str] = []
        async for chunk in llm.astream(prompt):
            content = extract_chunk_content(chunk)
            if content:
                full_response.append(content)
                yield _sse("token", {"content": content})

        answer = "".join(full_response).strip()

        # ── Step 3: Validate citations ────────────────────────
        if chunks_used > 0:
            from app.services.rag.citation_validator import validate_citations
            validation = validate_citations(
                response=answer, num_sources=chunks_used, strict=True,
            )
            if not validation["is_valid"]:
                logger.warning("[rag_pipeline] Citation validation failed: %s", validation.get("error_message"))

        # ── Step 4: Emit metadata + done ──────────────────────
        elapsed = round(time.time() - start_time, 2)
        # NOTE: Persistence is the route layer's responsibility.
        # _route_rag accumulates tokens and calls _persist_and_finalize after
        # the stream completes — no need to also save here.
        yield _sse("meta", {
            "intent": "RAG",
            "chunks_used": chunks_used,
            "elapsed": elapsed,
        })
        yield _sse("done", {"elapsed": elapsed})

    except Exception as exc:
        logger.exception("[rag_pipeline] Error: %s", exc)
        yield _sse("error", {"error": str(exc)})
        yield _sse("done", {"elapsed": round(time.time() - start_time, 2)})


async def _save_message(
    notebook_id: str,
    user_id: str,
    session_id: str,
    chat_session_id: str | None,
    query: str,
    answer: str,
    chunks_used: int,
) -> None:
    """Save user + assistant messages to DB. Best-effort — never raises."""
    try:
        # Ensure chat session exists
        if not chat_session_id:
            session = await prisma.chatsession.find_first(
                where={"notebookId": notebook_id, "userId": user_id},
                order={"createdAt": "desc"},
            )
            if session:
                chat_session_id = session.id
            else:
                session = await prisma.chatsession.create(data={
                    "notebookId": notebook_id,
                    "userId": user_id,
                    "title": query[:100],
                })
                chat_session_id = session.id

        agent_meta = json.dumps({
            "intent": "RAG",
            "chunks_used": chunks_used,
        })

        # Save user message
        await prisma.chatmessage.create(data={
            "notebookId": notebook_id,
            "userId": user_id,
            "chatSessionId": chat_session_id,
            "role": "user",
            "content": query,
        })

        # Save assistant message
        await prisma.chatmessage.create(data={
            "notebookId": notebook_id,
            "userId": user_id,
            "chatSessionId": chat_session_id,
            "role": "assistant",
            "content": answer,
            "agentMeta": agent_meta,
        })

    except Exception as exc:
        logger.warning("[rag_pipeline] _save_message failed (non-fatal): %s", exc)


# ── Compatibility aliases ─────────────────────────────────────
# chat.py imports run_rag_pipeline (streaming) and run_rag_pipeline_sync (non-streaming)

run_rag_pipeline = stream_rag


async def run_rag_pipeline_sync(
    query: str,
    material_ids: List[str],
    notebook_id: str,
    user_id: str,
    session_id: str,
    chat_session_id: str | None = None,
) -> Dict[str, Any]:
    """Non-streaming wrapper — collects all SSE tokens and returns a plain dict.

    Returns:
        {"response": "<full answer>", "chunks_used": <int>}
    """
    response_parts: List[str] = []
    chunks_used = 0
    async for event in stream_rag(
        query=query,
        material_ids=material_ids,
        notebook_id=notebook_id,
        user_id=user_id,
        session_id=session_id,
        chat_session_id=chat_session_id,
    ):
        try:
            # Parse both the new standard-SSE format (event: TYPE\ndata: {...})
            # and the legacy type-in-data format (data: {"type": ..., ...}).
            event_type: str | None = None
            for line in event.splitlines():
                if line.startswith("event: "):
                    event_type = line[7:].strip()
                elif line.startswith("data: "):
                    payload: Dict[str, Any] = json.loads(line[6:])
                    # Fallback: legacy format embeds type inside payload
                    etype = event_type or payload.get("type")
                    if etype == "token":
                        response_parts.append(payload.get("content", ""))
                    elif etype == "meta":
                        chunks_used = payload.get("chunks_used", chunks_used)
        except (json.JSONDecodeError, AttributeError):
            pass
    return {"response": "".join(response_parts).strip(), "chunks_used": chunks_used}
