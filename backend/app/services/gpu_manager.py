"""GPU resource manager — single asyncio.Lock as sole GPU gate.

All GPU access goes through ``gpu_session()`` async context manager.
Sync callers must acquire via:
    asyncio.run_coroutine_threadsafe(lock.acquire(), loop).result()
"""

import asyncio
import logging
from contextlib import asynccontextmanager

try:
    import torch
except ImportError:
    torch = None

logger = logging.getLogger(__name__)

# ── Single async Lock — the ONLY GPU gate ─────────────────────
_gpu_lock = asyncio.Lock()
_has_gpu: bool = torch is not None and torch.cuda.is_available()

if _has_gpu:
    logger.info("GPUManager: Found %s", torch.cuda.get_device_name(0))
else:
    logger.info("GPUManager: No CUDA GPU detected")


def _clear_memory() -> None:
    """Aggressive GPU memory cleanup."""
    if _has_gpu:
        try:
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        except Exception as e:
            logger.warning("Failed to clear GPU memory: %s", e)


@asynccontextmanager
async def gpu_session(task_name: str = "Generic Task"):
    """Async-only context manager for exclusive GPU access.

    Usage:
        async with gpu_session("Embedding"):
            ...
    """
    if not _has_gpu:
        yield
        return

    logger.info("Waiting for GPU lock: %s", task_name)
    async with _gpu_lock:
        logger.info("Acquired GPU lock: %s", task_name)
        try:
            _clear_memory()
            yield
        finally:
            _clear_memory()
            logger.info("Released GPU lock: %s", task_name)


def get_gpu_lock() -> asyncio.Lock:
    """Return the singleton GPU lock for sync callers that need
    ``asyncio.run_coroutine_threadsafe(lock.acquire(), loop).result()``."""
    return _gpu_lock


def has_gpu() -> bool:
    """Whether a CUDA GPU is available."""
    return _has_gpu
