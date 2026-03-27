from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.services.ai_resource_builder import build_resources
from app.services.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ai-resource"])


class AIResourceRequest(BaseModel):
    query: str = Field(..., min_length=5, max_length=4000)
    notebook_id: str | None = None


@router.post("/ai-resource-builder")
async def ai_resource_builder(
    request: AIResourceRequest,
    current_user=Depends(get_current_user),
):
    try:
        return await build_resources(
            query=request.query.strip(),
            user_id=str(current_user.id),
            notebook_id=request.notebook_id,
        )
    except Exception as exc:
        logger.exception("AI resource builder failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to generate AI resources")
