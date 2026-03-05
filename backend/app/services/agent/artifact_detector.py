"""Artifact Detector — Scans workspace for generated files and categorizes them.

Handles:
- File detection and metadata extraction
- MIME type detection
- Category classification (Charts, Tables, Models, Reports, etc.)
- Preview generation for supported types
"""

from __future__ import annotations

import json
import logging
import mimetypes
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ArtifactCategory(str, Enum):
    """Categories for artifact grouping."""
    CHART = "chart"
    TABLE = "table"
    MODEL = "model"
    REPORT = "report"
    DATASET = "dataset"
    CODE = "code"
    AUDIO = "audio"
    VIDEO = "video"
    FILE = "file"


class DisplayType(str, Enum):
    """How artifact should be displayed in UI."""
    IMAGE = "image"
    CSV_TABLE = "csv_table"
    JSON_TREE = "json_tree"
    TEXT_PREVIEW = "text_preview"
    HTML_PREVIEW = "html_preview"
    PDF_EMBED = "pdf_embed"
    AUDIO_PLAYER = "audio_player"
    VIDEO_PLAYER = "video_player"
    MODEL_CARD = "model_card"
    FILE_CARD = "file_card"


# File extension to MIME type mapping
MIME_TYPES = {
    # Images
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
    ".bmp": "image/bmp",
    # Documents
    ".pdf": "application/pdf",
    ".html": "text/html",
    ".htm": "text/html",
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".log": "text/plain",
    # Data
    ".csv": "text/csv",
    ".json": "application/json",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".parquet": "application/octet-stream",
    # Models
    ".pkl": "application/octet-stream",
    ".pickle": "application/octet-stream",
    ".joblib": "application/octet-stream",
    ".pt": "application/octet-stream",
    ".pth": "application/octet-stream",
    ".h5": "application/octet-stream",
    ".hdf5": "application/octet-stream",
    ".onnx": "application/octet-stream",
    ".keras": "application/octet-stream",
    # Code
    ".py": "text/x-python",
    ".ipynb": "application/json",
    # Audio
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    # Video
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".avi": "video/x-msvideo",
    # Archives
    ".zip": "application/zip",
    ".tar": "application/x-tar",
    ".gz": "application/gzip",
}

# Extension to category mapping
EXTENSION_CATEGORIES = {
    # Charts
    ".png": ArtifactCategory.CHART,
    ".jpg": ArtifactCategory.CHART,
    ".jpeg": ArtifactCategory.CHART,
    ".svg": ArtifactCategory.CHART,
    # Tables/Data
    ".csv": ArtifactCategory.TABLE,
    ".xlsx": ArtifactCategory.TABLE,
    ".xls": ArtifactCategory.TABLE,
    ".parquet": ArtifactCategory.DATASET,
    # Models
    ".pkl": ArtifactCategory.MODEL,
    ".pickle": ArtifactCategory.MODEL,
    ".joblib": ArtifactCategory.MODEL,
    ".pt": ArtifactCategory.MODEL,
    ".pth": ArtifactCategory.MODEL,
    ".h5": ArtifactCategory.MODEL,
    ".hdf5": ArtifactCategory.MODEL,
    ".onnx": ArtifactCategory.MODEL,
    ".keras": ArtifactCategory.MODEL,
    # Reports
    ".pdf": ArtifactCategory.REPORT,
    ".html": ArtifactCategory.REPORT,
    ".md": ArtifactCategory.REPORT,
    # Code
    ".py": ArtifactCategory.CODE,
    ".ipynb": ArtifactCategory.CODE,
    # Audio
    ".mp3": ArtifactCategory.AUDIO,
    ".wav": ArtifactCategory.AUDIO,
    ".ogg": ArtifactCategory.AUDIO,
    # Video
    ".mp4": ArtifactCategory.VIDEO,
    ".webm": ArtifactCategory.VIDEO,
}

