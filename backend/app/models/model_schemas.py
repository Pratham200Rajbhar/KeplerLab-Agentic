from __future__ import annotations

from pathlib import Path
from typing import Dict, Literal, Optional
from pydantic import BaseModel, Field

from app.core.config import settings

def get_local_model_path(name: str) -> Path:
    return Path(settings.MODELS_DIR) / name.replace("/", "--")

def is_model_local(name: str) -> bool:
    p = get_local_model_path(name)
    hf = Path(settings.MODELS_DIR) / f"models--{name.replace('/', '--')}"
    return (
        (p.is_dir() and any(p.iterdir()))
        or (hf.is_dir() and any(hf.iterdir()))
    )

class ModelConfig(BaseModel):

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
        required=False,
        description="Cross-encoder reranker for precision retrieval (BGE Reranker Large)",
        fallback_name="BAAI/bge-reranker-base",
    ),
}

class ModelStatus(BaseModel):

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

    models_directory: str
    cache_size: str
    models: Dict[str, ModelStatus]
    summary: ModelsSummary

class ModelsReloadResponse(BaseModel):

    message: str
    results: Dict[str, bool]
    success: bool
