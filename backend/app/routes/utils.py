from __future__ import annotations

import os
from typing import Iterable

from fastapi import HTTPException

from app.db.prisma_client import prisma

def safe_path(base_dir: str, *parts: str) -> str:
    full = os.path.realpath(os.path.join(base_dir, *parts))
    base = os.path.realpath(base_dir)
    if not (full == base or full.startswith(base + os.sep)):
        raise HTTPException(status_code=400, detail="Invalid file path")
    return full


def _normalize_material_text(value: object) -> str:
    text = str(value or "").strip()
    return text


async def require_material_text(material_id: str, user_id: str) -> str:
    material = await require_material(material_id, user_id)

    text = _normalize_material_text(getattr(material, "originalText", None))
    if not text:
        raise HTTPException(
            status_code=400,
            detail="Material text is not available. Reprocess the material before generating content.",
        )
    return text


async def require_material(material_id: str, user_id: str):
    material = await prisma.material.find_first(
        where={"id": str(material_id), "userId": str(user_id)}
    )
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    return material


async def require_materials_text(material_ids: Iterable[str], user_id: str) -> str:
    ids = [str(mid) for mid in material_ids if str(mid).strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="No material selected")

    materials = await prisma.material.find_many(
        where={"id": {"in": ids}, "userId": str(user_id)}
    )
    found_ids = {str(m.id) for m in materials}
    missing = [mid for mid in ids if mid not in found_ids]
    if missing:
        raise HTTPException(status_code=404, detail="One or more materials were not found")

    texts = []
    for material in materials:
        text = _normalize_material_text(getattr(material, "originalText", None))
        if text:
            texts.append(text)

    if not texts:
        raise HTTPException(
            status_code=400,
            detail="No material text available in selected materials.",
        )

    return "\n\n".join(texts)


async def require_corpus_or_material_text(
    *,
    notebook_id: str | None,
    material_ids: list[str] | None,
    user_id: str,
    query: str = "",
) -> str:
    """
    Corpus-aware text retrieval — tries new pipeline first, falls back to legacy materials.
    This is the preferred entry point for all downstream content generators.
    """
    # Try new corpus pipeline if we have a notebook
    if notebook_id and notebook_id != "draft":
        try:
            from app.services.notebook_corpus.compatibility import get_material_text_from_corpus
            text = await get_material_text_from_corpus(notebook_id, user_id, query)
            if text.strip():
                return text
        except Exception:
            pass  # Fall through to legacy

    # Fallback: legacy materials
    if material_ids:
        return await require_materials_text(material_ids, user_id)

    raise HTTPException(
        status_code=400,
        detail="No source material available. Add sources to your notebook or select materials.",
    )

