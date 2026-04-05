"""File source processor — handles uploaded documents."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict

from app.core.config import settings
from app.services.notebook_corpus.enums import SourceType
from app.services.notebook_corpus.errors import PermanentError, SourceExtractionError, SourceValidationError
from app.services.notebook_corpus.fingerprints import compute_file_checksum, compute_fingerprint
from app.services.notebook_corpus.schemas import ExtractedContent
from app.services.notebook_corpus.validators import validate_file_source

from . import register_processor
from .base import BaseSourceProcessor

logger = logging.getLogger(__name__)


@register_processor(SourceType.FILE)
class FileProcessor(BaseSourceProcessor):
    """Processes uploaded files (PDF, DOCX, PPTX, TXT, etc.)."""

    async def validate_input(self, *, source_data: Dict[str, Any]) -> None:
        validate_file_source(
            filename=source_data.get("filename", ""),
            size_bytes=source_data.get("size_bytes", 0),
            mime_type=source_data.get("mime_type"),
        )

    async def normalize_input(self, *, source_data: Dict[str, Any]) -> Dict[str, Any]:
        file_path = source_data.get("local_file_path", "")
        if not file_path or not os.path.isfile(file_path):
            raise SourceValidationError(f"File not found at path: {file_path}")

        # Compute checksum
        with open(file_path, "rb") as f:
            raw = f.read()
        source_data["checksum"] = compute_file_checksum(raw)
        source_data["size_bytes"] = len(raw)
        source_data["_raw_bytes"] = raw
        return source_data

    async def extract_content(self, *, source_data: Dict[str, Any]) -> ExtractedContent:
        from app.services.notebook_corpus.extraction.document_parser import parse_document

        filename = source_data.get("filename", "unknown")
        file_path = source_data.get("local_file_path", "")
        mime_type = source_data.get("mime_type", "")

        try:
            result = await parse_document(
                file_path=file_path,
                filename=filename,
                mime_type=mime_type,
            )
        except Exception as e:
            raise SourceExtractionError(f"Failed to extract content from {filename}: {e}")

        if not result.text.strip():
            raise PermanentError(f"No text content extracted from {filename}")

        # Compute content fingerprint for dedup
        source_data["fingerprint"] = compute_fingerprint(result.text)

        return result

    def classify_error(self, error: Exception) -> Exception:
        if isinstance(error, (SourceValidationError, PermanentError)):
            return error
        if isinstance(error, SourceExtractionError):
            return PermanentError(str(error))
        return super().classify_error(error)