# Extension to display type mapping
EXTENSION_DISPLAY = {
    # Images
    ".png": DisplayType.IMAGE,
    ".jpg": DisplayType.IMAGE,
    ".jpeg": DisplayType.IMAGE,
    ".gif": DisplayType.IMAGE,
    ".webp": DisplayType.IMAGE,
    ".svg": DisplayType.IMAGE,
    ".bmp": DisplayType.IMAGE,
    # Tables
    ".csv": DisplayType.CSV_TABLE,
    ".xlsx": DisplayType.CSV_TABLE,
    ".xls": DisplayType.CSV_TABLE,
    # JSON
    ".json": DisplayType.JSON_TREE,
    # Text
    ".txt": DisplayType.TEXT_PREVIEW,
    ".log": DisplayType.TEXT_PREVIEW,
    ".md": DisplayType.TEXT_PREVIEW,
    ".py": DisplayType.TEXT_PREVIEW,
    # HTML
    ".html": DisplayType.HTML_PREVIEW,
    ".htm": DisplayType.HTML_PREVIEW,
    # PDF
    ".pdf": DisplayType.PDF_EMBED,
    # Models
    ".pkl": DisplayType.MODEL_CARD,
    ".pickle": DisplayType.MODEL_CARD,
    ".joblib": DisplayType.MODEL_CARD,
    ".pt": DisplayType.MODEL_CARD,
    ".pth": DisplayType.MODEL_CARD,
    ".h5": DisplayType.MODEL_CARD,
    ".onnx": DisplayType.MODEL_CARD,
    # Audio
    ".mp3": DisplayType.AUDIO_PLAYER,
    ".wav": DisplayType.AUDIO_PLAYER,
    ".ogg": DisplayType.AUDIO_PLAYER,
    # Video
    ".mp4": DisplayType.VIDEO_PLAYER,
    ".webm": DisplayType.VIDEO_PLAYER,
}

# Files to skip during detection
SKIP_FILES = {
    "_kepler_exec.py",
    "__pycache__",
    ".pyc",
    ".pyo",
    ".DS_Store",
    "Thumbs.db",
}

# Filename patterns that indicate specific artifact types
CHART_PATTERNS = [
    "chart", "plot", "figure", "graph", "histogram", "scatter",
    "distribution", "heatmap", "confusion", "correlation", "roc",
    "feature_importance", "learning_curve", "residual"
]

MODEL_PATTERNS = [
    "model", "classifier", "regressor", "predictor"
]


@dataclass
class DetectedArtifact:
    """A detected artifact with full metadata."""
    filename: str
    path: str
    size: int
    mime_type: str
    category: ArtifactCategory
    display_type: DisplayType
    created_at: str = ""
    preview_data: Optional[str] = None  # Base64 for images, first rows for CSV
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "path": self.path,
            "size": self.size,
            "mime": self.mime_type,
            "category": self.category.value,
            "display_type": self.display_type.value,
            "created_at": self.created_at,
            "preview_data": self.preview_data,
        }


