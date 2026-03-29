from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from app.models.learning_schemas import (
    AskLearningAssistRequest,
    CreateLearningPathRequest,
    OpenLearningDayRequest,
    SubmitGameRequest,
    SubmitInteractionRequest,
    SubmitQuizRequest,
    SubmitTaskRequest,
)
from app.services.auth import get_current_user
from app.services.learning.learning_engine import (
    LearningEngineError,
    ask_learning_assist,
    complete_day,
    open_day,
    submit_game,
    submit_interaction,
    submit_quiz,
    submit_task,
)
from app.services.learning.path_service import (
    create_path,
    get_path,
    get_path_progress,
    list_days,
    list_paths,
)
from app.services.learning.review_service import get_review_recommendations

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/learning", tags=["learning"])


@router.post("/paths")
async def create_learning_path(
    request: CreateLearningPathRequest,
    current_user=Depends(get_current_user),
):
    try:
        path = await create_path(
            user_id=str(current_user.id),
            topic=request.topic,
            duration_days=request.duration_days,
            level=request.level.value,
            goal_type=request.goal_type.value,
            title=request.title,
        )
        return JSONResponse(content=path, status_code=201)
    except Exception as exc:
        logger.exception("Failed to create learning path")
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/paths")
async def list_learning_paths(
    status: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
):
    paths = await list_paths(str(current_user.id), status=status)
    return JSONResponse(content={"paths": paths})


@router.get("/paths/{path_id}")
async def get_learning_path(
    path_id: str,
    current_user=Depends(get_current_user),
):
    path = await get_path(path_id, str(current_user.id))
    if not path:
        raise HTTPException(status_code=404, detail="Learning path not found")
    return JSONResponse(content=path)


@router.get("/paths/{path_id}/days")
async def get_learning_days(
    path_id: str,
    current_user=Depends(get_current_user),
):
    days = await list_days(path_id, str(current_user.id))
    if days is None:
        raise HTTPException(status_code=404, detail="Learning path not found")
    return JSONResponse(content={"days": days})


@router.post("/days/{day_id}/open")
async def open_learning_day(
    day_id: str,
    request: OpenLearningDayRequest,
    current_user=Depends(get_current_user),
):
    try:
        payload = await open_day(
            day_id=day_id,
            user_id=str(current_user.id),
            force_regenerate=request.force_regenerate,
        )
        return JSONResponse(content=payload)
    except LearningEngineError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/days/{day_id}/assist")
async def ask_learning_day_assist(
    day_id: str,
    request: AskLearningAssistRequest,
    current_user=Depends(get_current_user),
):
    try:
        payload = await ask_learning_assist(
            day_id=day_id,
            user_id=str(current_user.id),
            question=request.question,
        )
        return JSONResponse(content=payload)
    except LearningEngineError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/days/{day_id}/interaction")
async def submit_learning_interaction(
    day_id: str,
    request: SubmitInteractionRequest,
    current_user=Depends(get_current_user),
):
    try:
        payload = await submit_interaction(
            day_id=day_id,
            user_id=str(current_user.id),
            answers=[item.model_dump() for item in request.answers],
        )
        return JSONResponse(content=payload)
    except LearningEngineError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/days/{day_id}/task")
async def submit_learning_task(
    day_id: str,
    request: SubmitTaskRequest,
    current_user=Depends(get_current_user),
):
    try:
        payload = await submit_task(
            day_id=day_id,
            user_id=str(current_user.id),
            submission=request.submission,
        )
        return JSONResponse(content=payload)
    except LearningEngineError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/days/{day_id}/quiz")
async def submit_learning_quiz(
    day_id: str,
    request: SubmitQuizRequest,
    current_user=Depends(get_current_user),
):
    try:
        payload = await submit_quiz(
            day_id=day_id,
            user_id=str(current_user.id),
            answers=[item.model_dump() for item in request.answers],
        )
        return JSONResponse(content=payload)
    except LearningEngineError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/days/{day_id}/game")
async def submit_learning_game(
    day_id: str,
    request: SubmitGameRequest,
    current_user=Depends(get_current_user),
):
    try:
        payload = await submit_game(
            day_id=day_id,
            user_id=str(current_user.id),
            moves=[item.model_dump() for item in request.moves],
        )
        return JSONResponse(content=payload)
    except LearningEngineError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/days/{day_id}/complete")
async def complete_learning_day(
    day_id: str,
    current_user=Depends(get_current_user),
):
    try:
        payload = await complete_day(day_id=day_id, user_id=str(current_user.id))
        return JSONResponse(content=payload)
    except LearningEngineError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get("/paths/{path_id}/progress")
async def get_learning_progress(
    path_id: str,
    current_user=Depends(get_current_user),
):
    progress = await get_path_progress(path_id, str(current_user.id))
    if not progress:
        raise HTTPException(status_code=404, detail="Learning path not found")
    return JSONResponse(content=progress)


@router.get("/paths/{path_id}/review")
async def get_learning_review(
    path_id: str,
    current_user=Depends(get_current_user),
):
    review = await get_review_recommendations(path_id, str(current_user.id))
    if not review:
        raise HTTPException(status_code=404, detail="Learning path not found")
    return JSONResponse(content=review)
