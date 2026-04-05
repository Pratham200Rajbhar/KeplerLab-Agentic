"""Source management API routes."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.services.auth import get_current_user
from app.services.notebook_corpus.enums import SourceType
from app.services.notebook_corpus.errors import (
    CorpusError,
    DuplicateSourceError,
    SourceNotFoundError,
    SourceValidationError,
)
from app.services.notebook_corpus import orchestrator
from app.services.notebook_corpus.jobs import job_repository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notebooks/{notebook_id}/sources", tags=["Sources"])


# ── Request models ────────────────────────────────────────────────────────

class AddTextSourceRequest(BaseModel):
    source_type: SourceType
    title: Optional[str] = Field(None, max_length=510)
    text: Optional[str] = Field(None, max_length=500_000)
    url: Optional[str] = Field(None, max_length=2048)
    note_content: Optional[str] = Field(None, max_length=500_000)


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post("")
async def add_source(
    notebook_id: str,
    request: AddTextSourceRequest,
    current_user=Depends(get_current_user),
):
    """Add a text/URL/YouTube/note source to a notebook."""
    try:
        result = await orchestrator.add_source(
            notebook_id=notebook_id,
            user_id=str(current_user.id),
            source_type=request.source_type,
            title=request.title,
            text=request.text,
            url=request.url,
            note_content=request.note_content,
        )
        return result.model_dump()
    except DuplicateSourceError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except SourceValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except CorpusError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_source(
    notebook_id: str,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    current_user=Depends(get_current_user),
):
    """Upload a file source to a notebook."""
    try:
        result = await orchestrator.add_source(
            notebook_id=notebook_id,
            user_id=str(current_user.id),
            source_type=SourceType.FILE,
            title=title,
            file=file,
        )
        return result.model_dump()
    except DuplicateSourceError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except SourceValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except CorpusError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_sources(
    notebook_id: str,
    current_user=Depends(get_current_user),
):
    """List all sources for a notebook."""
    sources = await orchestrator.list_sources(notebook_id, str(current_user.id))
    return {"sources": [s.model_dump() for s in sources]}


@router.get("/{source_id}")
async def get_source(
    notebook_id: str,
    source_id: str,
    current_user=Depends(get_current_user),
):
    """Get details of a specific source."""
    try:
        source = await orchestrator.get_source(source_id, str(current_user.id))
        return source.model_dump()
    except SourceNotFoundError:
        raise HTTPException(status_code=404, detail="Source not found")


@router.delete("/{source_id}")
async def delete_source(
    notebook_id: str,
    source_id: str,
    current_user=Depends(get_current_user),
):
    """Delete a source and its indexed data."""
    try:
        await orchestrator.delete_source(source_id, str(current_user.id))
        return {"deleted": True}
    except SourceNotFoundError:
        raise HTTPException(status_code=404, detail="Source not found")


@router.post("/{source_id}/retry")
async def retry_source(
    notebook_id: str,
    source_id: str,
    current_user=Depends(get_current_user),
):
    """Retry a failed source."""
    try:
        result = await orchestrator.retry_source(source_id, str(current_user.id))
        return result.model_dump()
    except SourceNotFoundError:
        raise HTTPException(status_code=404, detail="Source not found")
    except SourceValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{source_id}/job")
async def get_job_status(
    notebook_id: str,
    source_id: str,
    current_user=Depends(get_current_user),
):
    """Get job status for a source."""
    job = await job_repository.get_job_by_source(source_id)
    if not job:
        raise HTTPException(status_code=404, detail="No job found for this source")

    return {
        "job_id": str(job.id),
        "source_id": str(job.sourceId),
        "stage": job.stage,
        "status": job.status,
        "retry_count": job.retryCount,
        "last_error": job.lastError,
        "started_at": job.startedAt.isoformat() if job.startedAt else None,
        "completed_at": job.completedAt.isoformat() if job.completedAt else None,
    }
