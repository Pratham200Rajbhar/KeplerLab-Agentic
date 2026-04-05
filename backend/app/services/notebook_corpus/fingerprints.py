"""Content fingerprinting for source deduplication."""
from __future__ import annotations

import hashlib
import re
import unicodedata


def compute_fingerprint(content: str) -> str:
    """
    Compute a stable SHA-256 fingerprint for deduplication.

    The content is normalized before hashing:
    - Unicode NFC normalization
    - Lowercase
    - Collapse all whitespace to single spaces
    - Strip leading / trailing whitespace

    This ensures that cosmetic differences (extra spaces, case changes)
    don't create duplicate sources.
    """
    if not content:
        return hashlib.sha256(b"").hexdigest()

    normalized = unicodedata.normalize("NFC", content)
    normalized = normalized.lower()
    normalized = re.sub(r"\s+", " ", normalized).strip()

    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def compute_file_checksum(data: bytes) -> str:
    """Compute SHA-256 checksum of raw file bytes."""
    return hashlib.sha256(data).hexdigest()
