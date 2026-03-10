from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path
from typing import Tuple

import magic

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

BLOCKED_MIME_TYPES: frozenset[str] = frozenset({
    "application/x-executable",
    "application/x-sharedlib",
    "application/x-elf",
    "application/x-pie-executable",
    "application/x-object",
    "application/x-dosexec",
    "application/x-msdownload",
    "application/x-mach-binary",
    "application/java-archive",
    "application/x-java-applet",
    "application/x-sh",
    "application/x-csh",
    "application/x-perl",
    "application/x-python-code",
    "text/x-shellscript",
    "text/x-script.python",
    "application/x-deb",
    "application/x-rpm",
    "application/x-msi",
    "application/vnd.android.package-archive",
    "application/x-apple-diskimage",
})

BLOCKED_EXTENSIONS: frozenset[str] = frozenset({
    ".exe", ".dll", ".so", ".dylib", ".bat", ".cmd", ".sh",
    ".ps1", ".vbs", ".jar", ".app", ".deb", ".rpm", ".msi",
    ".scr", ".com", ".pif", ".apk", ".dmg", ".bin", ".elf",
    ".cgi", ".pl", ".php", ".py", ".rb", ".lua",
})

class FileValidationError(Exception):
    pass

def validate_file_size(file_size: int) -> None:
    if file_size > MAX_FILE_SIZE:
        size_mb = file_size / (1024 * 1024)
        raise FileValidationError(
            f"File too large: {size_mb:.2f} MB exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit"
        )
    if file_size == 0:
        raise FileValidationError("File is empty")

def validate_not_executable(filename: str, file_path: str) -> str:
    file_ext = Path(filename).suffix.lower()
    if file_ext in BLOCKED_EXTENSIONS:
        raise FileValidationError(f"Executable/script files are not allowed: {file_ext}")

    try:
        mime = magic.Magic(mime=True)
        detected_mime = mime.from_file(file_path)
    except Exception as exc:
        logger.warning("MIME detection failed for %s: %s — skipping MIME block check", filename, exc)
        return "application/octet-stream"

    if detected_mime in BLOCKED_MIME_TYPES:
        raise FileValidationError(
            f"Blocked file type: {detected_mime}. Executable and script files are not allowed."
        )

    logger.debug("Accepted file: %s  mime=%s", filename, detected_mime)
    return detected_mime

def sanitize_filename(filename: str) -> str:
    filename = Path(filename).name
    filename = filename.replace("\0", "")
    if ".." in filename or "/" in filename or "\\" in filename:
        raise FileValidationError("Invalid filename: path traversal detected")

    safe = re.sub(r"[^\w\s.\-]", "_", filename)
    safe = re.sub(r"[\s_]+", "_", safe)

    if len(safe) > 255:
        stem = Path(safe).stem[:200]
        ext  = Path(safe).suffix
        safe = stem + ext

    if not safe:
        raise FileValidationError("Filename is invalid or empty after sanitization")
    return safe

def generate_internal_filename(original_filename: str) -> Tuple[str, str]:
    sanitized = sanitize_filename(original_filename)
    ext = Path(sanitized).suffix.lower()
    return f"{uuid.uuid4().hex}{ext}", ext

def validate_upload(
    file_path: str,
    filename: str,
    file_size: int,
) -> dict:
    validate_file_size(file_size)
    safe_filename = sanitize_filename(filename)
    detected_mime = validate_not_executable(filename, file_path)
    internal_filename, file_ext = generate_internal_filename(filename)

    logger.info(
        "File validation passed: %s → %s (%s, %d bytes)",
        filename, internal_filename, detected_mime, file_size,
    )
    return {
        "original_filename": filename,
        "safe_filename":     safe_filename,
        "internal_filename": internal_filename,
        "mime_type":         detected_mime,
        "file_extension":    file_ext,
        "file_size":         file_size,
    }
