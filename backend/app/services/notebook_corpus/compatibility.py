"""Compatibility layer — bridges legacy Material-based code to the new Source corpus."""
from __future__ import annotations

import logging
from typing import Optional

from app.db.prisma_client import prisma
from app.services.notebook_corpus.retrieval.notebook_context_builder import get_notebook_context

logger = logging.getLogger(__name__)


async def get_material_text_from_corpus(
    notebook_id: str,
    user_id: str,
    query: str = "",
) -> str:
    """
    Replacement for require_material_text() / require_materials_text()
    that pulls from the new corpus pipeline.

    Falls back to legacy material.originalText if no sources are available.
    """
    # Try new corpus first
    context = await get_notebook_context(notebook_id, user_id, query or "source material")
    if context.context_text.strip():
        return context.context_text

    # Fallback: check for legacy materials in this notebook
    materials = await prisma.material.find_many(
        where={"notebookId": notebook_id, "userId": user_id},
        order={"updatedAt": "desc"},
    )

    texts = []
    for material in materials:
        text = str(getattr(material, "originalText", "") or "").strip()
        if text:
            texts.append(text)

    return "\n\n".join(texts)


async def get_materials_text_by_ids(
    material_ids: list[str],
    user_id: str,
    query: str = "",
) -> str:
    """
    Get text for specific material IDs from corpus or legacy fallback.
    """
    if not material_ids:
        return ""

    # Check if any of these have linked Source records
    materials = await prisma.material.find_many(
        where={"id": {"in": material_ids}, "userId": user_id},
        include={"source": True},
    )

    # Collect notebook IDs for corpus lookup
    notebook_ids = {m.notebookId for m in materials if m.notebookId}

    # If we have sources, try corpus path
    if notebook_ids and any(m.source for m in materials if hasattr(m, "source") and m.source):
        for nb_id in notebook_ids:
            if nb_id:
                context = await get_notebook_context(nb_id, user_id, query or "source material")
                if context.context_text.strip():
                    return context.context_text

    # Fallback: legacy originalText
    texts = []
    for material in materials:
        text = str(getattr(material, "originalText", "") or "").strip()
        if text:
            texts.append(text)

    return "\n\n".join(texts)
