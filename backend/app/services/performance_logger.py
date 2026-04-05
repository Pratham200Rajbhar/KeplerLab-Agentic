from __future__ import annotations

import time
import logging
from typing import Optional, Dict
from contextvars import ContextVar
from fastapi import Request

logger = logging.getLogger(__name__)
perf_logger = logging.getLogger("performance")

_request_start_time: ContextVar[float] = ContextVar("request_start_time")
_retrieval_time: ContextVar[float] = ContextVar("retrieval_time", default=0.0)
_reranking_time: ContextVar[float] = ContextVar("reranking_time", default=0.0)
_llm_time: ContextVar[float] = ContextVar("llm_time", default=0.0)
_retrieval_trace: ContextVar[Dict[str, float | int | str]] = ContextVar("retrieval_trace", default={})

# --- Prometheus Metrics (Optional) ---
from app.core.config import settings

hist_request_duration = None
hist_retrieval_duration = None
hist_reranking_duration = None
hist_llm_duration = None

if settings.ENABLE_PROMETHEUS:
    try:
        from prometheus_client import Histogram
        hist_request_duration = Histogram(
            "request_duration_seconds",
            "Total request duration in seconds",
            ["method", "endpoint", "status"]
        )
        hist_retrieval_duration = Histogram(
            "retrieval_duration_seconds",
            "RAG retrieval duration in seconds"
        )
        hist_reranking_duration = Histogram(
            "reranking_duration_seconds",
            "RAG reranking duration in seconds"
        )
        hist_llm_duration = Histogram(
            "llm_duration_seconds",
            "LLM generation duration in seconds"
        )
    except ImportError:
        logger.warning("prometheus_client not installed, skipping metrics")

def set_request_start_time() -> None:
    _request_start_time.set(time.time())

def get_request_elapsed_time() -> float:
    try:
        start = _request_start_time.get()
        return time.time() - start
    except LookupError:
        return 0.0

def record_retrieval_time(seconds: float) -> None:
    _retrieval_time.set(seconds)
    if hist_retrieval_duration:
        hist_retrieval_duration.observe(seconds)
    logger.debug(f"Retrieval completed in {seconds:.3f}s")

def record_reranking_time(seconds: float) -> None:
    _reranking_time.set(seconds)
    if hist_reranking_duration:
        hist_reranking_duration.observe(seconds)
    logger.debug(f"Reranking completed in {seconds:.3f}s")

def record_llm_time(seconds: float) -> None:
    _llm_time.set(seconds)
    if hist_llm_duration:
        hist_llm_duration.observe(seconds)
    logger.debug(f"LLM generation completed in {seconds:.3f}s")


def record_retrieval_trace(trace: Dict[str, float | int | str]) -> None:
    _retrieval_trace.set(trace)
    logger.debug("Retrieval trace recorded: %s", trace)

def get_performance_metrics() -> Dict[str, float]:
    try:
        total_time = get_request_elapsed_time()
        retrieval = _retrieval_time.get()
        reranking = _reranking_time.get()
        llm = _llm_time.get()
        trace = _retrieval_trace.get()
    except LookupError:
        return {
            "retrieval_time": 0.0,
            "reranking_time": 0.0,
            "llm_time": 0.0,
            "total_time": 0.0,
        }

    base = {
        "retrieval_time": retrieval,
        "reranking_time": reranking,
        "llm_time": llm,
        "total_time": total_time,
    }
    if trace:
        for key, value in trace.items():
            base[f"retrieval_{key}"] = value
    return base

def log_performance_metrics(
    endpoint: str,
    method: str,
    status_code: int,
    user_id: Optional[str] = None,
) -> None:
    metrics = get_performance_metrics()
    
    known_time = (
        metrics["retrieval_time"] +
        metrics["reranking_time"] +
        metrics["llm_time"]
    )
    other_time = max(0.0, metrics["total_time"] - known_time)
    
    perf_logger.info(
        "request_performance",
        extra={
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "user_id": user_id or "anonymous",
            "total_time": round(metrics["total_time"], 3),
            "retrieval_time": round(metrics["retrieval_time"], 3),
            "reranking_time": round(metrics["reranking_time"], 3),
            "llm_time": round(metrics["llm_time"], 3),
            "other_time": round(other_time, 3),
        }
    )

async def performance_monitoring_middleware(request: Request, call_next):
    set_request_start_time()
    
    response = await call_next(request)
    
    total_time = get_request_elapsed_time()
    
    user_id = getattr(request.state, "user_id", None)
    
    if any(x in request.url.path for x in ["/chat", "/flashcard", "/quiz", "/ppt", "/notebook"]):
        log_performance_metrics(
            endpoint=request.url.path,
            method=request.method,
            status_code=response.status_code,
            user_id=user_id,
        )
    
    from app.core.config import settings
    if settings.ENVIRONMENT == "development":
        metrics = get_performance_metrics()
        response.headers["X-Response-Time"] = f"{total_time:.3f}s"
        if metrics["retrieval_time"] > 0:
            response.headers["X-Retrieval-Time"] = f"{metrics['retrieval_time']:.3f}s"
        if metrics["reranking_time"] > 0:
            response.headers["X-Reranking-Time"] = f"{metrics['reranking_time']:.3f}s"
        if metrics["llm_time"] > 0:
            response.headers["X-LLM-Time"] = f"{metrics['llm_time']:.3f}s"
    
    if hist_request_duration:
        hist_request_duration.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).observe(total_time)

    return response

class PerformanceTimer:
    
    def __init__(self):
        self.start_time: float = 0.0
        self.elapsed: float = 0.0
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed = time.time() - self.start_time
        return False
