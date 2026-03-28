from __future__ import annotations

"""RAG chunking facade.

The canonical implementation lives in app.services.text_processing.chunker.
This module exists to provide a stable RAG-oriented import path.
"""

from app.services.text_processing.chunker import chunk_text

__all__ = ["chunk_text"]
