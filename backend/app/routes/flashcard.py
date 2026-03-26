import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional

from app.models.shared_enums import DifficultyLevel
from app.services.flashcard.generator import generate_flashcards, suggest_flashcard_count
from app.services.auth import get_current_user
from .utils import require_material_text, require_materials_text

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/flashcard", tags=["flashcard"])

class FlashcardRequest(BaseModel):
    material_id: Optional[str] = None
    material_ids: Optional[List[str]] = None
    topic: Optional[str] = Field(None, max_length=500)
    card_count: Optional[int] = Field(None, ge=1, le=150)
    difficulty: DifficultyLevel = DifficultyLevel.medium
    additional_instructions: Optional[str] = Field(None, max_length=2000)

class SuggestRequest(BaseModel):
    material_id: Optional[str] = None
    material_ids: Optional[List[str]] = None

@router.post("")
async def create_flashcards(
    request: FlashcardRequest,
    current_user=Depends(get_current_user),
):
    ids = request.material_ids or ([request.material_id] if request.material_id else [])
    if not ids:
        raise HTTPException(status_code=400, detail="No material selected")

    logger.info(
        "Flashcard generation started | user=%s | material_ids=%s | count=%s | difficulty=%s | topic=%s",
        current_user.id, ids, request.card_count, request.difficulty.value, request.topic or "none",
    )

    if len(ids) == 1:
        text = await require_material_text(ids[0], current_user.id)
    else:
        text = await require_materials_text(ids, current_user.id)

    logger.debug("Flashcard source text loaded | chars=%d", len(text))

    if request.topic and request.topic.strip():
        text = f"Focus on the topic: {request.topic}\n\nContent:\n{text}"
        logger.debug("Flashcard topic filter applied | topic=%s", request.topic)

    try:
        loop = asyncio.get_running_loop()
        logger.info("Flashcard LLM call dispatched | user=%s", current_user.id)
        flashcards = await loop.run_in_executor(
            None,
            lambda: generate_flashcards(
                text,
                card_count=request.card_count,
                difficulty=request.difficulty.value.capitalize(),
                instructions=request.additional_instructions,
            ),
        )
        count = len(flashcards.get("flashcards") or flashcards.get("cards") or [])
        logger.info(
            "Flashcard generation complete | user=%s | cards=%d",
            current_user.id, count,
        )
        return JSONResponse(content=flashcards)
    except Exception as e:
        logger.error(
            "Flashcard generation failed | user=%s | material_ids=%s | error=%s",
            current_user.id, ids, e, exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to generate flashcards")

@router.post("/suggest")
async def suggest_count(
    request: SuggestRequest,
    current_user=Depends(get_current_user),
):
    ids = request.material_ids or ([request.material_id] if request.material_id else [])
    if not ids:
        raise HTTPException(status_code=400, detail="No material selected")

    if len(ids) == 1:
        text = await require_material_text(ids[0], current_user.id)
    else:
        text = await require_materials_text(ids, current_user.id)

    try:
        suggestion = await suggest_flashcard_count(text)
        return JSONResponse(content=suggestion)
    except Exception as e:
        logger.error("Flashcard suggestion failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to get suggestion")

