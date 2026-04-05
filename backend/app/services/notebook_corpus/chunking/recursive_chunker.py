"""Recursive character text splitter — fallback chunker for unstructured content."""
from __future__ import annotations

import logging
from typing import List

from app.services.notebook_corpus.extraction.normalization import estimate_tokens
from .chunk_models import ChunkingResult, SourceChunkData

logger = logging.getLogger(__name__)


def chunk_recursive(
    text: str,
    source_id: str,
    *,
    chunk_size: int = 1200,
    chunk_overlap: int = 200,
) -> ChunkingResult:
    """
    Split text using recursive character splitting (paragraph → sentence → word).
    Uses langchain's RecursiveCharacterTextSplitter under the hood.
    """
    if not text.strip():
        return ChunkingResult(chunks=[], total_tokens=0, strategy="recursive")

    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n\n", "\n\n", "\n", ". ", " ", ""],
            length_function=len,
        )
        raw_chunks = splitter.split_text(text)
    except ImportError:
        # Manual fallback split
        logger.warning("langchain_text_splitters not available, using simple split")
        raw_chunks = _simple_split(text, chunk_size, chunk_overlap)

    chunks: List[SourceChunkData] = []
    total_tokens = 0

    for idx, chunk_text in enumerate(raw_chunks):
        chunk_text = chunk_text.strip()
        if not chunk_text:
            continue
        token_count = estimate_tokens(chunk_text)
        total_tokens += token_count
        chunks.append(SourceChunkData(
            chunk_index=idx,
            text=chunk_text,
            token_count=token_count,
            source_id=source_id,
        ))

    return ChunkingResult(chunks=chunks, total_tokens=total_tokens, strategy="recursive")


def _simple_split(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Simple fallback splitter."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap
        if start >= len(text):
            break
    return chunks
