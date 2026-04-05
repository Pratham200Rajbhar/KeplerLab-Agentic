"""Chunk data models."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SourceChunkData(BaseModel):
    """A single chunk produced by the chunking stage."""
    chunk_index: int
    text: str
    token_count: int = 0
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    source_id: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChunkingResult(BaseModel):
    """Result of chunking a source."""
    chunks: List[SourceChunkData]
    total_tokens: int = 0
    strategy: str = "recursive"
