from __future__ import annotations

import logging
import threading
import time
import re
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
_MAX_RERANK_CHARS = 2200


def _trim_chunk_for_rerank(query: str, chunk: str, max_chars: int = _MAX_RERANK_CHARS) -> str:
    """Trim chunk around query-relevant spans so cross-encoder truncation keeps signal."""
    if len(chunk) <= max_chars:
        return chunk

    query_terms = [t for t in re.findall(r"[a-zA-Z0-9_]{3,}", query.lower()) if t]
    if not query_terms:
        return chunk[:max_chars]

    lower = chunk.lower()
    positions = [lower.find(term) for term in query_terms if lower.find(term) >= 0]
    if not positions:
        return chunk[:max_chars]

    center = int(sum(positions) / max(1, len(positions)))
    half = max_chars // 2
    start = max(0, center - half)
    end = min(len(chunk), start + max_chars)
    if end - start < max_chars:
        start = max(0, end - max_chars)

    trimmed = chunk[start:end].strip()
    if start > 0:
        trimmed = "... " + trimmed
    if end < len(chunk):
        trimmed = trimmed + " ..."
    return trimmed

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
        trimmed_chunks = [_trim_chunk_for_rerank(query, c) for c in chunks]
        pairs = [[query, chunk] for chunk in trimmed_chunks]
        
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
                    try:
                        if hasattr(reranker, "model"):
                            reranker.model.to("cpu")
                        scores = reranker.predict(
                            pairs,
                            batch_size=max(1, _RERANKER_BATCH_SIZE // 4),
                            show_progress_bar=False,
                        )
                    finally:
                        if torch.cuda.is_available() and hasattr(reranker, "model"):
                            try:
                                reranker.model.to("cuda")
                            except Exception:
                                pass
                else:
                    raise
        
        elapsed = time.time() - start_time
        
        chunk_scores = list(zip(chunks, scores))
        chunk_scores.sort(key=lambda x: x[1], reverse=True)
        
        if top_k:
            chunk_scores = chunk_scores[:top_k]
        
        if elapsed > 0:
            score_vals = [float(s) for _, s in chunk_scores]
            min_score = min(score_vals) if score_vals else 0.0
            max_score = max(score_vals) if score_vals else 0.0
            mean_score = (sum(score_vals) / len(score_vals)) if score_vals else 0.0
            logger.debug(
                "Reranked %d chunks in %.2fs (%.1f chunks/sec), score[min=%.3f mean=%.3f max=%.3f], returning top %d",
                len(chunks),
                elapsed,
                len(chunks) / elapsed,
                min_score,
                mean_score,
                max_score,
                len(chunk_scores),
            )
        
        return chunk_scores
        
    except Exception as e:
        logger.error("Reranking failed: %s, returning original chunks", e)
        return [(c, 1.0) for c in chunks[:top_k]] if top_k else [(c, 1.0) for c in chunks]
