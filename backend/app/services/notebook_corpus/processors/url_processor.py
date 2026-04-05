"""URL source processor — fetches and extracts content from web pages."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from app.services.notebook_corpus.enums import SourceType
from app.services.notebook_corpus.errors import SourceExtractionError, TransientError
from app.services.notebook_corpus.fingerprints import compute_fingerprint
from app.services.notebook_corpus.schemas import ExtractedContent
from app.services.notebook_corpus.validators import validate_url_source

from . import register_processor
from .base import BaseSourceProcessor

logger = logging.getLogger(__name__)


@register_processor(SourceType.URL)
class URLProcessor(BaseSourceProcessor):
    """Processes URL sources by fetching and extracting article content."""

    async def validate_input(self, *, source_data: Dict[str, Any]) -> None:
        url = source_data.get("url", "")
        validate_url_source(url)

    async def normalize_input(self, *, source_data: Dict[str, Any]) -> Dict[str, Any]:
        return source_data

    async def extract_content(self, *, source_data: Dict[str, Any]) -> ExtractedContent:
        from app.services.notebook_corpus.extraction.html_parser import extract_from_url
        from app.services.notebook_corpus.extraction.normalization import normalize_text, estimate_tokens

        url = source_data["url"]
        try:
            raw_result = await extract_from_url(url)
        except TimeoutError:
            raise TransientError(f"Timeout fetching URL: {url}")
        except Exception as e:
            raise SourceExtractionError(f"Failed to fetch URL {url}: {e}")

        text = raw_result.get("text", "")
        title = raw_result.get("title", "")

        if not text.strip():
            raise SourceExtractionError(f"No content extracted from URL: {url}")

        normalized = normalize_text(text)
        token_count = estimate_tokens(normalized)
        source_data["fingerprint"] = compute_fingerprint(normalized)

        if title and not source_data.get("title"):
            source_data["title"] = title[:510]

        return ExtractedContent(
            text=normalized,
            metadata={"url": url, "title": title, "source_type": "url"},
            sections=[],
            warnings=raw_result.get("warnings", []),
            token_count=token_count,
            page_count=0,
        )

    def classify_error(self, error: Exception) -> Exception:
        if isinstance(error, (TimeoutError, ConnectionError)):
            return TransientError(f"Transient URL error: {error}")
        return super().classify_error(error)
