"""Text source processor — handles direct text/paste input."""
from __future__ import annotations

import logging
from typing import Any, Dict

from app.services.notebook_corpus.enums import SourceType
from app.services.notebook_corpus.fingerprints import compute_fingerprint
from app.services.notebook_corpus.schemas import ExtractedContent
from app.services.notebook_corpus.validators import validate_text_source

from . import register_processor
from .base import BaseSourceProcessor

logger = logging.getLogger(__name__)


@register_processor(SourceType.TEXT)
class TextProcessor(BaseSourceProcessor):
    """Processes direct text/paste sources."""

    async def validate_input(self, *, source_data: Dict[str, Any]) -> None:
        text = source_data.get("text", "")
        validate_text_source(text)

    async def normalize_input(self, *, source_data: Dict[str, Any]) -> Dict[str, Any]:
        text = source_data.get("text", "").strip()
        source_data["text"] = text
        source_data["fingerprint"] = compute_fingerprint(text)
        return source_data

    async def extract_content(self, *, source_data: Dict[str, Any]) -> ExtractedContent:
        from app.services.notebook_corpus.extraction.normalization import normalize_text, estimate_tokens

        text = source_data["text"]
        normalized = normalize_text(text)
        token_count = estimate_tokens(normalized)

        return ExtractedContent(
            text=normalized,
            metadata={"source_type": "text"},
            sections=[],
            warnings=[],
            token_count=token_count,
            page_count=0,
        )
