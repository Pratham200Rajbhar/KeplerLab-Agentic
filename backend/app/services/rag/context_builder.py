from __future__ import annotations

import logging
import math
import re
import hashlib
from typing import List, Tuple, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

def _count_tokens(text: str) -> int:
    try:
        import tiktoken
        _enc = tiktoken.get_encoding("cl100k_base")
        return len(_enc.encode(text))
    except Exception:
        return max(1, int(len(text) / 3.5))

def _normalize_score(score: float) -> float:
    return 1.0 / (1.0 + math.exp(-score))

def _filter_chunks(
    chunks: List[Tuple[str, float]],
    min_score: float,
    min_length: int,
) -> List[Tuple[str, float]]:
    filtered = []
    for chunk, score in chunks:
        norm_score = _normalize_score(score)
        if norm_score >= min_score and len(chunk) >= min_length:
            filtered.append((chunk, norm_score))
        else:
            logger.debug(
                "Filtered chunk: raw_score=%.3f norm_score=%.3f len=%d",
                score, norm_score, len(chunk),
            )
    return filtered

def _summarize_chunk(chunk: str, max_sentences: int = 4) -> str:
    sentence_end = re.compile(r'(?<=[.!?])(?:\s+|$)(?=[A-Z"\']|$)')
    sentences = [s.strip() for s in sentence_end.split(chunk) if s.strip()]
    if len(sentences) <= max_sentences:
        return chunk
    return " ".join(sentences[:max_sentences]) + " …"

def build_context(
    chunks: List[Tuple[str, float]],
    max_tokens: Optional[int] = None,
) -> str:
    if not chunks:
        return "No relevant context found."
    
    max_tokens = max_tokens or settings.RAG_CONTEXT_MAX_TOKENS
    
    filtered = _filter_chunks(
        chunks,
        min_score=settings.MIN_SIMILARITY_SCORE,
        min_length=settings.MIN_CONTEXT_CHUNK_LENGTH,
    )
    
    if not filtered:
        logger.warning("All chunks filtered out due to low quality")
        return "No sufficiently relevant context found."

    logger.info("Filtered %d chunks down to %d", len(chunks), len(filtered))
    
    formatted_chunks = []
    seen = set()
    total_tokens = 0
    
    for idx, (chunk, score) in enumerate(filtered, start=1):
        fingerprint = hashlib.sha1(chunk.encode("utf-8", errors="ignore")).hexdigest()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)

        compact = re.sub(r"\s+", " ", chunk).strip()
        chunk_tokens = _count_tokens(compact)
        
        if total_tokens + chunk_tokens > max_tokens:
            if idx < len(filtered):
                summarized = _summarize_chunk(compact)
                chunk_tokens = _count_tokens(summarized)
                
                if total_tokens + chunk_tokens <= max_tokens:
                    compact = summarized
                else:
                    logger.info(f"Context limit reached at chunk {idx}/{len(filtered)}")
                    break
            else:
                if total_tokens < max_tokens * 0.5:
                    compact = _summarize_chunk(compact)
                else:
                    break
        
        formatted_chunks.append(
            f"- source: SOURCE {idx}\n"
            f"  score: {score:.3f}\n"
            f"  snippet: {compact}\n"
        )
        total_tokens += chunk_tokens
        
        logger.debug(
            "Added source %d: %d tokens (score=%.3f)",
            idx, chunk_tokens, score,
        )

    context = "\n".join(formatted_chunks)
    logger.info(
        "Built context: %d sources, ~%d tokens",
        len(formatted_chunks), total_tokens,
    )
    return context
