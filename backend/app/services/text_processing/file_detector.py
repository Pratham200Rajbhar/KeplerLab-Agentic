from __future__ import annotations

import mimetypes
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class FileTypeDetector:

    SUPPORTED_TYPES: Dict[str, str] = {
        "application/pdf":                                                          "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/msword":                                                       "doc",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation":"pptx",
        "application/vnd.ms-powerpoint":                                            "ppt",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":       "xlsx",
        "application/vnd.ms-excel":                                                 "xls",
        "text/plain":                                                               "txt",
        "text/markdown":                                                            "md",
        "text/csv":                                                                 "csv",
        "text/html":                                                                "html",
        "application/rtf":                                                          "rtf",
        "text/rtf":                                                                 "rtf",
        "application/epub+zip":                                                     "epub",
        "application/vnd.oasis.opendocument.text":                                  "odt",
        "application/vnd.oasis.opendocument.spreadsheet":                           "ods",
        "application/vnd.oasis.opendocument.presentation":                          "odp",
        "image/jpeg":                                                               "jpg",
        "image/jpg":                                                                "jpg",
        "image/png":                                                                "png",
        "image/gif":                                                                "gif",
        "image/bmp":                                                                "bmp",
        "image/tiff":                                                               "tiff",
        "image/webp":                                                               "webp",
        "image/svg+xml":                                                            "svg",
        "audio/mpeg":                                                               "mp3",
        "audio/mp3":                                                                "mp3",
        "audio/wav":                                                                "wav",
        "audio/x-wav":                                                              "wav",
        "audio/mp4":                                                                "m4a",
        "audio/x-m4a":                                                              "m4a",
        "audio/aac":                                                                "aac",
        "audio/x-aac":                                                              "aac",
        "audio/ogg":                                                                "ogg",
        "audio/flac":                                                               "flac",
        "audio/x-flac":                                                             "flac",
        "audio/webm":                                                               "webm",
        "video/mp4":                                                                "mp4",
        "video/mpeg":                                                               "mpeg",
        "video/avi":                                                                "avi",
        "video/x-msvideo":                                                          "avi",
        "video/quicktime":                                                          "mov",
        "video/x-matroska":                                                         "mkv",
        "video/mkv":                                                                "mkv",
        "video/webm":                                                               "webm",
        "video/x-ms-wmv":                                                           "wmv",
        "video/3gpp":                                                               "3gp",
        "message/rfc822":                                                           "eml",
        "application/vnd.ms-outlook":                                               "msg",
    }

    _EXT_MAP: Dict[str, str] = {
        ".pdf": "pdf", ".docx": "docx", ".doc": "doc", ".pptx": "pptx",
        ".ppt": "ppt", ".xlsx": "xlsx", ".xls": "xls", ".txt": "txt",
        ".md": "md", ".csv": "csv", ".html": "html", ".htm": "html",
        ".rtf": "rtf", ".epub": "epub", ".odt": "odt", ".ods": "ods",
        ".odp": "odp",
        ".jpg": "jpg", ".jpeg": "jpg", ".png": "png", ".gif": "gif",
        ".bmp": "bmp", ".tiff": "tiff", ".tif": "tiff", ".webp": "webp",
        ".svg": "svg",
        ".mp3": "mp3", ".wav": "wav", ".m4a": "m4a", ".aac": "aac",
        ".ogg": "ogg", ".flac": "flac",
        ".mp4": "mp4", ".avi": "avi", ".mov": "mov", ".mkv": "mkv",
        ".webm": "webm", ".wmv": "wmv", ".mpeg": "mpeg", ".mpg": "mpeg",
        ".3gp": "3gp",
        ".eml": "eml", ".msg": "msg",
    }

    @staticmethod
    def _mime_to_category(mime: str) -> str:
        if not mime:
            return "unknown"
        if mime.startswith("image/"):
            return "image"
        if mime.startswith("audio/"):
            return "audio"
        if mime.startswith("video/"):
            return "video"
        if mime.startswith("text/") or mime in {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
            "application/rtf",
            "application/epub+zip",
            "application/vnd.oasis.opendocument.text",
            "application/vnd.oasis.opendocument.spreadsheet",
            "application/vnd.oasis.opendocument.presentation",
            "message/rfc822",
            "application/vnd.ms-outlook",
        }:
            return "document"
        return "unknown"

    @staticmethod
    def _ext_to_category(ext: str) -> str:
        images   = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".svg"}
        audio    = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
        video    = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".wmv", ".mpeg", ".mpg", ".3gp"}
        if ext in images:   return "image"
        if ext in audio:    return "audio"
        if ext in video:    return "video"
        return "document"

    @staticmethod
    def detect_file_type(file_path: str) -> Dict[str, Optional[str]]:
        path = Path(file_path)
        file_ext = path.suffix.lower()

        mime_type: Optional[str] = None
        try:
            import magic as _magic
            mime_type = _magic.from_file(str(path), mime=True)
        except Exception:
            pass

        if not mime_type or mime_type == "application/octet-stream":
            guessed, _ = mimetypes.guess_type(str(path))
            if guessed:
                mime_type = guessed
            elif not mime_type:
                mime_type = "application/octet-stream"

        ext = FileTypeDetector.SUPPORTED_TYPES.get(mime_type)
        if not ext:
            ext = FileTypeDetector._EXT_MAP.get(file_ext, file_ext.lstrip(".") or "bin")

        category = FileTypeDetector._mime_to_category(mime_type)
        if category == "unknown" and file_ext:
            category = FileTypeDetector._ext_to_category(file_ext)

        is_supported = mime_type in FileTypeDetector.SUPPORTED_TYPES or file_ext in FileTypeDetector._EXT_MAP

        return {
            "mime_type":    mime_type,
            "extension":    ext,
            "category":     category,
            "is_supported": is_supported,
        }

    @staticmethod
    def detect_from_extension(url_or_path: str) -> Optional[str]:
        ext = Path(url_or_path.split("?")[0]).suffix.lower()
        if not ext:
            return None

        canonical = FileTypeDetector._EXT_MAP.get(ext)
        if not canonical:
            return None
            
        cat = FileTypeDetector._ext_to_category(ext)
        if cat == "image":
            return "image"
        return canonical

    @staticmethod
    def is_supported(file_path: str) -> bool:
        info = FileTypeDetector.detect_file_type(file_path)
        return info["is_supported"]

    @staticmethod
    def get_supported_extensions() -> list:
        exts = list({v for v in FileTypeDetector.SUPPORTED_TYPES.values()})
        return sorted(exts)