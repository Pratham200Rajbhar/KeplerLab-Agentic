"""Typed error hierarchy for the notebook corpus domain."""
from __future__ import annotations


class CorpusError(Exception):
    """Base error for all notebook corpus operations."""

    def __init__(self, message: str, *, code: str = "CORPUS_ERROR", source_id: str | None = None):
        self.code = code
        self.source_id = source_id
        super().__init__(message)


# ── Validation errors ─────────────────────────────────────────────────────

class SourceValidationError(CorpusError):
    """Input failed validation (bad MIME, too large, empty, etc.)."""

    def __init__(self, message: str, *, source_id: str | None = None):
        super().__init__(message, code="SOURCE_VALIDATION_ERROR", source_id=source_id)


class UnsupportedSourceTypeError(SourceValidationError):
    """The source type is not recognised by the processor registry."""

    def __init__(self, source_type: str):
        super().__init__(f"Unsupported source type: {source_type}")
        self.code = "UNSUPPORTED_SOURCE_TYPE"


class DuplicateSourceError(CorpusError):
    """A source with the same fingerprint already exists in this notebook."""

    def __init__(self, *, source_id: str | None = None, existing_source_id: str | None = None):
        self.existing_source_id = existing_source_id
        super().__init__(
            "Duplicate source detected (same content already exists in this notebook)",
            code="DUPLICATE_SOURCE",
            source_id=source_id,
        )


# ── Extraction errors ─────────────────────────────────────────────────────

class SourceExtractionError(CorpusError):
    """Content extraction failed."""

    def __init__(self, message: str, *, source_id: str | None = None):
        super().__init__(message, code="SOURCE_EXTRACTION_ERROR", source_id=source_id)


# ── Transient vs permanent ────────────────────────────────────────────────

class TransientError(CorpusError):
    """Temporary failure that should be retried (network timeout, rate limit, etc.)."""

    def __init__(self, message: str, *, source_id: str | None = None):
        super().__init__(message, code="TRANSIENT_ERROR", source_id=source_id)


class PermanentError(CorpusError):
    """Permanent failure (invalid file, no transcript, corrupted data)."""

    def __init__(self, message: str, *, source_id: str | None = None):
        super().__init__(message, code="PERMANENT_ERROR", source_id=source_id)


# ── Access errors ─────────────────────────────────────────────────────────

class SourceNotFoundError(CorpusError):
    """Source does not exist or the user does not have access."""

    def __init__(self, source_id: str):
        super().__init__(f"Source not found: {source_id}", code="SOURCE_NOT_FOUND", source_id=source_id)


class TenantViolationError(CorpusError):
    """Cross-tenant access attempt detected."""

    def __init__(self, message: str = "Tenant isolation violation"):
        super().__init__(message, code="TENANT_VIOLATION")


# ── Job errors ────────────────────────────────────────────────────────────

class InvalidStageTransitionError(CorpusError):
    """Attempted an invalid state machine transition."""

    def __init__(self, current: str, target: str, *, source_id: str | None = None):
        super().__init__(
            f"Invalid job stage transition: {current} → {target}",
            code="INVALID_STAGE_TRANSITION",
            source_id=source_id,
        )


class StuckJobError(CorpusError):
    """A job has been running longer than the stuck-job timeout."""

    def __init__(self, job_id: str):
        super().__init__(f"Stuck job detected: {job_id}", code="STUCK_JOB")
