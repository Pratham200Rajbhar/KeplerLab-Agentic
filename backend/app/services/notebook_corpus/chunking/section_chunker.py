"""Section-aware chunker — preserves document structure (pages, headings, slides)."""
from __future__ import annotations

import logging
from typing import List

from app.services.notebook_corpus.extraction.normalization import estimate_tokens
from app.services.notebook_corpus.schemas import ExtractedContent
from .chunk_models import ChunkingResult, SourceChunkData

logger = logging.getLogger(__name__)


def chunk_by_sections(
    extracted: ExtractedContent,
    source_id: str,
    *,
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
) -> ChunkingResult:
    """
    Chunk by document sections, splitting long sections with recursive chunker.
    Preserves section_title and page_number metadata.
    """
    chunks: List[SourceChunkData] = []
    total_tokens = 0
    chunk_index = 0

    for section in extracted.sections:
        section_text = section.get("text", "").strip()
        section_title = section.get("title", "")
        page_number = section.get("page_number") or section.get("slide_index")

        if not section_text:
            continue

        if len(section_text) <= chunk_size * 1.2:
            # Small enough to be a single chunk
            token_count = estimate_tokens(section_text)
            total_tokens += token_count
            chunks.append(SourceChunkData(
                chunk_index=chunk_index,
                text=section_text,
                token_count=token_count,
                section_title=section_title,
                page_number=page_number,
                source_id=source_id,
            ))
            chunk_index += 1
        else:
            # Section is too large — sub-split it
            from .recursive_chunker import chunk_recursive
            sub_result = chunk_recursive(
                section_text, source_id,
                chunk_size=chunk_size, chunk_overlap=chunk_overlap,
            )
            for sub_chunk in sub_result.chunks:
                sub_chunk.chunk_index = chunk_index
                sub_chunk.section_title = section_title
                sub_chunk.page_number = page_number
                total_tokens += sub_chunk.token_count
                chunks.append(sub_chunk)
                chunk_index += 1

    return ChunkingResult(chunks=chunks, total_tokens=total_tokens, strategy="section")
