from __future__ import annotations

import asyncio
import logging
import re
from typing import AsyncIterator, List

from app.core.config import settings
from app.services.chat_v2.schemas import ToolResult
from app.services.chat_v2.streaming import sse_tool_start, sse_tool_result

logger = logging.getLogger(__name__)

async def execute(
    query: str,
    material_ids: List[str],
    user_id: str,
    notebook_id: str,
) -> AsyncIterator[str | ToolResult]:
    yield sse_tool_start("rag", label="Searching your materials…")

    context = ""
    chunks_used = 0

    try:
        from app.services.rag.secure_retriever import secure_similarity_search_enhanced

        raw_context = await asyncio.to_thread(
            secure_similarity_search_enhanced,
            user_id=user_id,
            query=query,
            material_ids=material_ids,
            notebook_id=notebook_id,
            use_mmr=True,
            use_reranker=settings.USE_RERANKER,
            return_formatted=True,
        )

        if raw_context and raw_context.strip() != "No relevant context found.":
            context = raw_context
            chunks_used = len(re.findall(r"\[SOURCE\s+\d+\]", context))

    except Exception as exc:
        logger.error("RAG retrieval failed: %s", exc)
        yield sse_tool_result("rag", success=False, summary="Retrieval failed")
        yield ToolResult(
            tool_name="rag",
            success=False,
            content="",
            metadata={"error": str(exc), "chunks_used": 0},
        )
        return

    if not context:
        yield sse_tool_result("rag", success=True, summary="No relevant context found")
        yield ToolResult(
            tool_name="rag",
            success=True,
            content="",
            metadata={"chunks_used": 0, "empty": True},
        )
        return

    yield sse_tool_result("rag", success=True, summary=f"Found {chunks_used} source(s)")
    yield ToolResult(
        tool_name="rag",
        success=True,
        content=context,
        metadata={"chunks_used": chunks_used},
    )
