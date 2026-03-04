"""Mind map generation route."""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.models.mindmap_schemas import MindMapRequest
from app.services.mindmap.generator import generate_mindmap
from app.services.auth import get_current_user
from app.db.prisma_client import prisma

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mindmap", tags=["mindmap"])


@router.post("")
async def create_mindmap(
    request: MindMapRequest,
    current_user=Depends(get_current_user),
):
    """Generate a mind map from selected materials."""
    if not request.material_ids:
        raise HTTPException(status_code=400, detail="No materials selected")

    logger.info(
        "MindMap generation started | user=%s | notebook=%s | material_ids=%s",
        current_user.id, request.notebook_id, request.material_ids,
    )

    # Verify notebook belongs to user
    notebook = await prisma.notebook.find_first(
        where={"id": request.notebook_id, "userId": str(current_user.id)}
    )
    if not notebook:
        logger.warning(
            "MindMap generation rejected — notebook not found | user=%s | notebook=%s",
            current_user.id, request.notebook_id,
        )
        raise HTTPException(status_code=404, detail="Notebook not found")

    import time
    _t0 = time.monotonic()
    try:
        logger.info("MindMap LLM call dispatched | user=%s | notebook=%s", current_user.id, request.notebook_id)
        result = await generate_mindmap(
            material_ids=request.material_ids,
            notebook_id=request.notebook_id,
            user_id=str(current_user.id),
        )
        elapsed = time.monotonic() - _t0
        node_count = len(result.get("nodes") or [])
        logger.info(
            "MindMap generation complete | user=%s | notebook=%s | nodes=%d | elapsed=%.2fs",
            current_user.id, request.notebook_id, node_count, elapsed,
        )
        return JSONResponse(content=result)
    except Exception as e:
        elapsed = time.monotonic() - _t0
        logger.error(
            "MindMap generation failed | user=%s | notebook=%s | elapsed=%.2fs | error=%s",
            current_user.id, request.notebook_id, elapsed, e, exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to generate mind map")


@router.get("/{notebook_id}")
async def get_mindmap(
    notebook_id: str,
    current_user=Depends(get_current_user),
):
    """Retrieve saved mind map for a notebook."""
    content = await prisma.generatedcontent.find_first(
        where={
            "notebookId": notebook_id,
            "contentType": "mindmap",
            "userId": str(current_user.id),
        }
    )
    if not content:
        raise HTTPException(status_code=404, detail="Mind map not found")

    data = content.data if isinstance(content.data, dict) else (json.loads(content.data) if content.data else {})
    # Expose the GeneratedContent record UUID as `id` so callers (e.g. DELETE) can use it
    data["id"] = content.id
    return JSONResponse(content=data)


@router.delete("/{id}")
async def delete_mindmap(
    id: str,
    current_user=Depends(get_current_user),
):
    """Delete a mind map."""
    content = await prisma.generatedcontent.find_first(
        where={
            "id": id,
            "contentType": "mindmap",
            "userId": str(current_user.id),
        }
    )
    if not content:
        raise HTTPException(status_code=404, detail="Mind map not found")

    await prisma.generatedcontent.delete(where={"id": id})
    return {"success": True}
