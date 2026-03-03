"""Quiz generation route."""

import asyncio
import logging
from enum import Enum
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional

from app.services.quiz.generator import generate_quiz
from app.services.auth import get_current_user
from .utils import require_material_text, require_materials_text

logger = logging.getLogger(__name__)
router = APIRouter()


class DifficultyLevel(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class QuizRequest(BaseModel):
    material_id: Optional[str] = None
    material_ids: Optional[List[str]] = None
    topic: Optional[str] = Field(None, max_length=500)
    mcq_count: Optional[int] = Field(10, ge=1, le=150)
    difficulty: DifficultyLevel = DifficultyLevel.medium
    additional_instructions: Optional[str] = Field(None, max_length=2000)


@router.post("/quiz")
async def create_quiz(
    request: QuizRequest,
    current_user=Depends(get_current_user),
):
    ids = request.material_ids or ([request.material_id] if request.material_id else [])
    if not ids:
        raise HTTPException(status_code=400, detail="No material selected")

    logger.info(
        "Quiz generation started | user=%s | material_ids=%s | count=%s | difficulty=%s | topic=%s",
        current_user.id, ids, request.mcq_count, request.difficulty.value, request.topic or "none",
    )

    if len(ids) == 1:
        text = await require_material_text(ids[0], current_user.id)
    else:
        text = await require_materials_text(ids, current_user.id)

    logger.debug("Quiz source text loaded | chars=%d", len(text))

    if request.topic and request.topic.strip():
        text = f"Focus on the topic: {request.topic}\n\nContent:\n{text}"
        logger.debug("Quiz topic filter applied | topic=%s", request.topic)

    try:
        loop = asyncio.get_running_loop()
        logger.info("Quiz LLM call dispatched | user=%s", current_user.id)
        quiz = await loop.run_in_executor(
            None,
            lambda: generate_quiz(
                text,
                mcq_count=request.mcq_count,
                difficulty=request.difficulty.value.capitalize(),
                instructions=request.additional_instructions,
            ),
        )
        count = len(quiz.get("questions") or quiz.get("mcqs") or [])
        logger.info(
            "Quiz generation complete | user=%s | questions=%d",
            current_user.id, count,
        )
        return JSONResponse(content=quiz)
    except Exception as e:
        logger.error(
            "Quiz generation failed | user=%s | material_ids=%s | error=%s",
            current_user.id, ids, e, exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to generate quiz")

