"""Material CRUD routes.

These endpoints manage the lifecycle of materials (list, update, delete, text retrieval)
separate from the upload/ingestion flow in upload.py.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from app.services.material_service import (
    get_user_materials,
    delete_material,
    update_material,
    get_material_for_user,
    get_material_text,
)
from app.services.auth import get_current_user
from app.services.text_processing.file_detector import FileTypeDetector
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/materials", tags=["materials"])


@router.get("")
async def list_materials(
    notebook_id: Optional[str] = None,
    current_user=Depends(get_current_user),
):
    """List all materials for the current user, optionally filtered by notebook."""
    nb_id = notebook_id if notebook_id else None
    materials = await get_user_materials(current_user.id, nb_id)
    return [
        {
            "id": str(m.id),
            "filename": m.filename,
            "title": getattr(m, "title", None),
            "status": m.status,
            "chunk_count": m.chunkCount,
            "source_type": getattr(m, "sourceType", None) or "file",
            "created_at": m.createdAt.isoformat(),
            **({"error": m.error} if getattr(m, "error", None) else {}),
        }
        for m in materials
    ]


class MaterialUpdateBody(BaseModel):
    filename: Optional[str] = None
    title: Optional[str] = None


@router.patch("/{material_id}")
async def patch_material(
    material_id: str,
    body: MaterialUpdateBody,
    current_user=Depends(get_current_user),
):
    """Update material filename or title."""
    updated = await update_material(
        material_id, current_user.id,
        filename=body.filename,
        title=body.title,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Material not found")
    return {
        "id": str(updated.id),
        "filename": updated.filename,
        "status": updated.status,
        "chunk_count": updated.chunkCount,
        "source_type": getattr(updated, "sourceType", None) or "file",
    }


@router.delete("/{material_id}")
async def remove_material(
    material_id: str,
    current_user=Depends(get_current_user),
):
    """Delete a material and all associated storage."""
    deleted = await delete_material(material_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Material not found")
    return {"deleted": True}


@router.get("/{material_id}/text")
async def get_material_text_endpoint(
    material_id: str,
    current_user=Depends(get_current_user),
):
    """Get full extracted text for a material."""
    material = await get_material_for_user(material_id, str(current_user.id))
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    text = await get_material_text(material_id, str(current_user.id))
    if not text:
        raise HTTPException(status_code=404, detail="Material text not found")

    filename = getattr(material, "filename", "") or ""
    return {"text": text, "filename": filename}
