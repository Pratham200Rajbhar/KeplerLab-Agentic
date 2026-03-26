import logging
import json
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.services.auth import get_current_user
from app.services.notebook_service import (
    get_notebook_by_id,
    save_notebook_content,
    get_notebook_content,
    delete_notebook_content,
    update_notebook_content_title,
    rate_notebook_content,
    create_notebook,
    get_user_notebooks,
    update_notebook,
    delete_notebook,
)
from app.db.prisma_client import prisma

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notebooks", tags=["notebooks"])

class ContentType(str):
    FLASHCARDS = "flashcards"
    QUIZ = "quiz"
    PRESENTATION = "presentation"
    MINDMAP = "mindmap"

class SaveContentRequest(BaseModel):
    content_type: str
    title: Optional[str] = Field(None, max_length=500)
    data: dict
    material_id: Optional[str] = None

class CreateNotebookRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None

class UpdateNotebookRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


@router.get("")
async def list_notebooks(current_user=Depends(get_current_user)):
    notebooks = await get_user_notebooks(str(current_user.id))
    return [
        {
            "id": str(n.id),
            "name": n.name,
            "description": n.description,
            "created_at": n.createdAt.isoformat() if hasattr(n.createdAt, 'isoformat') else n.createdAt,
            "updated_at": n.updatedAt.isoformat() if hasattr(n.updatedAt, 'isoformat') else n.updatedAt,
        }
        for n in notebooks
    ]


@router.post("")
async def create_notebook_endpoint(
    request: CreateNotebookRequest,
    current_user=Depends(get_current_user),
):
    notebook = await create_notebook(str(current_user.id), request.name, request.description)
    return {
        "id": str(notebook.id),
        "name": notebook.name,
        "description": notebook.description,
    }


@router.get("/{notebook_id}")
async def get_notebook_endpoint(
    notebook_id: UUID,
    current_user=Depends(get_current_user),
):
    notebook = await get_notebook_by_id(str(notebook_id), str(current_user.id))
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return {
        "id": str(notebook.id),
        "name": notebook.name,
        "description": notebook.description,
        "created_at": notebook.createdAt.isoformat() if hasattr(notebook.createdAt, 'isoformat') else notebook.createdAt,
        "updated_at": notebook.updatedAt.isoformat() if hasattr(notebook.updatedAt, 'isoformat') else notebook.updatedAt,
    }


@router.put("/{notebook_id}")
async def update_notebook_endpoint(
    notebook_id: UUID,
    request: UpdateNotebookRequest,
    current_user=Depends(get_current_user),
):
    notebook = await update_notebook(
        str(notebook_id), str(current_user.id), request.name, request.description
    )
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return {
        "id": str(notebook.id),
        "name": notebook.name,
        "description": notebook.description,
    }


@router.delete("/{notebook_id}")
async def delete_notebook_endpoint(
    notebook_id: UUID,
    current_user=Depends(get_current_user),
):
    deleted = await delete_notebook(str(notebook_id), str(current_user.id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return {"deleted": True}


@router.post("/{notebook_id}/content")
async def save_generated_content(
    notebook_id: UUID,
    request: SaveContentRequest,
    current_user=Depends(get_current_user),
):
    notebook = await get_notebook_by_id(str(notebook_id), str(current_user.id))
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    content = await save_notebook_content(
        notebook_id=str(notebook_id),
        user_id=str(current_user.id),
        content_type=request.content_type,
        title=request.title,
        data=request.data,
        material_id=request.material_id,
    )

    return {
        "id": str(content.id),
        "content_type": content.contentType,
        "title": content.title,
        "created_at": content.createdAt.isoformat() if hasattr(content.createdAt, 'isoformat') else content.createdAt,
    }


@router.get("/{notebook_id}/content")
async def get_notebook_content_endpoint(
    notebook_id: UUID,
    current_user=Depends(get_current_user),
):
    notebook = await get_notebook_by_id(str(notebook_id), str(current_user.id))
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    contents = await get_notebook_content(str(notebook_id), str(current_user.id))

    return [
        {
            "id": str(c.id),
            "content_type": c.contentType,
            "title": c.title,
            "data": json.loads(c.data) if isinstance(c.data, str) else c.data,
            "material_id": c.materialId,
            "rating": c.rating,
            "created_at": c.createdAt.isoformat() if hasattr(c.createdAt, 'isoformat') else c.createdAt,
        }
        for c in contents
    ]


@router.delete("/{notebook_id}/content/{content_id}")
async def delete_generated_content(
    notebook_id: UUID,
    content_id: UUID,
    current_user=Depends(get_current_user),
):
    deleted = await delete_notebook_content(
        str(notebook_id), str(current_user.id), str(content_id)
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Content not found")
    return {"deleted": True}


class UpdateContentRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)


@router.put("/{notebook_id}/content/{content_id}")
async def update_generated_content_title_endpoint(
    notebook_id: UUID,
    content_id: UUID,
    request: UpdateContentRequest,
    current_user=Depends(get_current_user),
):
    updated = await update_notebook_content_title(
        str(notebook_id), str(current_user.id), str(content_id), request.title
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Content not found")
    return {
        "id": str(updated.id),
        "content_type": updated.contentType,
        "title": updated.title,
        "created_at": updated.createdAt.isoformat() if hasattr(updated.createdAt, 'isoformat') else updated.createdAt,
    }


class RateContentRequest(BaseModel):
    rating: Optional[str] = Field(None, pattern="^(positive|negative)$")


@router.patch("/{notebook_id}/content/{content_id}/rating")
async def rate_generated_content(
    notebook_id: UUID,
    content_id: UUID,
    request: RateContentRequest,
    current_user=Depends(get_current_user),
):
    updated = await rate_notebook_content(
        str(notebook_id), str(current_user.id), str(content_id), request.rating
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Content not found")

    return {
        "id": str(updated.id),
        "rating": updated.rating,
    }
