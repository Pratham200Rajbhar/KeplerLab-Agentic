"""Source processing worker — polls for pending jobs and processes them."""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from app.core.config import settings
from app.db.prisma_client import prisma
from app.services.notebook_corpus.chunking.chunker_factory import chunk_content
from app.services.notebook_corpus.enums import SourceType
from app.services.notebook_corpus.errors import PermanentError, TransientError
from app.services.notebook_corpus.indexing.index_manager import index_chunks
from app.services.notebook_corpus.processors import get_processor
from app.services.notebook_corpus.retrieval.corpus_router import select_retrieval_mode

from . import job_repository

logger = logging.getLogger(__name__)

_running = False
_worker_task: asyncio.Task | None = None


async def start_worker() -> None:
    """Start the background worker loop."""
    global _running, _worker_task
    if _running:
        return
    _running = True
    _worker_task = asyncio.create_task(_worker_loop(), name="source_job_worker")
    logger.info("Source job worker started")


async def stop_worker() -> None:
    """Stop the background worker."""
    global _running, _worker_task
    _running = False
    if _worker_task:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
        _worker_task = None
    logger.info("Source job worker stopped")


async def _worker_loop() -> None:
    """Main worker polling loop."""
    while _running:
        try:
            jobs = await job_repository.get_pending_jobs(limit=settings.JOB_MAX_CONCURRENT)

            if jobs:
                tasks = [_process_job(job) for job in jobs]
                await asyncio.gather(*tasks, return_exceptions=True)
            else:
                await asyncio.sleep(settings.JOB_WORKER_POLL_SECONDS)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Worker loop error: %s", e)
            await asyncio.sleep(settings.JOB_WORKER_POLL_SECONDS)


