"""Note source processor — handles notebook notes as first-class sources."""
from __future__ import annotations

import logging
from typing import Any, Dict

from app.services.notebook_corpus.enums import SourceType
from app.services.notebook_corpus.fingerprints import compute_fingerprint
from app.services.notebook_corpus.schemas import ExtractedContent
from app.services.notebook_corpus.validators import validate_note_source

from . import register_processor
from .base import BaseSourceProcessor

logger = logging.getLogger(__name__)


@register_processor(SourceType.NOTE)
class NoteProcessor(BaseSourceProcessor):
    """Processes user notebook notes as sources (supports reprocessing on edit)."""

    async def validate_input(self, *, source_data: Dict[str, Any]) -> None:
        content = source_data.get("note_content", source_data.get("text", ""))
        validate_note_source(content)

    async def normalize_input(self, *, source_data: Dict[str, Any]) -> Dict[str, Any]:
        content = source_data.get("note_content", source_data.get("text", "")).strip()
        source_data["note_content"] = content
        source_data["fingerprint"] = compute_fingerprint(content)
        return source_data

    async def extract_content(self, *, source_data: Dict[str, Any]) -> ExtractedContent:
        from app.services.notebook_corpus.extraction.normalization import normalize_text, estimate_tokens

        content = source_data["note_content"]
        normalized = normalize_text(content)
        token_count = estimate_tokens(normalized)

        return ExtractedContent(
            text=normalized,
            metadata={"source_type": "note"},
            sections=[],
            warnings=[],
            token_count=token_count,
            page_count=0,
        )