class ArtifactDetector:
    """Scans workspace directory for generated artifacts."""
    
    def __init__(self, work_dir: str):
        self.work_dir = work_dir
    
    def detect_all(self) -> List[Dict[str, Any]]:
        """Detect all artifacts in workspace directory.
        
        Returns:
            List of artifact dictionaries with metadata
        """
        if not self.work_dir or not os.path.isdir(self.work_dir):
            return []
        
        artifacts = []
        
        for item in os.listdir(self.work_dir):
            if item in SKIP_FILES or item.startswith("__"):
                continue
            
            fpath = os.path.join(self.work_dir, item)
            
            if os.path.isdir(fpath):
                # Recursively scan subdirectories
                artifacts.extend(self._scan_directory(fpath, item))
            elif os.path.isfile(fpath):
                artifact = self._detect_file(fpath, item)
                if artifact:
                    artifacts.append(artifact)
        
        return artifacts
    
    def _scan_directory(self, dir_path: str, prefix: str) -> List[Dict[str, Any]]:
        """Recursively scan a directory for artifacts."""
        artifacts = []
        
        for item in os.listdir(dir_path):
            if item in SKIP_FILES or item.startswith("__"):
                continue
            
            fpath = os.path.join(dir_path, item)
            display_name = f"{prefix}/{item}"
            
            if os.path.isfile(fpath):
                artifact = self._detect_file(fpath, display_name)
                if artifact:
                    artifacts.append(artifact)
        
        return artifacts
    
    def _detect_file(self, fpath: str, filename: str) -> Optional[Dict[str, Any]]:
        """Detect and classify a single file.
        
        Args:
            fpath: Full path to file
            filename: Display filename
            
        Returns:
            Artifact dictionary or None if should be skipped
        """
        try:
            stat = os.stat(fpath)
            
            # Skip empty files
            if stat.st_size == 0:
                return None
            
            # Skip very large files (>100MB)
            if stat.st_size > 100 * 1024 * 1024:
                logger.warning("Skipping large file: %s (%d bytes)", filename, stat.st_size)
                return None
            
            # Get extension
            ext = os.path.splitext(filename)[1].lower()
            base_name = os.path.basename(filename).lower()
            
            # Determine MIME type
            mime_type = MIME_TYPES.get(ext)
            if not mime_type:
                mime_type, _ = mimetypes.guess_type(filename)
                mime_type = mime_type or "application/octet-stream"
            
            # Determine category
            category = self._classify_category(filename, ext, mime_type)
            
            # Determine display type
            display_type = self._classify_display(ext, mime_type)
            
            # Get creation time
            from datetime import datetime
            created_at = datetime.fromtimestamp(stat.st_ctime).isoformat()
            
            # Generate preview if applicable
            preview_data = self._generate_preview(fpath, ext, display_type)
            
            return {
                "filename": os.path.basename(filename),
                "path": fpath,
                "size": stat.st_size,
                "mime": mime_type,
                "category": category.value,
                "display_type": display_type.value,
                "created_at": created_at,
                "preview_data": preview_data,
            }
            
        except Exception as e:
            logger.error("Failed to detect artifact %s: %s", filename, e)
            return None
    
    def _classify_category(
        self,
        filename: str,
        ext: str,
        mime_type: str
    ) -> ArtifactCategory:
        """Classify artifact into a category."""
        base_name = os.path.basename(filename).lower()
        
        # Check extension mapping first
        if ext in EXTENSION_CATEGORIES:
            category = EXTENSION_CATEGORIES[ext]
            
            # Refine based on filename patterns
            if category == ArtifactCategory.CHART:
                # Verify it's actually a chart based on name
                if not any(p in base_name for p in CHART_PATTERNS):
                    # Generic image, still categorize as chart
                    return ArtifactCategory.CHART
            
            return category
        
        # Check MIME type
        if mime_type.startswith("image/"):
            return ArtifactCategory.CHART
        if mime_type.startswith("audio/"):
            return ArtifactCategory.AUDIO
        if mime_type.startswith("video/"):
            return ArtifactCategory.VIDEO
        if mime_type in ("text/csv", "application/csv"):
            return ArtifactCategory.TABLE
        if mime_type == "application/pdf":
            return ArtifactCategory.REPORT
        
        # Check filename patterns
        if any(p in base_name for p in MODEL_PATTERNS):
            return ArtifactCategory.MODEL
        if any(p in base_name for p in CHART_PATTERNS):
            return ArtifactCategory.CHART
        if "report" in base_name or "summary" in base_name:
            return ArtifactCategory.REPORT
        if "data" in base_name or "dataset" in base_name:
            return ArtifactCategory.DATASET
        
        return ArtifactCategory.FILE
    
    def _classify_display(self, ext: str, mime_type: str) -> DisplayType:
        """Determine how artifact should be displayed."""
        # Check extension mapping
        if ext in EXTENSION_DISPLAY:
            return EXTENSION_DISPLAY[ext]
        
        # Check MIME type
        if mime_type.startswith("image/"):
            return DisplayType.IMAGE
        if mime_type.startswith("audio/"):
            return DisplayType.AUDIO_PLAYER
        if mime_type.startswith("video/"):
            return DisplayType.VIDEO_PLAYER
        if mime_type in ("text/csv", "application/csv"):
            return DisplayType.CSV_TABLE
        if mime_type == "application/json":
            return DisplayType.JSON_TREE
        if mime_type.startswith("text/"):
            return DisplayType.TEXT_PREVIEW
        if mime_type == "application/pdf":
            return DisplayType.PDF_EMBED
        
        return DisplayType.FILE_CARD
    
    def _generate_preview(
        self,
        fpath: str,
        ext: str,
        display_type: DisplayType
    ) -> Optional[str]:
        """Generate preview data for supported types."""
        try:
            # CSV/Table preview - first few rows
            if display_type == DisplayType.CSV_TABLE:
                return self._preview_csv(fpath)
            
            # Text preview - first 1000 chars
            if display_type == DisplayType.TEXT_PREVIEW:
                return self._preview_text(fpath)
            
            # JSON preview - pretty formatted
            if display_type == DisplayType.JSON_TREE:
                return self._preview_json(fpath)
            
            # Image preview - base64 thumbnail
            # (Skipping for now to avoid large payloads)
            
            return None
            
        except Exception as e:
            logger.warning("Failed to generate preview for %s: %s", fpath, e)
            return None
    
    def _preview_csv(self, fpath: str, max_rows: int = 10) -> Optional[str]:
        """Generate CSV preview with first N rows."""
        try:
            lines = []
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f):
                    if i >= max_rows:
                        break
                    lines.append(line.strip())
            
            return "\n".join(lines) if lines else None
            
        except Exception:
            return None
    
    def _preview_text(self, fpath: str, max_chars: int = 1000) -> Optional[str]:
        """Generate text preview."""
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(max_chars)
                if len(content) == max_chars:
                    content += "..."
                return content
                
        except Exception:
            return None
    
    def _preview_json(self, fpath: str) -> Optional[str]:
        """Generate JSON preview."""
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Truncate large objects
            preview = json.dumps(data, indent=2)
            if len(preview) > 2000:
                preview = preview[:2000] + "\n..."
            
            return preview
            
        except Exception:
            return None
    
    def detect_by_category(self) -> Dict[str, List[Dict[str, Any]]]:
        """Detect artifacts and group by category.
        
        Returns:
            Dictionary mapping category names to artifact lists
        """
        all_artifacts = self.detect_all()
        
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        
        for artifact in all_artifacts:
            category = artifact.get("category", "file")
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(artifact)
        
        return grouped


