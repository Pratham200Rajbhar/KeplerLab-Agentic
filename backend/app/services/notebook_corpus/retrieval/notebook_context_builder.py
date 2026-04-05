"""Notebook context builder — unified entry point for grounded context retrieval."""
from __future__ import annotations

import logging
from typing import Optional

from app.core.config import settings
from app.db.prisma_client import prisma
from app.services.notebook_corpus.enums import RetrievalMode
from app.services.notebook_corpus.schemas import GroundedContext

from .corpus_router import select_retrieval_mode
from .direct_grounding import ground_directly
from .hybrid_retriever import retrieve_hybrid

logger = logging.getLogger(__name__)


async def get_notebook_context(
    notebook_id: str,
    user_id: str,
    query: str,
    *,
    max_tokens: Optional[int] = None,
) -> GroundedContext:
    """
    Unified retrieval entry point.

    Determines the retrieval mode based on corpus state, then dispatches
    to either direct grounding or hybrid indexed retrieval.

    This is the ONLY function that downstream features should call.
    """
    if not notebook_id or notebook_id == "draft":
        return GroundedContext(
            context_text="",
            retrieval_mode=RetrievalMode.DIRECT_GROUNDING,
            citations=[],
            total_tokens=0,
            sources_used=0,
            chunks_used=0,
        )

    # Get or compute corpus state
    corpus_state = await prisma.notebookcorpusstate.find_unique(
        where={"notebookId": notebook_id}
    )

    if corpus_state:
        total_tokens = corpus_state.totalTokens
        source_count = corpus_state.sourceCount
    else:
        # No cached state — count from sources directly
        ready_sources = await prisma.source.find_many(
            where={
                "notebookId": notebook_id,
                "userId": user_id,
                "status": "READY",
            },
        )
        total_tokens = sum(s.tokenCount for s in ready_sources)
        source_count = len(ready_sources)

    mode = select_retrieval_mode(total_tokens, source_count)
    budget = max_tokens or settings.DIRECT_GROUNDING_TOKEN_THRESHOLD

    if mode == RetrievalMode.DIRECT_GROUNDING:
        return await ground_directly(notebook_id, user_id, max_tokens=budget)

    return await retrieve_hybrid(notebook_id, user_id, query)
