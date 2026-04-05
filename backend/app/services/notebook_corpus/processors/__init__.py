"""Processor registry and package init."""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.services.notebook_corpus.enums import SourceType

if TYPE_CHECKING:
    from .base import BaseSourceProcessor

_REGISTRY: dict[SourceType, type["BaseSourceProcessor"]] = {}


def register_processor(source_type: SourceType):
    """Decorator to register a processor class for a source type."""
    def decorator(cls: type["BaseSourceProcessor"]):
        _REGISTRY[source_type] = cls
        return cls
    return decorator


def get_processor(source_type: SourceType) -> "BaseSourceProcessor":
    """Instantiate and return the appropriate processor for a source type."""
    from .file_processor import FileProcessor  # noqa: F401
    from .text_processor import TextProcessor  # noqa: F401
    from .url_processor import URLProcessor  # noqa: F401
    from .youtube_processor import YouTubeProcessor  # noqa: F401
    from .note_processor import NoteProcessor  # noqa: F401

    cls = _REGISTRY.get(source_type)
    if cls is None:
        from app.services.notebook_corpus.errors import UnsupportedSourceTypeError
        raise UnsupportedSourceTypeError(source_type)
    return cls()
