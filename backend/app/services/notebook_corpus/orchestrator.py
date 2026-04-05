"""Notebook corpus orchestrator — the main entry point for all corpus operations."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import UploadFile

from app.core.config import settings
from app.db.prisma_client import prisma
from app.services.notebook_corpus.enums import SourceStatus, SourceType
from app.services.notebook_corpus.errors import (
    DuplicateSourceError,
    SourceNotFoundError,
    SourceValidationError,
    TenantViolationError,
)
from app.services.notebook_corpus.fingerprints import compute_fingerprint
from app.services.notebook_corpus.indexing.index_manager import delete_source_index
from app.services.notebook_corpus.jobs import job_repository
from app.services.notebook_corpus.retrieval.notebook_context_builder import get_notebook_context
from app.services.notebook_corpus.schemas import (
    AddSourceResponse,
    GroundedContext,
    SourceDetail,
    SourceSummary,
)
from app.services.notebook_corpus.validators import validate_source_input

logger = logging.getLogger(__name__)


async def add_source(
    *,
    notebook_id: str,
    user_id: str,
    source_type: SourceType,
    title: Optional[str] = None,
    text: Optional[str] = None,
    url: Optional[str] = None,
    note_content: Optional[str] = None,
    file: Optional[UploadFile] = None,
) -> AddSourceResponse:
    """
    Add a new source to a notebook.
    Validates input, checks for duplicates, persists the source, and queues a processing job.
    """
    # 1. Validate input
    validated = validate_source_input(
        source_type,
        filename=file.filename if file else None,
        size_bytes=file.size if file else 0,
        mime_type=file.content_type if file else None,
        text=text,
        url=url,
        note_content=note_content,
    )

    # 2. Handle file upload
    local_file_path: Optional[str] = None
    original_name: Optional[str] = None
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None

    if file and source_type in (SourceType.FILE, SourceType.AUDIO_TRANSCRIPT):
        original_name = file.filename
        mime_type = file.content_type
        file_bytes = await file.read()
        size_bytes = len(file_bytes)

        # Save to upload dir
        upload_dir = os.path.join(settings.UPLOAD_DIR, user_id, "sources")
        os.makedirs(upload_dir, exist_ok=True)
        import uuid
        safe_name = f"{uuid.uuid4().hex}_{original_name}"
        local_file_path = os.path.join(upload_dir, safe_name)
        with open(local_file_path, "wb") as f:
            f.write(file_bytes)

    # 3. Compute fingerprint for dedup (text/note sources)
    fingerprint: Optional[str] = None
    if source_type == SourceType.TEXT and text:
        fingerprint = compute_fingerprint(text)
    elif source_type == SourceType.NOTE and note_content:
        fingerprint = compute_fingerprint(note_content)

    # 4. Check for duplicates
    if fingerprint and settings.ENABLE_SOURCE_DEDUPLICATION:
        existing = await prisma.source.find_first(
            where={
                "notebookId": notebook_id,
                "userId": user_id,
                "fingerprint": fingerprint,
                "status": {"not": "DEAD_LETTER"},
            },
        )
        if existing:
            raise DuplicateSourceError(
                existing_source_id=str(existing.id),
            )

    # 5. Persist source
    source = await prisma.source.create(
        data={
            "userId": user_id,
            "notebookId": notebook_id,
            "sourceType": source_type.value,
            "status": SourceStatus.QUEUED.value,
            "title": title or original_name,
            "originalName": original_name,
            "mimeType": mime_type,
            "sizeBytes": size_bytes,
            "inputText": text or note_content,
            "inputUrl": url,
            "localFilePath": local_file_path,
            "fingerprint": fingerprint,
        },
    )

    source_id = str(source.id)

    # 6. Create processing job
    job_id = await job_repository.create_job(source_id, user_id)

    logger.info(
        "Source added: id=%s type=%s notebook=%s job=%s",
        source_id, source_type.value, notebook_id, job_id,
    )

    return AddSourceResponse(
        source_id=source_id,
        job_id=job_id,
        status=SourceStatus.QUEUED,
        message=f"Source queued for processing ({source_type.value})",
    )


async def list_sources(notebook_id: str, user_id: str) -> List[SourceSummary]:
    """List all sources for a notebook."""
    sources = await prisma.source.find_many(
        where={"notebookId": notebook_id, "userId": user_id},
        order={"createdAt": "desc"},
    )

    return [
        SourceSummary(
            id=str(s.id),
            source_type=SourceType(s.sourceType),
            title=s.title,
            original_name=s.originalName,
            status=SourceStatus(s.status),
            token_count=s.tokenCount,
            warning_count=s.warningCount,
            error_code=s.errorCode,
            error_message=s.errorMessage,
            created_at=s.createdAt,
            processed_at=s.processedAt,
        )
        for s in sources
    ]


async def get_source(source_id: str, user_id: str) -> SourceDetail:
    """Get detailed source info."""
    source = await prisma.source.find_first(
        where={"id": source_id, "userId": user_id},
    )
    if not source:
        raise SourceNotFoundError(source_id)

    return SourceDetail(
        id=str(source.id),
        source_type=SourceType(source.sourceType),
        title=source.title,
        original_name=source.originalName,
        status=SourceStatus(source.status),
        notebook_id=source.notebookId,
        mime_type=source.mimeType,
        size_bytes=source.sizeBytes,
        checksum=source.checksum,
        fingerprint=source.fingerprint,
        token_count=source.tokenCount,
        warning_count=source.warningCount,
        error_code=source.errorCode,
        error_message=source.errorMessage,
        retry_count=source.retryCount,
        extracted_metadata=source.extractedMetadata,
        created_at=source.createdAt,
        processed_at=source.processedAt,
        updated_at=source.updatedAt,
    )


async def delete_source(source_id: str, user_id: str) -> bool:
    """Delete a source and all its indexed data."""
    source = await prisma.source.find_first(
        where={"id": source_id, "userId": user_id},
    )
    if not source:
        raise SourceNotFoundError(source_id)

    notebook_id = source.notebookId

    # Delete index data
    if notebook_id:
        await delete_source_index(source_id, notebook_id)

    # Delete source (cascades to chunks, citations, job)
    await prisma.source.delete(where={"id": source_id})

    # Rebuild corpus state
    if notebook_id:
        from app.services.notebook_corpus.jobs.worker import _rebuild_corpus_state
        await _rebuild_corpus_state(notebook_id, user_id)

    logger.info("Deleted source %s", source_id)
    return True


async def retry_source(source_id: str, user_id: str) -> AddSourceResponse:
    """Retry a failed source."""
    source = await prisma.source.find_first(
        where={"id": source_id, "userId": user_id},
    )
    if not source:
        raise SourceNotFoundError(source_id)

    if source.status not in ("FAILED", "DEAD_LETTER"):
        raise SourceValidationError(f"Cannot retry source in status: {source.status}")

    # Reset source status
    await prisma.source.update(
        where={"id": source_id},
        data={
            "status": "QUEUED",
            "errorCode": None,
            "errorMessage": None,
            "extractionStatus": "PENDING",
            "indexingStatus": "PENDING",
        },
    )

    # Reset or create job
    job = await job_repository.get_job_by_source(source_id)
    if job:
        await job_repository.update_job_stage(
            str(job.id), "QUEUED", status="pending",
        )
        job_id = str(job.id)
    else:
        job_id = await job_repository.create_job(source_id, user_id)

    return AddSourceResponse(
        source_id=source_id,
        job_id=job_id,
        status=SourceStatus.QUEUED,
        message="Source re-queued for processing",
    )


async def get_context(
    notebook_id: str,
    user_id: str,
    query: str,
) -> GroundedContext:
    """Main context retrieval entry point — delegates to retrieval pipeline."""
    return await get_notebook_context(notebook_id, user_id, query)
