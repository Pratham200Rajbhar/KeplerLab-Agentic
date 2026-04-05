"""Abstract base class for all source processors."""
from __future__ import annotations

import abc
import logging
from typing import Any, Dict, Optional

from app.services.notebook_corpus.errors import (
    CorpusError,
    PermanentError,
    SourceExtractionError,
    SourceValidationError,
    TransientError,
)
from app.services.notebook_corpus.schemas import ExtractedContent

logger = logging.getLogger(__name__)


class BaseSourceProcessor(abc.ABC):
    """
    Template for source processing.

    Subclasses implement the specific pipeline stages:
        validate_input() → normalize_input() → extract_content() → build_source_metadata()

    The classify_error() method decides whether an error is transient (retry) or permanent (dead-letter).
    """

    @abc.abstractmethod
    async def validate_input(self, *, source_data: Dict[str, Any]) -> None:
        """
        Validate the raw input before processing.
        Raise SourceValidationError on failure.
        """

    @abc.abstractmethod
    async def normalize_input(self, *, source_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform raw input into normalised form (e.g. download file, resolve URL).
        Returns updated source_data dict.
        """

    @abc.abstractmethod
    async def extract_content(self, *, source_data: Dict[str, Any]) -> ExtractedContent:
        """
        Extract text content from the normalised input.
        Returns an ExtractedContent with text, metadata, sections, and warnings.
        """

    def build_source_metadata(self, *, source_data: Dict[str, Any], extracted: ExtractedContent) -> Dict[str, Any]:
        """
        Build additional metadata to persist on the Source record.
        Default implementation returns the extraction metadata.
        """
        return {
            "page_count": extracted.page_count,
            "token_count": extracted.token_count,
            "section_count": len(extracted.sections),
            "warnings": extracted.warnings,
            **extracted.metadata,
        }

    def classify_error(self, error: Exception) -> CorpusError:
        """
        Determine whether an error is transient or permanent.
        Override in subclasses for source-type–specific logic.
        """
        if isinstance(error, (SourceValidationError, PermanentError)):
            return error if isinstance(error, CorpusError) else PermanentError(str(error))

        if isinstance(error, SourceExtractionError):
            return error

        if isinstance(error, (TimeoutError, ConnectionError, OSError)):
            return TransientError(f"Transient error: {error}")

        # Default: treat unknown errors as permanent
        return PermanentError(f"Unexpected error: {error}")

    async def process(self, *, source_data: Dict[str, Any]) -> tuple[ExtractedContent, Dict[str, Any]]:
        """
        Full pipeline: validate → normalize → extract → build metadata.
        Returns (extracted_content, source_metadata).
        """
        await self.validate_input(source_data=source_data)
        source_data = await self.normalize_input(source_data=source_data)
        extracted = await self.extract_content(source_data=source_data)
        metadata = self.build_source_metadata(source_data=source_data, extracted=extracted)
        return extracted, metadata
