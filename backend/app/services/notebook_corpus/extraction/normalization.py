"""Text normalization and token estimation utilities."""
from __future__ import annotations

import re
import unicodedata

_WHITESPACE_COLLAPSE = re.compile(r"[ \t]+")
_BLANK_LINES = re.compile(r"\n{4,}")
_DASH_BULLETS = re.compile(r"(?m)^[\s]*[-•]+\s*")


def normalize_text(text: str) -> str:
    """
    Normalize extracted text for consistent processing.

    - Unicode NFC normalization
    - Strip null bytes and control characters
    - Collapse excessive whitespace
    - Normalize line endings
    - Trim leading/trailing whitespace
    """
    if not text:
        return ""

    # Unicode normalization
    text = unicodedata.normalize("NFC", text)

    # Remove null bytes and weird control characters (keep \n, \t)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Collapse excessive blank lines
    text = _BLANK_LINES.sub("\n\n\n", text)

    # Collapse horizontal whitespace within lines
    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        cleaned = _WHITESPACE_COLLAPSE.sub(" ", line).strip()
        cleaned_lines.append(cleaned)
    text = "\n".join(cleaned_lines)

    return text.strip()


def estimate_tokens(text: str) -> int:
    """
    Estimate token count using the ~4 chars per token heuristic.
    This is intentionally fast — we don't want to load a full tokenizer
    just for estimation. For budget-critical paths, use a proper tokenizer.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


def truncate_to_token_budget(text: str, max_tokens: int) -> str:
    """Truncate text to fit within a token budget (approximate)."""
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    # Try to truncate at a sentence boundary
    truncated = text[:max_chars]
    last_period = truncated.rfind(". ")
    if last_period > max_chars * 0.7:
        return truncated[:last_period + 1]
    last_newline = truncated.rfind("\n")
    if last_newline > max_chars * 0.7:
        return truncated[:last_newline]
    return truncated
