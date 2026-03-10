from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# File extensions that indicate structured / tabular data
_STRUCTURED_EXTENSIONS: Set[str] = {"csv", "xlsx", "xls", "tsv", "ods", "parquet", "json", "jsonl"}

# File extensions that indicate text / document resources
_DOCUMENT_EXTENSIONS: Set[str] = {
    "pdf", "txt", "md", "docx", "doc", "rtf", "pptx", "ppt", "odt", "html", "htm", "epub",
}


@dataclass
class ResourceProfile:
    """Classification of materials available for the current agent run."""

    dataset_ids: List[str] = field(default_factory=list)
    document_ids: List[str] = field(default_factory=list)
    other_ids: List[str] = field(default_factory=list)

    dataset_filenames: List[str] = field(default_factory=list)
    document_filenames: List[str] = field(default_factory=list)

    @property
    def has_datasets(self) -> bool:
        return len(self.dataset_ids) > 0

    @property
    def has_documents(self) -> bool:
        return len(self.document_ids) > 0

    @property
    def has_materials(self) -> bool:
        return bool(self.dataset_ids or self.document_ids or self.other_ids)

    @property
    def is_mixed(self) -> bool:
        return self.has_datasets and self.has_documents

    def summary(self) -> str:
        """Human-readable resource summary for LLM prompts."""
        parts: List[str] = []
        if self.dataset_filenames:
            parts.append(
                f"{len(self.dataset_filenames)} structured dataset(s): "
                + ", ".join(self.dataset_filenames)
            )
        if self.document_filenames:
            parts.append(
                f"{len(self.document_filenames)} document(s): "
                + ", ".join(self.document_filenames)
            )
        if self.other_ids:
            parts.append(f"{len(self.other_ids)} other material(s)")
        if not parts:
            parts.append("No uploaded materials.")
        return "; ".join(parts)

    def recommended_tools(self) -> str:
        """Tool guidance based on resource types."""
        lines: List[str] = []
        if self.has_datasets:
            lines.append(
                "- **python_auto**: MUST be used for CSV/Excel/tabular datasets. "
                "Executes code immediately — charts appear inline, output files get "
                "download buttons. Use for loading data, statistics, ML, visualizations."
            )
        if self.has_documents:
            lines.append(
                "- **rag**: Use for PDFs, text documents, and knowledge sources. "
                "Retrieves relevant passages from uploaded documents."
            )
        if not self.has_materials:
            lines.append(
                "- **LLM knowledge**: No uploaded materials. Use the LLM's built-in "
                "knowledge for general or well-known facts. Do NOT default to web_search.\n"
                "- **web_search** / **research**: ONLY use when the user explicitly asks "
                "for current, live, real-time, or very recent information (e.g. today's "
                "news, stock prices, latest stats). General knowledge does NOT need web search."
            )
        return "\n".join(lines) if lines else ""


def _ext(filename: str) -> str:
    """Extract lowercase file extension without dot."""
    return os.path.splitext(filename)[1].lstrip(".").lower()


def _classify_by_filename(filename: str) -> str:
    """Classify a material as 'dataset', 'document', or 'other' based on extension."""
    ext = _ext(filename)
    if ext in _STRUCTURED_EXTENSIONS:
        return "dataset"
    if ext in _DOCUMENT_EXTENSIONS:
        return "document"
    return "other"


def _classify_by_metadata(metadata: Optional[Dict]) -> Optional[str]:
    """Try to classify from Prisma metadata JSON (extraction_metadata)."""
    if not metadata:
        return None
    if isinstance(metadata, dict):
        if metadata.get("is_structured"):
            return "dataset"
    return None


async def classify_materials(material_ids: List[str]) -> ResourceProfile:
    """Query Prisma for material metadata and classify each material."""
    profile = ResourceProfile()

    if not material_ids:
        return profile

    try:
        from app.db.prisma_client import prisma

        materials = await prisma.material.find_many(
            where={"id": {"in": material_ids}},
        )
    except Exception as exc:
        logger.error("Failed to fetch materials for resource routing: %s", exc)
        # Fallback: treat all as 'other' so agent still works
        profile.other_ids = list(material_ids)
        return profile

    for mat in materials:
        filename = getattr(mat, "filename", "") or ""
        mat_id = getattr(mat, "id", "")
        metadata = getattr(mat, "metadata", None)

        # Try metadata first, then fall back to filename extension
        classification = _classify_by_metadata(metadata) or _classify_by_filename(filename)

        if classification == "dataset":
            profile.dataset_ids.append(mat_id)
            profile.dataset_filenames.append(filename)
        elif classification == "document":
            profile.document_ids.append(mat_id)
            profile.document_filenames.append(filename)
        else:
            profile.other_ids.append(mat_id)

    logger.info(
        "Resource router: %d dataset(s), %d document(s), %d other — %s",
        len(profile.dataset_ids),
        len(profile.document_ids),
        len(profile.other_ids),
        profile.summary(),
    )
    return profile
