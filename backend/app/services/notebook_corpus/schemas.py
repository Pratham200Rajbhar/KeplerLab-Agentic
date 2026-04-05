"""Pydantic schemas for the notebook corpus domain — requests, responses, internal DTOs."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .enums import (
    ExtractionStatus,
    IndexingStatus,
    RetrievalMode,
    SourceStatus,
    SourceType,
)


# ── Add source request / response ─────────────────────────────────────────

class AddSourceRequest(BaseModel):
    """Request body for adding a new source to a notebook."""
    notebook_id: str
    source_type: SourceType
    title: Optional[str] = Field(None, max_length=510)
    # For TEXT sources:
    text: Optional[str] = Field(None, max_length=500_000)
    # For URL sources:
    url: Optional[str] = Field(None, max_length=2048)
    # For NOTE sources:
    note_content: Optional[str] = Field(None, max_length=500_000)


class AddSourceResponse(BaseModel):
    """Response after queuing a new source."""
    source_id: str
    job_id: Optional[str] = None
    status: SourceStatus
    message: str = "Source queued for processing"


# ── Source listing / detail ───────────────────────────────────────────────

class SourceSummary(BaseModel):
    """Compact source representation for listing."""
    id: str
    source_type: SourceType
    title: Optional[str] = None
    original_name: Optional[str] = None
    status: SourceStatus
    extraction_status: ExtractionStatus = ExtractionStatus.PENDING
    indexing_status: IndexingStatus = IndexingStatus.PENDING
    token_count: int = 0
    warning_count: int = 0
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None


class SourceDetail(SourceSummary):
    """Full source representation including metadata."""
    notebook_id: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    checksum: Optional[str] = None
    fingerprint: Optional[str] = None
    retry_count: int = 0
    extracted_metadata: Optional[Dict[str, Any]] = None
    updated_at: Optional[datetime] = None


# ── Job status ────────────────────────────────────────────────────────────

class JobStatus(BaseModel):
    """Status of a source processing job."""
    job_id: str
    source_id: str
    stage: str
    status: str
    retry_count: int = 0
    last_error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    heartbeat_at: Optional[datetime] = None


# ── Retrieval ─────────────────────────────────────────────────────────────

class CitationAnchor(BaseModel):
    """A citation reference within retrieved context."""
    source_id: str
    chunk_id: Optional[str] = None
    section_id: Optional[str] = None
    title: str = ""
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    timestamp: Optional[str] = None  # for audio/video


class RetrievalResult(BaseModel):
    """A single retrieval result with text and citation."""
    text: str
    score: float = 0.0
    citation: CitationAnchor


class GroundedContext(BaseModel):
    """Assembled grounded context for downstream LLM consumption."""
    context_text: str
    retrieval_mode: RetrievalMode
    citations: List[CitationAnchor] = Field(default_factory=list)
    total_tokens: int = 0
    sources_used: int = 0
    chunks_used: int = 0


# ── Notebook corpus state ────────────────────────────────────────────────

class CorpusStateResponse(BaseModel):
    """Current state of a notebook's corpus."""
    notebook_id: str
    total_tokens: int = 0
    source_count: int = 0
    ready_source_count: int = 0
    retrieval_mode: RetrievalMode = RetrievalMode.DIRECT_GROUNDING
    last_rebuilt_at: Optional[datetime] = None


# ── Internal DTOs ────────────────────────────────────────────────────────

class ExtractedContent(BaseModel):
    """Result of content extraction from a source."""
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    sections: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    token_count: int = 0
    page_count: int = 0


class ChunkData(BaseModel):
    """A single chunk produced by the chunking stage."""
    chunk_index: int
    text: str
    token_count: int = 0
    section_title: Optional[str] = None
    page_number: Optional[int] = None
    source_id: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
