from __future__ import annotations

import os

from fastapi import HTTPException

from app.services.material_service import get_material_for_user

def safe_path(base_dir: str, *parts: str) -> str:
    full = os.path.realpath(os.path.join(base_dir, *parts))
    base = os.path.realpath(base_dir)
    if not (full == base or full.startswith(base + os.sep)):
        raise HTTPException(status_code=400, detail="Invalid file path")
    return full

async def require_material(material_id: str, user_id, *, require_text: bool = True):
    material = await get_material_for_user(str(material_id), user_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    if require_text and not material.originalText:
        raise HTTPException(status_code=400, detail="Material has no text content")
    return material

async def require_material_text(material_id: str, user_id) -> str:
    await require_material(material_id, user_id, require_text=False)
    
    from app.services.material_service import get_material_text
    text = await get_material_text(str(material_id), str(user_id))
    if not text:
        raise HTTPException(status_code=404, detail="Material text not found in storage")
    return text

async def require_materials_text(
    material_ids: list[str], user_id, *, separator: str = "\n\n---\n\n"
) -> str:
    import asyncio

    async def _try_fetch(mid: str) -> str:
        try:
            return await require_material_text(mid, user_id)
        except HTTPException:
            return ""

    texts = await asyncio.gather(*[_try_fetch(mid) for mid in material_ids])
    valid = [t for t in texts if t]
    if not valid:
        raise HTTPException(status_code=404, detail="No accessible material text found")
    return separator.join(valid)


