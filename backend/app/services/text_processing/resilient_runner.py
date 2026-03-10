from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

class ProcessingTimeoutError(Exception):
    pass

class ProcessingRetryExhaustedError(Exception):

    def __init__(self, task_name: str, attempts: int, last_error: Exception):
        self.task_name = task_name
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"{task_name} failed after {attempts} attempt(s): {last_error}"
        )

def run_with_timeout(
    fn: Callable[[], T],
    timeout: int,
    *,
    task_name: str = "task",
) -> T:
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(fn)
        try:
            return future.result(timeout=timeout)
        except FuturesTimeout:
            logger.error(
                "%s timed out after %d seconds", task_name, timeout
            )
            future.cancel()
            raise ProcessingTimeoutError(
                f"{task_name} timed out after {timeout} seconds"
            )

def run_with_retry(
    fn: Callable[[], T],
    timeout: int,
    *,
    max_retries: int = 2,
    task_name: str = "task",
    backoff_base: float = 1.0,
) -> T:
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                "%s attempt %d/%d (timeout=%ds)",
                task_name, attempt, max_retries, timeout,
            )
            return run_with_timeout(fn, timeout, task_name=task_name)

        except Exception as exc:
            last_error = exc
            logger.warning(
                "%s attempt %d/%d failed: %s",
                task_name, attempt, max_retries, exc,
            )
            if attempt < max_retries:
                sleep_secs = backoff_base * (2 ** (attempt - 1))
                logger.info(
                    "Retrying %s in %.1f seconds…", task_name, sleep_secs
                )
                time.sleep(sleep_secs)

    raise ProcessingRetryExhaustedError(task_name, max_retries, last_error)  # type: ignore[arg-type]
