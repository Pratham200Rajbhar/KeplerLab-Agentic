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
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"

async def stream_rag(
    query: str,
    material_ids: List[str],
    notebook_id: str,
    user_id: str,
    session_id: str,
    chat_session_id: str | None = None,
) -> AsyncIterator[str]:
    start_time = time.time()

    try:
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

            import re
            chunks_used = len(re.findall(r"\[SOURCE\s+\d+\]", context))

        from app.services.chat_v2.message_store import get_history as get_chat_history
        from app.services.llm_service.llm import get_llm, extract_chunk_content
        from app.prompts import get_chat_prompt

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

        if chunks_used > 0:
            from app.services.rag.citation_validator import validate_citations
            validation = validate_citations(
                response=answer, num_sources=chunks_used, strict=True,
            )
            if not validation["is_valid"]:
                logger.warning("[rag_pipeline] Citation validation failed: %s", validation.get("error_message"))

        elapsed = round(time.time() - start_time, 2)
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
    try:
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

        await prisma.chatmessage.create(data={
            "notebookId": notebook_id,
            "userId": user_id,
            "chatSessionId": chat_session_id,
            "role": "user",
            "content": query,
        })

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


