"""Direct grounding — returns full extracted text from all sources."""
from __future__ import annotations

import logging
from typing import List

from app.db.prisma_client import prisma
from app.services.notebook_corpus.enums import RetrievalMode
from app.services.notebook_corpus.schemas import CitationAnchor, GroundedContext

logger = logging.getLogger(__name__)


async def ground_directly(
    notebook_id: str,
    user_id: str,
    *,
    max_tokens: int = 60_000,
) -> GroundedContext:
    """
    Direct grounding: return full extracted text from all ready sources.
    Used when the notebook's total tokens fit within the LLM context window.
    Preserves source boundaries and section structure.
    """
    sources = await prisma.source.find_many(
        where={
            "notebookId": notebook_id,
            "userId": user_id,
            "status": "READY",
        },
        order={"createdAt": "asc"},
    )

    if not sources:
        return GroundedContext(
            context_text="",
            retrieval_mode=RetrievalMode.DIRECT_GROUNDING,
            citations=[],
            total_tokens=0,
            sources_used=0,
            chunks_used=0,
        )

    blocks: List[str] = []
    citations: List[CitationAnchor] = []
    total_tokens = 0
    budget = max_tokens * 4  # char estimate

    for source in sources:
        text = source.extractedText or ""
        if not text.strip():
            continue

        title = source.title or source.originalName or str(source.id)[:8]

        # Budget check
        if total_tokens + (len(text) // 4) > max_tokens:
            # Truncate to fit
            remaining_chars = budget - sum(len(b) for b in blocks)
            if remaining_chars > 200:
                text = text[:remaining_chars]
            else:
                break

        block = f"[SOURCE: {title}]\n{text}"
        blocks.append(block)
        total_tokens += len(text) // 4

        citations.append(CitationAnchor(
            source_id=str(source.id),
            title=title,
        ))

    context_text = "\n\n---\n\n".join(blocks)

    return GroundedContext(
        context_text=context_text,
        retrieval_mode=RetrievalMode.DIRECT_GROUNDING,
        citations=citations,
        total_tokens=total_tokens,
        sources_used=len(citations),
        chunks_used=0,
    )
