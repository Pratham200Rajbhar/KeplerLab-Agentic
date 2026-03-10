from __future__ import annotations

import logging
import threading
import time
from contextlib import nullcontext
from typing import List, Tuple, Optional
import torch

from app.core.config import settings
from app.models.model_schemas import get_local_model_path, is_model_local

logger = logging.getLogger(__name__)

_reranker = None
_reranker_lock = threading.Lock()

_RERANKER_BATCH_SIZE = 16
_MAX_LENGTH = 512

def get_reranker():
    global _reranker
    if _reranker is None:
        with _reranker_lock:
            if _reranker is None:
                try:
                    from sentence_transformers import CrossEncoder
                    
                    start_time = time.time()
                    device = "cuda" if torch.cuda.is_available() else "cpu"
                    
                    model_name = settings.RERANKER_MODEL
                    if device == "cpu" and "large" in model_name:
                        model_name = "BAAI/bge-reranker-base"
                        logger.info("No GPU detected, using bge-reranker-base instead of large")

                    load_path = (
                        str(get_local_model_path(model_name))
                        if is_model_local(model_name)
                        else model_name
                    )
                    logger.info(
                        "Loading reranker: %s on %s (source: %s)",
                        model_name, device,
                        "local" if is_model_local(model_name) else "HuggingFace hub",
                    )

                    _reranker = CrossEncoder(
                        load_path,
                        device=device,
                        max_length=_MAX_LENGTH,
                        trust_remote_code=False,
                    )
                    
                    if device == "cuda":
                        with torch.inference_mode():
                            _reranker.predict([["warmup query", "warmup document"]], show_progress_bar=False)
                        logger.info("Reranker warm-up forward pass complete")
                    
                    load_time = time.time() - start_time
                    logger.info("Reranker loaded successfully in %.2fs", load_time)
                    
                except Exception as e:
                    logger.error("Failed to load reranker: %s", e)
                    _reranker = None
    
    return _reranker

def rerank_chunks(
    query: str,
    chunks: List[str],
    top_k: Optional[int] = None,
) -> List[Tuple[str, float]]:
    if not chunks:
        return []
    
    if not settings.USE_RERANKER:
        logger.debug("Reranker disabled, returning chunks as-is")
        return [(c, 1.0) for c in chunks[:top_k]] if top_k else [(c, 1.0) for c in chunks]
    
    reranker = get_reranker()
    if reranker is None:
        logger.warning("Reranker not available, returning chunks without reranking")
        return [(c, 1.0) for c in chunks[:top_k]] if top_k else [(c, 1.0) for c in chunks]
    
    try:
        start_time = time.time()
        pairs = [[query, chunk] for chunk in chunks]
        
        with torch.inference_mode():
            device_type = "cuda" if torch.cuda.is_available() else "cpu"
            ctx = torch.autocast(device_type=device_type, dtype=torch.float16) if device_type == "cuda" else nullcontext()
            
            try:
                with ctx:
                    scores = reranker.predict(
                        pairs,
                        batch_size=min(_RERANKER_BATCH_SIZE, len(pairs)),
                        show_progress_bar=False,
                    )
            except RuntimeError as e:
                if "out of memory" in str(e).lower():
                    logger.warning("GPU OOM during reranking, falling back to CPU")
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    scores = reranker.predict(
                        pairs,
                        batch_size=max(1, _RERANKER_BATCH_SIZE // 4),
                        show_progress_bar=False,
                    )
                else:
                    raise
        
        elapsed = time.time() - start_time
        
        chunk_scores = list(zip(chunks, scores))
        chunk_scores.sort(key=lambda x: x[1], reverse=True)
        
        if top_k:
            chunk_scores = chunk_scores[:top_k]
        
        if elapsed > 0:
            logger.debug(
                "Reranked %d chunks in %.2fs (%.1f chunks/sec), returning top %d",
                len(chunks), elapsed, len(chunks) / elapsed, len(chunk_scores),
            )
        
        return chunk_scores
        
    except Exception as e:
        logger.error("Reranking failed: %s, returning original chunks", e)
        return [(c, 1.0) for c in chunks[:top_k]] if top_k else [(c, 1.0) for c in chunks]