def detect_output_files(work_dir: str, code: str = "") -> List[Dict[str, Any]]:
    """Convenience function to detect artifacts in a workspace.
    
    This maintains backward compatibility with existing code.
    """
    detector = ArtifactDetector(work_dir)
    return detector.detect_all()


def classify_artifact(filename: str, mime: str) -> str:
    """Classify artifact for display type (backward compatibility).
    
    Returns the display_type value as a string.
    """
    ext = os.path.splitext(filename)[1].lower()
    
    if ext in EXTENSION_DISPLAY:
        return EXTENSION_DISPLAY[ext].value
    
    if mime.startswith("image/"):
        return DisplayType.IMAGE.value
    if mime in ("text/csv", "application/csv") or ext in (".csv",):
        return DisplayType.CSV_TABLE.value
    if ext in (".xlsx", ".xls"):
        return DisplayType.CSV_TABLE.value
    if mime == "application/json" or ext == ".json":
        return DisplayType.JSON_TREE.value
    if mime in ("text/plain", "text/markdown") or ext in (".txt", ".log", ".md"):
        return DisplayType.TEXT_PREVIEW.value
    if mime == "text/html" or ext in (".html", ".htm"):
        return DisplayType.HTML_PREVIEW.value
    if mime == "application/pdf" or ext == ".pdf":
        return DisplayType.PDF_EMBED.value
    if mime.startswith("audio/"):
        return DisplayType.AUDIO_PLAYER.value
    if mime.startswith("video/"):
        return DisplayType.VIDEO_PLAYER.value
    
    return DisplayType.FILE_CARD.value
