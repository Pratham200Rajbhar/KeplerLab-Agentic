"""Job repository — DB operations for SourceJob CRUD."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

from app.db.prisma_client import prisma

logger = logging.getLogger(__name__)


async def create_job(source_id: str, user_id: str) -> str:
    """Create a new source processing job. Returns job ID."""
    job = await prisma.sourcejob.create(
        data={
            "sourceId": source_id,
            "userId": user_id,
            "stage": "QUEUED",
            "status": "pending",
        }
    )
    return str(job.id)


async def get_job(job_id: str):
    """Get a job by ID."""
    return await prisma.sourcejob.find_unique(where={"id": job_id})


async def get_job_by_source(source_id: str):
    """Get the job for a source."""
    return await prisma.sourcejob.find_unique(where={"sourceId": source_id})


async def get_pending_jobs(limit: int = 5) -> list:
    """Get jobs that are waiting to be processed."""
    return await prisma.sourcejob.find_many(
        where={"status": "pending", "stage": "QUEUED"},
        order={"createdAt": "asc"},
        take=limit,
    )


async def update_job_stage(
    job_id: str,
    stage: str,
    *,
    status: str = "processing",
    error: Optional[str] = None,
) -> None:
    """Update job stage and status."""
    data: dict = {
        "stage": stage,
        "status": status,
        "heartbeatAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc),
    }
    if error:
        data["lastError"] = error
    if stage == "QUEUED" and status == "pending":
        data["startedAt"] = None
    if status == "processing" and not data.get("startedAt"):
        data["startedAt"] = datetime.now(timezone.utc)
    if status in ("completed", "failed"):
        data["completedAt"] = datetime.now(timezone.utc)

    await prisma.sourcejob.update(where={"id": job_id}, data=data)


async def heartbeat(job_id: str) -> None:
    """Update the heartbeat timestamp."""
    await prisma.sourcejob.update(
        where={"id": job_id},
        data={"heartbeatAt": datetime.now(timezone.utc)},
    )


async def increment_retry(job_id: str) -> int:
    """Increment retry count and return new value."""
    job = await prisma.sourcejob.find_unique(where={"id": job_id})
    new_count = (job.retryCount if job else 0) + 1
    await prisma.sourcejob.update(
        where={"id": job_id},
        data={
            "retryCount": new_count,
            "stage": "QUEUED",
            "status": "pending",
            "startedAt": None,
            "completedAt": None,
        },
    )
    return new_count


async def get_stuck_jobs(timeout_minutes: int = 30) -> list:
    """Find jobs that have been running for too long without heartbeat."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)

    return await prisma.sourcejob.find_many(
        where={
            "status": "processing",
            "heartbeatAt": {"lt": cutoff},
        },
    )
