from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone

from app.db.prisma_client import prisma
from app.services.job_service import fetch_next_pending_job
from app.services.material_service import (
    process_material_by_id,
    process_url_material_by_id,
    process_text_material_by_id,
)

logger = logging.getLogger(__name__)

_POLL_SECONDS: float = 2.0
_ERROR_BACKOFF: float = 5.0
MAX_CONCURRENT_JOBS: int = 5
_STUCK_JOB_TIMEOUT_MINUTES: int = 30
_SHUTDOWN_TIMEOUT: float = 30.0

_shutdown_event = asyncio.Event()

async def _recover_stuck_jobs() -> None:
    try:
        result = await prisma.query_raw(
            """
            UPDATE background_jobs
            SET    status     = 'pending',
                   updated_at = NOW(),
                   error      = 'Auto-reset: stuck in processing after server restart'
            WHERE  status     = 'processing'
              AND  updated_at < NOW() - INTERVAL '1 minute' * $1::int
            RETURNING id
            """,
            _STUCK_JOB_TIMEOUT_MINUTES,
        )
        if result:
            logger.warning(
                "[WORKER] Recovered %d stuck job(s) → reset to pending: %s",
                len(result), [r["id"] for r in result],
            )
    except Exception as exc:
        logger.warning("[WORKER] Stuck job recovery failed (non-fatal): %s", exc)

