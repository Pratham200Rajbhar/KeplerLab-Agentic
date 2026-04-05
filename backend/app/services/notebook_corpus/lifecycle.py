"""Lifecycle management — startup and shutdown hooks for the corpus system."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def startup() -> None:
    """
    Called during app startup (lifespan).
    - Recover stuck jobs
    - Start the job worker
    """
    logger.info("Notebook corpus pipeline starting up...")

    # 1. Repair stuck jobs from previous shutdown
    try:
        from app.services.notebook_corpus.jobs.repair import repair_stuck_jobs
        repaired = await repair_stuck_jobs()
        if repaired:
            logger.info("Repaired %d stuck source jobs", repaired)
    except Exception as e:
        logger.error("Failed to repair stuck jobs: %s", e)

    # 2. Start the background worker
    try:
        from app.services.notebook_corpus.jobs.worker import start_worker
        await start_worker()
        logger.info("Source job worker started")
    except Exception as e:
        logger.error("Failed to start job worker: %s", e)

    logger.info("Notebook corpus pipeline ready")


async def shutdown() -> None:
    """
    Called during app shutdown (lifespan).
    - Stop the job worker gracefully
    """
    logger.info("Notebook corpus pipeline shutting down...")

    try:
        from app.services.notebook_corpus.jobs.worker import stop_worker
        await stop_worker()
    except Exception as e:
        logger.error("Error stopping job worker: %s", e)

    logger.info("Notebook corpus pipeline stopped")
