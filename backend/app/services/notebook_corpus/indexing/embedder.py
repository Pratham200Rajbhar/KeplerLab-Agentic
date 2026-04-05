"""Batch embedding service using sentence-transformers."""
from __future__ import annotations

import asyncio
import logging
from typing import List

from app.core.config import settings

logger = logging.getLogger(__name__)

_model = None
_model_lock = asyncio.Lock()


async def get_embedding_model():
    """Lazy-load the embedding model (singleton)."""
    global _model
    if _model is not None:
        return _model

    async with _model_lock:
        if _model is not None:
            return _model

        logger.info("Loading embedding model: %s", settings.EMBEDDING_MODEL)
        from sentence_transformers import SentenceTransformer
        _model = await asyncio.to_thread(
            SentenceTransformer,
            settings.EMBEDDING_MODEL,
            trust_remote_code=True,
        )
        logger.info("Embedding model loaded: dim=%d", _model.get_sentence_embedding_dimension())
        return _model


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of texts in batches.
    Returns list of embedding vectors (list of floats).
    """
    if not texts:
        return []

    model = await get_embedding_model()
    batch_size = settings.EMBED_BATCH_SIZE

    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        embeddings = await asyncio.to_thread(
            model.encode,
            batch,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        all_embeddings.extend(embeddings.tolist())

    return all_embeddings


async def embed_query(query: str) -> List[float]:
    """Embed a single query string."""
    result = await embed_texts([query])
    return result[0] if result else []
