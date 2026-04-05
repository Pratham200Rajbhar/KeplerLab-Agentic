"""Corpus router — decides DIRECT_GROUNDING vs INDEXED_RETRIEVAL."""
from __future__ import annotations

import logging

from app.core.config import settings
from app.services.notebook_corpus.enums import RetrievalMode

logger = logging.getLogger(__name__)


def select_retrieval_mode(total_tokens: int, source_count: int) -> RetrievalMode:
    """
    Select retrieval mode based on corpus size.

    Rules:
    - If total_tokens <= DIRECT_GROUNDING_TOKEN_THRESHOLD AND
      source_count <= DIRECT_GROUNDING_SOURCE_LIMIT → DIRECT_GROUNDING
    - Otherwise → INDEXED_RETRIEVAL
    """
    if (
        total_tokens <= settings.DIRECT_GROUNDING_TOKEN_THRESHOLD
        and source_count <= settings.DIRECT_GROUNDING_SOURCE_LIMIT
    ):
        logger.debug(
            "Retrieval mode: DIRECT_GROUNDING (tokens=%d, sources=%d)",
            total_tokens, source_count,
        )
        return RetrievalMode.DIRECT_GROUNDING

    logger.debug(
        "Retrieval mode: INDEXED_RETRIEVAL (tokens=%d, sources=%d)",
        total_tokens, source_count,
    )
    return RetrievalMode.INDEXED_RETRIEVAL