async def _process_job(job) -> None:
    """Process a single source job through the full pipeline."""
    job_id = str(job.id)
    source_id = str(job.sourceId)
    start_time = time.monotonic()

    logger.info("Processing job %s for source %s", job_id, source_id)

    try:
        # Load source
        source = await prisma.source.find_unique(where={"id": source_id})
        if not source:
            await job_repository.update_job_stage(job_id, "FAILED", status="failed", error="Source not found")
            return

        source_type = SourceType(source.sourceType)
        processor = get_processor(source_type)

        # Build source_data dict from DB record
        source_data = {
            "source_id": source_id,
            "source_type": source.sourceType,
            "filename": source.originalName or "",
            "size_bytes": source.sizeBytes or 0,
            "mime_type": source.mimeType or "",
            "text": source.inputText or "",
            "url": source.inputUrl or "",
            "note_content": source.inputText or "",
            "local_file_path": source.localFilePath or "",
            "title": source.title or "",
        }

        # Stage: VALIDATING
        await job_repository.update_job_stage(job_id, "VALIDATING")
        await prisma.source.update(where={"id": source_id}, data={"status": "VALIDATING", "extractionStatus": "IN_PROGRESS"})

        # Stage: EXTRACTING
        await job_repository.update_job_stage(job_id, "EXTRACTING")
        await prisma.source.update(where={"id": source_id}, data={"status": "EXTRACTING"})

        extracted, metadata = await processor.process(source_data=source_data)
        await job_repository.heartbeat(job_id)

        # Stage: NORMALIZING — update source with extracted content
        await job_repository.update_job_stage(job_id, "NORMALIZING")
        await prisma.source.update(
            where={"id": source_id},
            data={
                "status": "NORMALIZING",
                "extractedText": extracted.text,
                "extractedMetadata": metadata,
                "tokenCount": extracted.token_count,
                "fingerprint": source_data.get("fingerprint", ""),
                "extractionStatus": "COMPLETE",
                "warningCount": len(extracted.warnings),
                "warningMessages": extracted.warnings if extracted.warnings else None,
            },
        )

        # Stage: CORPUS_BUILDING — chunk the content
        await job_repository.update_job_stage(job_id, "CORPUS_BUILDING")
        await prisma.source.update(where={"id": source_id}, data={"status": "CORPUS_BUILDING"})

        chunk_result = chunk_content(extracted, source_id)
        await job_repository.heartbeat(job_id)

        # Stage: INDEXING — embed and index chunks
        await job_repository.update_job_stage(job_id, "INDEXING")
        await prisma.source.update(where={"id": source_id}, data={"status": "INDEXING", "indexingStatus": "IN_PROGRESS"})

        notebook_id = source.notebookId or ""
        if notebook_id and chunk_result.chunks:
            await index_chunks(source_id, notebook_id, chunk_result.chunks)

        # Stage: READY
        await job_repository.update_job_stage(job_id, "READY", status="completed")
        await prisma.source.update(
            where={"id": source_id},
            data={
                "status": "READY",
                "readinessStatus": "READY",
                "indexingStatus": "COMPLETE",
                "processedAt": datetime.now(timezone.utc),
            },
        )

        # Rebuild corpus state for the notebook
        if notebook_id:
            await _rebuild_corpus_state(notebook_id, source.userId)

        elapsed = time.monotonic() - start_time
        logger.info(
            "Job %s completed in %.1fs — source=%s chunks=%d tokens=%d",
            job_id, elapsed, source_id, len(chunk_result.chunks), extracted.token_count,
        )

    except TransientError as e:
        logger.warning("Transient error for job %s: %s", job_id, e)
        retry_count = await job_repository.increment_retry(job_id)
        if retry_count > settings.SOURCE_MAX_RETRIES:
            await _fail_job(job_id, source_id, str(e), dead_letter=True)
        else:
            await prisma.source.update(
                where={"id": source_id},
                data={"status": "QUEUED", "errorMessage": str(e)},
            )

    except PermanentError as e:
        logger.error("Permanent error for job %s: %s", job_id, e)
        await _fail_job(job_id, source_id, str(e), dead_letter=True)

    except Exception as e:
        logger.exception("Unexpected error for job %s: %s", job_id, e)
        retry_count = await job_repository.increment_retry(job_id)
        if retry_count > settings.SOURCE_MAX_RETRIES:
            await _fail_job(job_id, source_id, str(e), dead_letter=True)
        else:
            await prisma.source.update(
                where={"id": source_id},
                data={"status": "QUEUED", "errorMessage": str(e)},
            )


async def _fail_job(job_id: str, source_id: str, error: str, *, dead_letter: bool = False) -> None:
    """Mark a job and its source as failed."""
    stage = "DEAD_LETTER" if dead_letter else "FAILED"
    status = "DEAD_LETTER" if dead_letter else "FAILED"

    await job_repository.update_job_stage(job_id, stage, status="failed", error=error)
    await prisma.source.update(
        where={"id": source_id},
        data={
            "status": status,
            "errorMessage": error[:2000],
            "errorCode": "PERMANENT" if dead_letter else "FAILED",
        },
    )


async def _rebuild_corpus_state(notebook_id: str, user_id: str) -> None:
    """Recalculate and persist notebook-level corpus stats."""
    sources = await prisma.source.find_many(
        where={"notebookId": notebook_id, "userId": user_id, "status": "READY"},
    )

    total_tokens = sum(s.tokenCount for s in sources)
    source_count = len(sources)
    mode = select_retrieval_mode(total_tokens, source_count)

    await prisma.notebookcorpusstate.upsert(
        where={"notebookId": notebook_id},
        data={
            "create": {
                "notebookId": notebook_id,
                "userId": user_id,
                "totalTokens": total_tokens,
                "sourceCount": source_count,
                "readyCount": source_count,
                "retrievalMode": mode.value,
                "lastRebuiltAt": datetime.now(timezone.utc),
            },
            "update": {
                "totalTokens": total_tokens,
                "sourceCount": source_count,
                "readyCount": source_count,
                "retrievalMode": mode.value,
                "lastRebuiltAt": datetime.now(timezone.utc),
            },
        },
    )
