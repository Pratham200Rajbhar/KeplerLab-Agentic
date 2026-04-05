"""Enumerations for the notebook corpus domain."""
from __future__ import annotations

from enum import Enum


class SourceType(str, Enum):
    """Types of sources that can be ingested into a notebook corpus."""
    FILE = "FILE"
    TEXT = "TEXT"
    URL = "URL"
    YOUTUBE = "YOUTUBE"
    NOTE = "NOTE"
    AUDIO_TRANSCRIPT = "AUDIO_TRANSCRIPT"


class SourceStatus(str, Enum):
    """Overall readiness status of a source."""
    QUEUED = "QUEUED"
    VALIDATING = "VALIDATING"
    EXTRACTING = "EXTRACTING"
    NORMALIZING = "NORMALIZING"
    CORPUS_BUILDING = "CORPUS_BUILDING"
    INDEXING = "INDEXING"
    READY = "READY"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


class IndexingStatus(str, Enum):
    """Indexing (embedding + vector store) status for a source."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    NOT_REQUIRED = "NOT_REQUIRED"


class ExtractionStatus(str, Enum):
    """Content extraction status for a source."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class RetrievalMode(str, Enum):
    """Which retrieval lane to use for a notebook query."""
    DIRECT_GROUNDING = "DIRECT_GROUNDING"
    INDEXED_RETRIEVAL = "INDEXED_RETRIEVAL"


class JobStage(str, Enum):
    """Stages a source processing job goes through."""
    QUEUED = "QUEUED"
    VALIDATING = "VALIDATING"
    EXTRACTING = "EXTRACTING"
    NORMALIZING = "NORMALIZING"
    CORPUS_BUILDING = "CORPUS_BUILDING"
    INDEXING = "INDEXING"
    READY = "READY"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


# Valid stage transitions for the state machine
VALID_STAGE_TRANSITIONS: dict[JobStage, set[JobStage]] = {
    JobStage.QUEUED: {JobStage.VALIDATING, JobStage.FAILED},
    JobStage.VALIDATING: {JobStage.EXTRACTING, JobStage.FAILED},
    JobStage.EXTRACTING: {JobStage.NORMALIZING, JobStage.FAILED},
    JobStage.NORMALIZING: {JobStage.CORPUS_BUILDING, JobStage.FAILED},
    JobStage.CORPUS_BUILDING: {JobStage.INDEXING, JobStage.READY, JobStage.FAILED},
    JobStage.INDEXING: {JobStage.READY, JobStage.FAILED},
    JobStage.READY: set(),  # terminal
    JobStage.FAILED: {JobStage.QUEUED, JobStage.DEAD_LETTER},  # retry or give up
    JobStage.DEAD_LETTER: set(),  # terminal
}
