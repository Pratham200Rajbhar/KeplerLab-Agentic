"""Chunker factory — selects the right chunker based on document structure."""
from __future__ import annotations

import logging
from typing import List, Dict, Any

from app.services.notebook_corpus.schemas import ExtractedContent
from .chunk_models import ChunkingResult

logger = logging.getLogger(__name__)


def chunk_content(
    extracted: ExtractedContent,
    source_id: str,
    *,
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
) -> ChunkingResult:
    """
    Select the right chunker and chunk the extracted content.

    Strategy selection:
    - If the document has sections (headings, pages, slides), use section chunker
    - Otherwise, use recursive character splitter
    """
    if extracted.sections and len(extracted.sections) >= 2:
        from .section_chunker import chunk_by_sections
        logger.info("Using section chunker for source %s (%d sections)", source_id, len(extracted.sections))
        return chunk_by_sections(extracted, source_id, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    from .recursive_chunker import chunk_recursive
    logger.info("Using recursive chunker for source %s", source_id)
    return chunk_recursive(extracted.text, source_id, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
