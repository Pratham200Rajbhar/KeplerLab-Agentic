from __future__ import annotations

import asyncio
import logging
import logging.handlers
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager

_LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")
os.makedirs(_LOG_DIR, exist_ok=True)

_fmt = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
_stream_handler = logging.StreamHandler(sys.stdout)
_stream_handler.setFormatter(_fmt)
_file_handler = logging.handlers.RotatingFileHandler(
    os.path.join(_LOG_DIR, "app.log"), maxBytes=10 * 1024 * 1024, backupCount=3
)
_file_handler.setFormatter(_fmt)

logging.basicConfig(level=logging.INFO, handlers=[_stream_handler, _file_handler])
for _noisy in ("httpx", "httpcore", "uvicorn.access"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.db.prisma_client import connect_db, disconnect_db

from app.routes.auth import router as auth_router
from app.routes.notebook import router as notebook_router
from app.routes.upload import router as upload_router
from app.routes.materials import router as materials_router
from app.routes.flashcard import router as flashcard_router
from app.routes.quiz import router as quiz_router
from app.routes.mindmap import router as mindmap_router
from app.routes.chat import router as chat_router
from app.routes.models import router as models_router
from app.routes.jobs import router as jobs_router
from app.routes.ppt import router as ppt_router
from app.routes.health import router as health_router
from app.routes.websocket_router import router as ws_router
from app.routes.search import router as search_router
from app.routes.proxy import router as proxy_router
from app.routes.explainer import router as explainer_router
from app.routes.podcast_live import router as podcast_live_router
from app.routes.code_execution import router as code_execution_router
from app.routes.artifacts import router as artifacts_router
from app.routes.ai_resource import router as ai_resource_router
from app.routes.skills import router as skills_router
from app.routes.learning import router as learning_router
from app.services.presentation.router import router as presentation_router

from app.services.rate_limiter import rate_limit_middleware
from app.services.performance_logger import performance_monitoring_middleware

logger = logging.getLogger("main")

_job_processor_task: asyncio.Task | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _job_processor_task

    await connect_db()

    loop = asyncio.get_running_loop()
    try:
        from app.services.rag.embedder import warm_up_embeddings
        logger.info("Warming up embedding model (running in thread pool)…")
        await loop.run_in_executor(None, warm_up_embeddings)
    except Exception as exc:
        logger.warning("Embedding warm-up failed (non-fatal, will retry on first use): %s", exc)

    try:
        from app.services.rag.reranker import get_reranker
        logger.info("Preloading reranker model (running in thread pool)…")
        await loop.run_in_executor(None, get_reranker)
        logger.info("Reranker preloaded.")
    except Exception as exc:
        logger.warning("Reranker preload failed (non-fatal, will load on first use): %s", exc)

    from app.services.worker import job_processor
    _job_processor_task = asyncio.create_task(job_processor(), name="job_processor")
    logger.info("Background job processor task created.")

    try:
        from app.services.code_execution.sandbox_env import ensure_packages
        logger.info("Ensuring sandbox packages are installed…")
        await ensure_packages()
    except Exception as exc:
        logger.warning("Sandbox package setup failed (non-fatal): %s", exc)

    try:
        import glob
        import shutil
        stale_dirs = glob.glob("/tmp/kepler_sandbox_*") + glob.glob("/tmp/kepler_analysis_*")
        if stale_dirs:
            for d in stale_dirs:
                shutil.rmtree(d, ignore_errors=True)
            logger.info("Cleaned up %d stale sandbox temp directories", len(stale_dirs))
    except Exception as exc:
        logger.warning("Sandbox temp cleanup failed (non-fatal): %s", exc)

    for _dir in [settings.GENERATED_OUTPUT_DIR, settings.PRESENTATIONS_OUTPUT_DIR, os.path.join(settings.GENERATED_OUTPUT_DIR, "..", "explainers"), os.path.join(settings.GENERATED_OUTPUT_DIR, "..", "podcast")]:
        os.makedirs(_dir, exist_ok=True)
    os.makedirs(settings.ARTIFACTS_DIR, exist_ok=True)
    logger.info("Output directories ensured.")

    try:
        from app.services.auth.service import cleanup_expired_tokens
        deleted = await cleanup_expired_tokens()
        if deleted:
            logger.info("Purged %d expired refresh token(s) on startup.", deleted)
    except Exception as exc:
        logger.warning("Expired token cleanup failed (non-fatal): %s", exc)

    yield

    if _job_processor_task and not _job_processor_task.done():
        from app.services.worker import graceful_shutdown, _SHUTDOWN_TIMEOUT
        await graceful_shutdown()
        _job_processor_task.cancel()
        try:
            await asyncio.wait_for(_job_processor_task, timeout=_SHUTDOWN_TIMEOUT)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
        logger.info("Background job processor stopped.")

    await disconnect_db()

app = FastAPI(lifespan=lifespan, title="Study Assistant API", version="2.0.0")

app.middleware("http")(performance_monitoring_middleware)

app.middleware("http")(rate_limit_middleware)

@app.middleware("http")
async def log_requests(request, call_next):
    request_id = uuid.uuid4().hex[:8]
    request.state.request_id = request_id
    start = time.time()
    try:
        response = await call_next(request)
        dt = time.time() - start
        logger.info("%s %s %s %.2fs [%s]", request.method, request.url.path, response.status_code, dt, request_id)
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as e:
        dt = time.time() - start
        logger.error("%s %s ERROR %s %.2fs [%s]", request.method, request.url.path, type(e).__name__, dt, request_id)
        raise

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

if settings.ENVIRONMENT == "production":
    from urllib.parse import urlparse as _urlparse
    _allowed_hosts = (
        [_urlparse(o).hostname for o in settings.CORS_ORIGINS if _urlparse(o).hostname]
        if settings.CORS_ORIGINS and settings.CORS_ORIGINS != ["*"]
        else ["*"]
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=_allowed_hosts or ["*"],
    )

def _cors_headers(origin: str | None = None) -> dict:
    allowed = origin if origin in settings.CORS_ORIGINS else (settings.CORS_ORIGINS[0] if settings.CORS_ORIGINS else "*")
    return {
        "Access-Control-Allow-Origin": allowed,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "*",
        "Access-Control-Allow-Headers": "*",
    }

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=_cors_headers(request.headers.get("origin")),
    )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.exception("Unhandled %s [request_id=%s]", type(exc).__name__, request_id)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
        headers=_cors_headers(request.headers.get("origin")),
    )

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(models_router)

app.include_router(notebook_router)
app.include_router(upload_router)
app.include_router(materials_router)
app.include_router(flashcard_router)
app.include_router(quiz_router)
app.include_router(mindmap_router)
app.include_router(chat_router)
app.include_router(jobs_router)
app.include_router(ppt_router)
app.include_router(presentation_router)
app.include_router(search_router)
app.include_router(proxy_router)
app.include_router(explainer_router)
app.include_router(podcast_live_router)
app.include_router(code_execution_router)
app.include_router(artifacts_router)
app.include_router(ai_resource_router)
app.include_router(skills_router)
app.include_router(learning_router)

app.include_router(ws_router)
