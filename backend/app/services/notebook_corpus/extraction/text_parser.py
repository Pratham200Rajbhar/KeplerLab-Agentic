"""Plain text and markdown parser."""
from __future__ import annotations

import logging

from app.services.notebook_corpus.errors import SourceExtractionError
from app.services.notebook_corpus.schemas import ExtractedContent
from .normalization import normalize_text, estimate_tokens

logger = logging.getLogger(__name__)


def parse_text_file(file_path: str) -> ExtractedContent:
    """Parse plain text / CSV / markdown files."""
    try:
        import chardet
    except ImportError:
        chardet = None

    try:
        with open(file_path, "rb") as f:
            raw_bytes = f.read()
    except Exception as e:
        raise SourceExtractionError(f"Failed to read text file: {e}")

    # Detect encoding
    encoding = "utf-8"
    if chardet:
        detected = chardet.detect(raw_bytes[:10000])
        if detected and detected.get("encoding"):
            encoding = detected["encoding"]

    try:
        text = raw_bytes.decode(encoding, errors="replace")
    except (UnicodeDecodeError, LookupError):
        text = raw_bytes.decode("utf-8", errors="replace")

    normalized = normalize_text(text)
    token_count = estimate_tokens(normalized)

    return ExtractedContent(
        text=normalized,
        metadata={"encoding": encoding, "source_type": "text"},
        sections=[],
        warnings=[],
        token_count=token_count,
        page_count=0,
    )
