"""Document parser facade — dispatches to format-specific parsers."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from app.services.notebook_corpus.errors import PermanentError, SourceExtractionError
from app.services.notebook_corpus.schemas import ExtractedContent

from .normalization import estimate_tokens, normalize_text

logger = logging.getLogger(__name__)

# Map file extensions to parser functions
_PARSER_MAP: dict[str, str] = {
    ".pdf": "pdf",
    ".docx": "office_docx",
    ".doc": "office_docx",
    ".pptx": "office_pptx",
    ".ppt": "office_pptx",
    ".xlsx": "office_xlsx",
    ".xls": "office_xlsx",
    ".csv": "text",
    ".txt": "text",
    ".md": "text",
    ".html": "html",
    ".htm": "html",
}


async def parse_document(
    *,
    file_path: str,
    filename: str,
    mime_type: Optional[str] = None,
) -> ExtractedContent:
    """
    Parse a document file and return extracted content.
    Dispatches to the appropriate parser based on file extension.
    """
    ext = os.path.splitext(filename.lower())[1]
    parser_type = _PARSER_MAP.get(ext)

    if not parser_type:
        raise PermanentError(f"No parser available for extension: {ext}")

    if not os.path.isfile(file_path):
        raise SourceExtractionError(f"File not found: {file_path}")

    try:
        if parser_type == "pdf":
            from .pdf_parser import parse_pdf
            return await asyncio.to_thread(parse_pdf, file_path)

        if parser_type == "office_docx":
            from .office_parser import parse_docx
            return await asyncio.to_thread(parse_docx, file_path)

        if parser_type == "office_pptx":
            from .office_parser import parse_pptx
            return await asyncio.to_thread(parse_pptx, file_path)

        if parser_type == "office_xlsx":
            from .office_parser import parse_xlsx
            return await asyncio.to_thread(parse_xlsx, file_path)

        if parser_type == "text":
            from .text_parser import parse_text_file
            return await asyncio.to_thread(parse_text_file, file_path)

        if parser_type == "html":
            from .html_parser import parse_html_file
            return await asyncio.to_thread(parse_html_file, file_path)

    except (PermanentError, SourceExtractionError):
        raise
    except Exception as e:
        raise SourceExtractionError(f"Parser failed for {filename} ({parser_type}): {e}")

    raise PermanentError(f"Parser type '{parser_type}' not implemented")