class _JobQueue:

    def __init__(self):
        self._event = asyncio.Event()

    def notify(self):
        self._event.set()

    async def wait(self, timeout: float = _POLL_SECONDS):
        try:
            await asyncio.wait_for(self._event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass
        self._event.clear()

job_queue = _JobQueue()

async def job_processor() -> None:
    logger.info("Background job processor started (poll_interval=%.1fs, concurrent_limit=%d)", _POLL_SECONDS, MAX_CONCURRENT_JOBS)

    await _recover_stuck_jobs()

    cleanup_task = asyncio.create_task(_cleanup_old_jobs())

    active_tasks: set[asyncio.Task] = set()

    while not _shutdown_event.is_set():
        try:
            done = {t for t in active_tasks if t.done()}
            for t in done:
                active_tasks.remove(t)
                try:
                    await t
                except Exception as e:
                    logger.exception("Task explicitly failed inside worker pool: %s", e)

            jobs_to_fetch = MAX_CONCURRENT_JOBS - len(active_tasks)
            jobs_added = 0

            if jobs_to_fetch > 0 and not _shutdown_event.is_set():
                for _ in range(jobs_to_fetch):
                    job = await fetch_next_pending_job("material_processing")
                    if not job:
                        break
                    
                    task = asyncio.create_task(_process_job(job))
                    active_tasks.add(task)
                    jobs_added += 1

            if not active_tasks:
                await job_queue.wait(timeout=_POLL_SECONDS)
            else:
                if len(active_tasks) >= MAX_CONCURRENT_JOBS or jobs_added == 0:
                     await asyncio.wait(active_tasks, return_when=asyncio.FIRST_COMPLETED)

        except Exception as exc:
            logger.exception("Unhandled error in job_processor event loop: %s", exc)
            await asyncio.sleep(_ERROR_BACKOFF)

    cleanup_task.cancel()
    if active_tasks:
        logger.info("Waiting for %d in-flight job(s) to complete...", len(active_tasks))
        try:
            await asyncio.wait_for(
                asyncio.gather(*active_tasks, return_exceptions=True),
                timeout=_SHUTDOWN_TIMEOUT,
            )
        except asyncio.TimeoutError:
            logger.warning("Shutdown timeout — %d job(s) still running", len([t for t in active_tasks if not t.done()]))
    logger.info("Job processor loop exited.")

async def _process_job(job) -> None:
    payload: dict = job.result or {}
    material_id: str | None = payload.get("material_id")
    user_id: str | None = payload.get("user_id")
    notebook_id: str | None = payload.get("notebook_id")
    source_type: str = payload.get("source_type", "file")

    if not material_id or not user_id:
        logger.error(
            "Job %s has incomplete payload — marking failed.  payload=%s",
            job.id, payload,
        )
        await _fail_job(job.id, "Incomplete job payload: missing material_id or user_id")
        return

    logger.info(
        "Processing job %s | material=%s type=%s user=%s",
        job.id, material_id, source_type, user_id,
    )
    _t_job = time.perf_counter()

    try:
        if source_type == "file":
            file_path: str | None = payload.get("file_path")
            filename: str = payload.get("filename", "unknown")
            if not file_path:
                raise ValueError("Missing file_path for file source_type")
            await process_material_by_id(
                material_id=material_id,
                file_path=file_path,
                filename=filename,
                user_id=user_id,
                notebook_id=notebook_id,
            )
        elif source_type in ("url", "web", "youtube"):
            url: str | None = payload.get("url")
            if not url:
                raise ValueError("Missing url for url source_type")
            await process_url_material_by_id(
                material_id=material_id,
                url=url,
                user_id=user_id,
                notebook_id=notebook_id,
                source_type=source_type,
            )
        elif source_type == "text":
            text: str | None = payload.get("text")
            title: str = payload.get("title", "unknown")
            if not text:
                raise ValueError("Missing text content for text source_type")
            await process_text_material_by_id(
                material_id=material_id,
                text_content=text,
                title=title,
                user_id=user_id,
                notebook_id=notebook_id,
            )
        else:
            raise ValueError(f"Unknown source_type: {source_type}")
        job_processing_time = (time.perf_counter() - _t_job) * 1000
        await prisma.backgroundjob.update(
            where={"id": job.id},
            data={"status": "completed"},
        )
        logger.info(
            "[WORKER] job_processing_time=%.1fms  job=%s  material=%s  status=completed",
            job_processing_time, job.id, material_id,
        )
        if notebook_id:
            await _maybe_rename_notebook(notebook_id, material_id)
    except Exception as exc:
        job_processing_time = (time.perf_counter() - _t_job) * 1000
        logger.exception(
            "[WORKER] job_processing_time=%.1fms  job=%s  material=%s  status=failed  error=%s",
            job_processing_time, job.id, material_id, exc,
        )
        await _fail_job(job.id, str(exc))

async def _fail_job(job_id: str, error: str) -> None:
    try:
        await prisma.backgroundjob.update(
            where={"id": job_id},
            data={"status": "failed", "error": error},
        )
    except Exception as exc:
        logger.error("Could not mark job %s as failed: %s", job_id, exc)

_AUTO_NAME_PREFIXES = ("notebook ", "untitled")

async def _maybe_rename_notebook(notebook_id: str, material_id: str) -> None:
    if notebook_id == "draft":
        return

    try:
        notebook = await prisma.notebook.find_unique(where={"id": notebook_id})
        if notebook is None:
            return

        current_name: str = (notebook.name or "").strip()

        if not any(current_name.lower().startswith(p) for p in _AUTO_NAME_PREFIXES):
            return

        loop = asyncio.get_running_loop()
        from functools import partial
        from app.services.storage_service import load_material_text
        text: str = await loop.run_in_executor(
            None, partial(load_material_text, material_id)
        ) or ""
        if len(text.strip()) < 30:
            return

        from app.services.notebook_name_generator import generate_notebook_name
        new_name: str = await loop.run_in_executor(
            None, partial(generate_notebook_name, text[:2000], None)
        )
        if not new_name or len(new_name) < 3 or new_name == current_name:
            return

        await prisma.notebook.update(
            where={"id": notebook_id},
            data={"name": new_name},
        )
        logger.info(
            "[WORKER] notebook_renamed  id=%s  old='%s'  new='%s'",
            notebook_id, current_name, new_name,
        )
    except Exception as exc:
        logger.warning("[WORKER] _maybe_rename_notebook failed (non-fatal): %s", exc)

async def graceful_shutdown() -> None:
    _shutdown_event.set()
    logger.info("Worker shutdown signal sent — waiting up to %.0fs for in-flight jobs", _SHUTDOWN_TIMEOUT)

_CLEANUP_INTERVAL_HOURS: int = 24
_CLEANUP_RETENTION_DAYS: int = 30

async def _cleanup_old_jobs() -> None:
    while not _shutdown_event.is_set():
        try:
            await asyncio.sleep(_CLEANUP_INTERVAL_HOURS * 3600)
        except asyncio.CancelledError:
            return

        if _shutdown_event.is_set():
            return

        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=_CLEANUP_RETENTION_DAYS)
            deleted = await prisma.backgroundjob.delete_many(
                where={
                    "status": {"in": ["completed", "failed"]},
                    "createdAt": {"lt": cutoff},
                },
            )
            if deleted:
                logger.info(
                    "[WORKER] Cleaned up %d old job record(s) (older than %d days)",
                    deleted, _CLEANUP_RETENTION_DAYS,
                )
        except Exception as exc:
            logger.warning("[WORKER] Job cleanup cron failed (non-fatal): %s", exc)
