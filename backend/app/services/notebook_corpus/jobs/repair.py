"""Stuck job repair — recover jobs that are stuck in processing."""
from __future__ import annotations

import logging

from app.core.config import settings
from app.db.prisma_client import prisma

from . import job_repository

logger = logging.getLogger(__name__)


async def repair_stuck_jobs() -> int:
    """
    Find and recover stuck jobs on startup.
    Jobs stuck in 'processing' state beyond the timeout are reset to 'pending'.
    Returns the number of repaired jobs.
    """
    stuck_jobs = await job_repository.get_stuck_jobs(
        timeout_minutes=settings.STUCK_JOB_TIMEOUT_MINUTES
    )

    repaired = 0
    for job in stuck_jobs:
        try:
            if job.retryCount >= settings.SOURCE_MAX_RETRIES:
                # Too many retries — dead-letter it
                await job_repository.update_job_stage(
                    str(job.id), "DEAD_LETTER", status="failed",
                    error="Stuck job exceeded max retries",
                )
                await prisma.source.update(
                    where={"id": str(job.sourceId)},
                    data={
                        "status": "DEAD_LETTER",
                        "errorCode": "STUCK_JOB",
                        "errorMessage": "Job was stuck and exceeded max retries",
                    },
                )
                logger.warning("Dead-lettered stuck job %s (retries=%d)", job.id, job.retryCount)
            else:
                # Reset to pending for retry
                await job_repository.increment_retry(str(job.id))
                await prisma.source.update(
                    where={"id": str(job.sourceId)},
                    data={"status": "QUEUED", "errorMessage": "Job was stuck and has been reset"},
                )
                logger.info("Repaired stuck job %s, retry #%d", job.id, job.retryCount + 1)

            repaired += 1
        except Exception as e:
            logger.error("Failed to repair stuck job %s: %s", job.id, e)

    if repaired:
        logger.info("Repaired %d stuck jobs", repaired)
    return repaired
