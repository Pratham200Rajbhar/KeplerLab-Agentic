import asyncio
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.services.auth import get_current_user
from app.services.mindmap.generator import generate_mindmap
from app.services.notebook_service import save_notebook_content, get_notebook_by_id
from app.services.material_service import filter_completed_material_ids
from .utils import require_materials_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/mindmap", tags=["mindmap"])

class MindMapRequest(BaseModel):
    notebook_id: str
    material_ids: List[str]
    focus_topic: Optional[str] = Field(None, max_length=500)
    additional_instructions: Optional[str] = Field(None, max_length=2000)

@router.post("")
async def create_mindmap(
    request: MindMapRequest,
    current_user=Depends(get_current_user),
):
    user_id = str(current_user.id)
    notebook_id = request.notebook_id
    
    # 1. Validate notebook exists and belongs to user
    notebook = await get_notebook_by_id(notebook_id, user_id)
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")

    # 2. Validate materials belong to user and are completed
    valid_ids = await filter_completed_material_ids(request.material_ids, user_id)
    if not valid_ids:
        raise HTTPException(status_code=400, detail="No valid/completed materials selected")
    
    logger.info(
        "Mind map generation started | user=%s | notebook=%s | material_count=%d | topic=%s",
        user_id, notebook_id, len(valid_ids), request.focus_topic or "none"
    )

    # 3. Load material texts
    try:
        text = await require_materials_text(valid_ids, user_id)
    except Exception as e:
        logger.error("Failed to load material texts: %s", e)
        raise HTTPException(status_code=404, detail="Material texts not found")

    # 4. Generate Mind Map
    try:
        loop = asyncio.get_running_loop()
        mindmap_data = await loop.run_in_executor(
            None,
            lambda: generate_mindmap(
                text,
                focus_topic=request.focus_topic,
                instructions=request.additional_instructions
            )
        )
    except Exception as e:
        logger.error("Mind map generation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate mind map")

    # 5. Save as GeneratedContent
    try:
        # Use first material_id if available as primary source link, or None
        primary_material_id = valid_ids[0] if valid_ids else None
        
        content_record = await save_notebook_content(
            notebook_id=notebook_id,
            user_id=user_id,
            content_type="mindmap",
            title=mindmap_data.get("title", "Mind Map"),
            data=mindmap_data,
            material_id=primary_material_id
        )
        
        # Link all materials to the generated content
        if valid_ids:
            from app.db.prisma_client import prisma
            # Create GeneratedContentMaterial joins
            await prisma.generatedcontentmaterial.create_many(
                data=[
                    {"generatedContentId": content_record.id, "materialId": mid}
                    for mid in valid_ids
                ],
                skip_duplicates=True
            )

        logger.info(
            "Mind map generation complete | user=%s | id=%s",
            user_id, content_record.id
        )
        
        import json
        return {
            "id": content_record.id,
            "content_type": content_record.contentType,
            "title": content_record.title,
            "data": json.loads(content_record.data) if isinstance(content_record.data, str) else content_record.data,
            "created_at": content_record.createdAt.isoformat() if hasattr(content_record.createdAt, 'isoformat') else content_record.createdAt
        }
    except Exception as e:
        logger.error("Failed to save generated mind map: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save generated mind map")
