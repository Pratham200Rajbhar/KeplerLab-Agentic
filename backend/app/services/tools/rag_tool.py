from __future__ import annotations

import asyncio
import logging
import re
from typing import AsyncIterator, List, Optional

from app.db.prisma_client import prisma
from app.services.chat_v2.schemas import ToolResult
from app.services.chat_v2.streaming import sse_tool_start, sse_tool_result

logger = logging.getLogger(__name__)


async def _build_context(
    *,
    query: str,
    material_ids: List[str],
    user_id: str,
    notebook_id: str,
    max_chars: int = 24_000,
) -> str:
    terms = {t for t in re.findall(r"[a-zA-Z0-9_]+", (query or "").lower()) if len(t) > 3}

    where: dict[str, object] = {"userId": str(user_id)}
    ids = [str(mid) for mid in (material_ids or []) if str(mid).strip()]
    if ids:
        where["id"] = {"in": ids}
    elif notebook_id and notebook_id != "draft":
        where["notebookId"] = str(notebook_id)
    else:
        return ""

    materials = await prisma.material.find_many(where=where, order={"updatedAt": "desc"})
    scored_blocks: list[tuple[int, str]] = []
    for material in materials:
        text = str(getattr(material, "originalText", "") or "").strip()
        if not text:
            continue
        snippet = text[:8000]
        score = sum(1 for term in terms if term in snippet.lower()) if terms else 0
        title = str(getattr(material, "title", None) or getattr(material, "filename", None) or material.id)
        block = f"[SOURCE - Material: {title}]\n{snippet}"
        scored_blocks.append((score, block))

    scored_blocks.sort(key=lambda item: item[0], reverse=True)
    used = 0
    selected: list[str] = []
    for _, block in scored_blocks:
        if used + len(block) > max_chars:
            remaining = max_chars - used
            if remaining > 128:
                selected.append(block[:remaining])
            break
        selected.append(block)
        used += len(block)

    return "\n\n".join(selected)

async def execute(
    query: str,
    material_ids: List[str],
    user_id: str,
    notebook_id: str,
    step_index: Optional[int] = None,
) -> AsyncIterator[str | ToolResult]:
    yield sse_tool_start("rag", label="Searching your materials…")

    context = ""
    chunks_used = 0

    try:
        raw_context = await _build_context(
            query=query,
            material_ids=material_ids,
            user_id=user_id,
            notebook_id=notebook_id,
        )

        if raw_context:
            context = raw_context
            chunks_used = len(re.findall(r"\[SOURCE\s+\d+(?:\s+-\s+Material:.*?)?\]", context))
            if chunks_used == 0:
                chunks_used = context.count("[SOURCE - Material:")

    except Exception as exc:
        logger.error("RAG retrieval failed: %s", exc)
        yield sse_tool_result("rag", success=False, summary="Retrieval failed", step_index=step_index)
        yield ToolResult(
            tool_name="rag",
            success=False,
            content="",
            metadata={"error": str(exc), "chunks_used": 0},
        )
        return

    if not context:
        yield sse_tool_result("rag", success=True, summary="No relevant context found", step_index=step_index)
        yield ToolResult(
            tool_name="rag",
            success=True,
            content="",
            metadata={"chunks_used": 0, "empty": True},
        )
        return

    yield sse_tool_result("rag", success=True, summary=f"Found {chunks_used} source(s)", step_index=step_index)
    yield ToolResult(
        tool_name="rag",
        success=True,
        content=context,
        metadata={"chunks_used": chunks_used},
    )
