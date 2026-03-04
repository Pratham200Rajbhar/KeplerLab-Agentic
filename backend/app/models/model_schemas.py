"""Schemas and registry for non-LLM AI models (embedding, reranker, whisper).

All AI model configurations used by the backend are defined here so that
model_manager, rag services, and API routes share one source of truth.

Usage:
    from app.models.model_schemas import REQUIRED_MODELS, ModelConfig, ModelStatus
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Literal, Optional
from pydantic import BaseModel, Field

from app.core.config import settings


# ── Local path helper ─────────────────────────────────────────────────────────

def get_local_model_path(name: str) -> Path:
    """Return the directory where a model is stored inside MODELS_DIR.

    Convention: ``{MODELS_DIR}/{name.replace("/", "--")}``
    e.g. ``data/models/BAAI--bge-m3``

    A model is considered locally available when this directory exists
    *and* contains at least one file.
    """
    return Path(settings.MODELS_DIR) / name.replace("/", "--")


def is_model_local(name: str) -> bool:
    """Return True when the model has been downloaded to MODELS_DIR.

    Checks both the direct ``model.save()`` path and the HuggingFace hub
    cache path (``models--{name}``), since both conventions are used.
    """
    p = get_local_model_path(name)
    hf = Path(settings.MODELS_DIR) / f"models--{name.replace('/', '--')}"
    return (
        (p.is_dir() and any(p.iterdir()))
        or (hf.is_dir() and any(hf.iterdir()))
    )


# ── Per-model configuration schema ───────────────────────────────────────────

class ModelConfig(BaseModel):
    """Configuration for a single downloadable/cacheable AI model."""

    name: str = Field(description="HuggingFace model ID or local path")
    type: Literal["sentence_transformer", "cross_encoder", "whisper", "tts"] = Field(
        description="Model type — determines which loader is used"
    )
    required: bool = Field(
        default=True,
        description="If True, a missing model blocks app startup",
    )
    description: str = Field(default="", description="Human-readable purpose")
    fallback_name: Optional[str] = Field(
        default=None,
        description="Smaller model to use when running on CPU only",
    )


# ── Registry ─────────────────────────────────────────────────────────────────

#: All non-LLM models the application requires.
#: model_manager iterates this dict to download / verify models on startup.
REQUIRED_MODELS: Dict[str, ModelConfig] = {
    "embedding": ModelConfig(
        name=settings.EMBEDDING_MODEL,
        type="sentence_transformer",
        required=True,
        description="Dense vector embeddings for semantic search (BGE-M3, 1024-dim)",
    ),
    "reranker": ModelConfig(
        name=settings.RERANKER_MODEL,
        type="cross_encoder",
        required=False,          # gracefully disabled when USE_RERANKER=False
        description="Cross-encoder reranker for precision retrieval (BGE Reranker Large)",
        fallback_name="BAAI/bge-reranker-base",  # used automatically on CPU
    ),
}


# ── API response schemas ──────────────────────────────────────────────────────

class ModelStatus(BaseModel):
    """Per-model status returned by GET /models/status."""

    name: str
    type: str
    required: bool
    description: str
    available: bool
    status: Literal["ready", "missing"]


class ModelsSummary(BaseModel):
    total: int
    ready: int
    missing: int


class ModelsStatusResponse(BaseModel):
    """Full response body for GET /models/status."""

    models_directory: str
    cache_size: str
    models: Dict[str, ModelStatus]
    summary: ModelsSummary


class ModelsReloadResponse(BaseModel):
    """Response body for POST /models/reload."""

    message: str
    results: Dict[str, bool]
    success: bool
