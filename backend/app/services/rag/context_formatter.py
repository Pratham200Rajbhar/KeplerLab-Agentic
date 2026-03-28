from __future__ import annotations

import logging
import re
import hashlib
from collections import OrderedDict
from typing import List, Dict, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_CACHE_MAX_SIZE = 2000
_material_name_cache: OrderedDict[str, str] = OrderedDict()


def _get_tokenizer():
    try:
        import tiktoken
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None


_TOKENIZER = _get_tokenizer()


def _count_tokens(text: str) -> int:
    if _TOKENIZER is None:
        return max(1, int(len(text) / 4))
    try:
        return len(_TOKENIZER.encode(text))
    except Exception:
        return max(1, int(len(text) / 4))


def _compact_snippet(text: str, max_tokens: int = 240) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    if _count_tokens(text) <= max_tokens:
        return text

    if _TOKENIZER is None:
        approx_chars = max_tokens * 4
        return text[:approx_chars].rstrip() + " ..."

    try:
        toks = _TOKENIZER.encode(text)
        clipped = _TOKENIZER.decode(toks[:max_tokens]).rstrip()
        return clipped + " ..."
    except Exception:
        approx_chars = max_tokens * 4
        return text[:approx_chars].rstrip() + " ..."

def _get_material_name_sync(material_id: str) -> str:
    if material_id in _material_name_cache:
        _material_name_cache.move_to_end(material_id)
        return _material_name_cache[material_id]
    return ""

def set_material_name(material_id: str, filename: str) -> None:
    _material_name_cache[material_id] = filename
    _material_name_cache.move_to_end(material_id)
    while len(_material_name_cache) > _CACHE_MAX_SIZE:
        _material_name_cache.popitem(last=False)

def format_context_with_citations(
    chunks: List[Dict],
    max_sources: Optional[int] = None,
    max_tokens: Optional[int] = None,
) -> str:
    if not chunks:
        return "No relevant context found."

    token_budget = max_tokens or settings.RAG_CONTEXT_MAX_TOKENS
    selected_chunks = chunks[:max_sources] if max_sources else chunks

    seen_fingerprints = set()
    formatted_sections = []
    total_tokens = 0

    for idx, chunk in enumerate(selected_chunks, start=1):
        raw_text = chunk.get("text", "")
        if not raw_text:
            continue
        fingerprint = hashlib.sha1(raw_text.encode("utf-8", errors="ignore")).hexdigest()
        if fingerprint in seen_fingerprints:
            continue
        seen_fingerprints.add(fingerprint)

        text = _compact_snippet(raw_text)
        if not text:
            continue

        chunk_id = chunk.get("id", "unknown")
        section_title = chunk.get("section_title", "No section")
        material_id = chunk.get("material_id", None)
        score = chunk.get("score", None)

        header_lines = ["-" * 50]

        if material_id:
            material_name = (
                chunk.get("filename")
                or _get_material_name_sync(material_id)
                or f"Source-{material_id[:8]}"
            )
            header_lines.append(f"[SOURCE {idx} - Material: {material_name}]")
        else:
            header_lines.append(f"[SOURCE {idx}]")

        if section_title and section_title != "No section":
            header_lines.append(f"Section: {section_title}")

        header_lines.append(f"Chunk ID: {chunk_id}")

        if score is not None:
            header_lines.append(f"Confidence: {score:.2f}")

        header_lines.append("")
        header_lines.append("Content:")

        section_text = "\n".join(header_lines) + f"\n{text}\n" + "-" * 50
        section_tokens = _count_tokens(section_text)
        if total_tokens + section_tokens > token_budget:
            logger.info(
                "Context token budget reached: used=%d incoming=%d budget=%d",
                total_tokens,
                section_tokens,
                token_budget,
            )
            break

        formatted_sections.append(section_text)
        total_tokens += section_tokens

        logger.debug(
            "Formatted SOURCE %d: chunk=%s  material=%s  section=%s  score=%s",
            idx, chunk_id, material_id, section_title, score,
        )

    context = "\n\n".join(formatted_sections)
    if not context:
        return "No relevant context found."
    logger.info(
        "Formatted %d source blocks with citation metadata (~%d tokens)",
        len(formatted_sections),
        total_tokens,
    )
    return context
