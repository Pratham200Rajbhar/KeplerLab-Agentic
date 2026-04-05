"""Input validation functions for each source type."""
from __future__ import annotations

import ipaddress
import logging
import os
import re
import socket
import unicodedata
from typing import Optional
from urllib.parse import urlparse

from app.core.config import settings

from .enums import SourceType
from .errors import SourceValidationError

logger = logging.getLogger(__name__)

# ── MIME type allow-lists ─────────────────────────────────────────────────

ALLOWED_MIME_TYPES: dict[str, set[str]] = {
    ".pdf": {"application/pdf"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".doc": {"application/msword"},
    ".pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation"},
    ".ppt": {"application/vnd.ms-powerpoint"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    ".xls": {"application/vnd.ms-excel"},
    ".csv": {"text/csv", "application/csv"},
    ".txt": {"text/plain"},
    ".md": {"text/markdown", "text/plain"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".mp3": {"audio/mpeg"},
    ".wav": {"audio/wav", "audio/x-wav"},
    ".m4a": {"audio/mp4", "audio/x-m4a"},
    ".mp4": {"video/mp4"},
    ".webm": {"video/webm"},
}

ALLOWED_EXTENSIONS: set[str] = set(ALLOWED_MIME_TYPES.keys())

# YouTube URL patterns
_YOUTUBE_RE = re.compile(
    r"(?:https?://)?(?:www\.|m\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})"
)


def validate_file_source(
    filename: str,
    size_bytes: int,
    mime_type: Optional[str] = None,
) -> None:
    """Validate a file source upload."""
    if not filename or not filename.strip():
        raise SourceValidationError("Filename is required")

    ext = os.path.splitext(filename.lower())[1]
    if ext not in ALLOWED_EXTENSIONS:
        raise SourceValidationError(f"Unsupported file extension: {ext}")

    if mime_type:
        allowed = ALLOWED_MIME_TYPES.get(ext, set())
        if allowed and mime_type not in allowed:
            logger.warning(
                "MIME mismatch: file=%s ext=%s mime=%s allowed=%s",
                filename, ext, mime_type, allowed,
            )
            # Warning only — don't block, some browsers report wrong MIME

    max_bytes = settings.SOURCE_MAX_FILE_SIZE_MB * 1024 * 1024
    if size_bytes > max_bytes:
        raise SourceValidationError(
            f"File too large: {size_bytes} bytes (max {settings.SOURCE_MAX_FILE_SIZE_MB} MB)"
        )
    if size_bytes == 0:
        raise SourceValidationError("Empty file rejected")

    # Path traversal check
    if ".." in filename or filename.startswith("/") or "\\" in filename:
        raise SourceValidationError("Invalid filename (path traversal detected)")


def validate_text_source(text: str) -> str:
    """Validate and normalize a text source. Returns cleaned text."""
    if not text or not text.strip():
        raise SourceValidationError("Text content is empty")

    text = text.strip()
    if len(text) < 10:
        raise SourceValidationError("Text is too short (minimum 10 characters)")
    if len(text) > 500_000:
        raise SourceValidationError("Text is too long (maximum 500,000 characters)")

    # Unicode normalization
    text = unicodedata.normalize("NFC", text)
    # Collapse excessive whitespace
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    text = re.sub(r" {3,}", "  ", text)

    return text


def validate_url_source(url: str) -> str:
    """Validate a URL source. Returns normalized URL."""
    if not url or not url.strip():
        raise SourceValidationError("URL is required")

    url = url.strip()
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise SourceValidationError(f"Invalid URL scheme: {parsed.scheme}")
    if not parsed.hostname:
        raise SourceValidationError("URL has no hostname")

    # Block private/local targets
    hostname = parsed.hostname
    if hostname in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
        raise SourceValidationError("Local URLs are not allowed")

    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise SourceValidationError("Private IP addresses are not allowed")
    except ValueError:
        # Not an IP, that's fine — it's a hostname
        pass

    if len(url) > 2048:
        raise SourceValidationError("URL too long (max 2048 characters)")

    return url


def validate_youtube_source(url: str) -> str:
    """Validate a YouTube URL. Returns extracted video ID."""
    url = validate_url_source(url)
    match = _YOUTUBE_RE.search(url)
    if not match:
        raise SourceValidationError("Invalid YouTube URL — could not extract video ID")
    return match.group(1)


def validate_note_source(content: str) -> str:
    """Validate a note source. Returns cleaned content."""
    return validate_text_source(content)


def validate_source_input(
    source_type: SourceType,
    *,
    filename: Optional[str] = None,
    size_bytes: int = 0,
    mime_type: Optional[str] = None,
    text: Optional[str] = None,
    url: Optional[str] = None,
    note_content: Optional[str] = None,
) -> dict:
    """
    Dispatch validation by source type.
    Returns a dict of validated/normalized values.
    """
    if source_type == SourceType.FILE:
        validate_file_source(filename or "", size_bytes, mime_type)
        return {"filename": filename, "size_bytes": size_bytes, "mime_type": mime_type}

    if source_type == SourceType.TEXT:
        cleaned = validate_text_source(text or "")
        return {"text": cleaned}

    if source_type == SourceType.URL:
        normalized_url = validate_url_source(url or "")
        return {"url": normalized_url}

    if source_type == SourceType.YOUTUBE:
        video_id = validate_youtube_source(url or "")
        return {"url": url, "video_id": video_id}

    if source_type == SourceType.NOTE:
        cleaned = validate_note_source(note_content or text or "")
        return {"note_content": cleaned}

    if source_type == SourceType.AUDIO_TRANSCRIPT:
        validate_file_source(filename or "", size_bytes, mime_type)
        return {"filename": filename, "size_bytes": size_bytes, "mime_type": mime_type}

    raise SourceValidationError(f"Unknown source type: {source_type}")
