from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.learning_enums import LearningGoalType, LearningLevel


class CreateLearningPathRequest(BaseModel):
    topic: str = Field(..., min_length=1, max_length=255)
    duration_days: int = Field(30, ge=7, le=90)
    level: LearningLevel = LearningLevel.beginner
    goal_type: LearningGoalType = LearningGoalType.concept_mastery
    title: Optional[str] = Field(None, min_length=1, max_length=255)

    @field_validator("topic")
    @classmethod
    def _normalize_topic(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Topic is required")
        return cleaned

    @field_validator("title", mode="before")
    @classmethod
    def _normalize_title(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return value


class OpenLearningDayRequest(BaseModel):
    force_regenerate: bool = False


class AskLearningAssistRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=4000)

    @field_validator("question")
    @classmethod
    def _normalize_question(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Question is required")
        return cleaned


class InteractionAnswer(BaseModel):
    question_id: str = Field(..., min_length=1, max_length=120)
    response: str = Field(..., min_length=1, max_length=4000)


class SubmitInteractionRequest(BaseModel):
    answers: List[InteractionAnswer] = Field(default_factory=list)


class SubmitTaskRequest(BaseModel):
    submission: str = Field(..., min_length=1, max_length=12000)


class QuizAnswer(BaseModel):
    question_id: str = Field(..., min_length=1, max_length=120)
    selected_option: str = Field(..., min_length=1, max_length=20)


class SubmitQuizRequest(BaseModel):
    answers: List[QuizAnswer] = Field(default_factory=list)


class GameMove(BaseModel):
    round_id: str = Field(..., min_length=1, max_length=120)
    answer: str = Field(..., min_length=1, max_length=1200)


class SubmitGameRequest(BaseModel):
    moves: List[GameMove] = Field(default_factory=list)


class LearningPathResponse(BaseModel):
    id: str
    title: str
    topic: str
    duration_days: int
    level: str
    goal_type: str
    status: str
    created_at: datetime
    updated_at: datetime


class LearningDayResponse(BaseModel):
    id: str
    day_number: int
    title: str
    description: Optional[str]
    status: str
    is_unlocked: bool
    has_generated_content: bool


class LearningProgressResponse(BaseModel):
    path_id: str
    current_day: int
    completion_percentage: float
    streak: int
    quiz_accuracy: Optional[float] = None
    last_active: Optional[datetime] = None
    weak_topics: List[Dict[str, Any]] = Field(default_factory=list)


class AskLearningAssistResponse(BaseModel):
    answer: str
    understanding_check: str
    next_steps: List[str] = Field(default_factory=list)
    related_concepts: List[str] = Field(default_factory=list)
    stage: str
    day_id: str
