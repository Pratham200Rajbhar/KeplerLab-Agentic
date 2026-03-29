from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from pydantic import BaseModel, Field
from prisma import Json

from app.db.prisma_client import prisma
from app.services.learning.adaptive_engine import apply_topic_feedback, get_weak_topics
from app.services.learning.day_generator import generate_day_content
from app.services.learning.game_engine import evaluate_game
from app.services.learning.path_service import get_day_and_path
from app.services.learning.progress_tracker import refresh_progress
from app.services.learning.quiz_engine import evaluate_quiz
from app.services.llm_service.llm import get_llm
from app.services.llm_service.structured_invoker import async_invoke_structured

logger = logging.getLogger(__name__)

_STAGE_ORDER = ["LESSON", "INTERACTION", "TASK", "QUIZ", "GAME", "COMPLETE"]
_STAGE_TO_INDEX = {name: idx + 1 for idx, name in enumerate(_STAGE_ORDER)}


class LearningEngineError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class _LearningAssistOutput(BaseModel):
    answer: str = Field(..., min_length=12, max_length=8000)
    understanding_check: str = Field(..., min_length=8, max_length=500)
    next_steps: List[str] = Field(default_factory=list, min_length=2, max_length=6)
    related_concepts: List[str] = Field(default_factory=list, max_length=10)


def _json_value(value: Any) -> Json:
    try:
        safe_value = json.loads(json.dumps(value, default=str))
    except Exception:
        safe_value = {"value": str(value)}
    return Json(safe_value)


def _normalize_content(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _to_day_payload(day: Any) -> Dict[str, Any]:
    return {
        "id": str(day.id),
        "day_number": int(day.dayNumber),
        "title": str(day.title),
        "status": str(day.status),
        "is_unlocked": bool(day.isUnlocked),
    }


def _to_session_payload(session: Any) -> Dict[str, Any]:
    return {
        "stage": str(session.stage),
        "stage_index": int(session.stageIndex),
        "total_stages": len(_STAGE_ORDER),
        "can_complete_day": bool(session.canCompleteDay),
    }


async def _ensure_generated_content(day: Any, path: Any, force_regenerate: bool, user_id: str):
    content = _normalize_content(day.generatedContent)
    if content and not force_regenerate:
        return day, content

    weak_topics = await get_weak_topics(user_id, str(path.id), limit=4)
    content = await generate_day_content(path, day, weak_topics)
    day = await prisma.learningday.update(
        where={"id": str(day.id)},
        data={
            "generatedContent": _json_value(content),
            "generatedAt": datetime.now(timezone.utc),
        },
    )
    return day, content


async def _ensure_session(user_id: str, path_id: str, day_id: str):
    session = await prisma.learningsessionstate.find_first(
        where={"userId": user_id, "dayId": day_id}
    )
    if session:
        return session

    return await prisma.learningsessionstate.create(
        data={
            "userId": user_id,
            "pathId": path_id,
            "dayId": day_id,
            "stage": "LESSON",
            "stageIndex": _STAGE_TO_INDEX["LESSON"],
            "canCompleteDay": False,
            "stateData": _json_value({}),
        }
    )


async def _set_stage(session_id: str, stage: str, can_complete_day: bool = False, state_data: Optional[dict] = None):
    data: Dict[str, Any] = {
        "stage": stage,
        "stageIndex": _STAGE_TO_INDEX[stage],
        "canCompleteDay": can_complete_day,
    }
    if state_data is not None:
        data["stateData"] = _json_value(state_data)

    return await prisma.learningsessionstate.update(
        where={"id": session_id},
        data=data,
    )


async def _record_attempt(
    user_id: str,
    path_id: str,
    day_id: str,
    stage: str,
    attempt_type: str,
    input_data: dict,
    result_data: dict,
    score: Optional[float],
    passed: bool,
) -> None:
    await prisma.learningattempt.create(
        data={
            "userId": user_id,
            "pathId": path_id,
            "dayId": day_id,
            "stage": stage,
            "attemptType": attempt_type,
            "inputData": _json_value(input_data),
            "resultData": _json_value(result_data),
            "score": score,
            "passed": passed,
        }
    )


def _evaluate_interaction(questions: List[dict], answers: Iterable[dict]) -> Dict[str, Any]:
    submitted = {
        str(a.get("question_id") or ""): str(a.get("response") or "")
        for a in (answers or [])
    }

    if not questions:
        return {
            "passed": True,
            "score": 1.0,
            "feedback": "Interaction not required for this day.",
            "wrong_topics": [],
            "correct_topics": [],
        }

    score_total = 0.0
    wrong_topics: List[str] = []
    correct_topics: List[str] = []

    for question in questions:
        question_id = str(question.get("id") or "")
        response = submitted.get(question_id, "").strip()
        expected_keywords = [str(v).lower() for v in (question.get("expected_keywords") or []) if str(v).strip()]
        topic = str(question.get("topic") or "core concepts")

        question_score = 0.0
        if len(response) >= 24:
            question_score += 0.6
        if expected_keywords and any(k in response.lower() for k in expected_keywords):
            question_score += 0.4

        question_score = min(question_score, 1.0)
        score_total += question_score

        if question_score >= 0.6:
            correct_topics.append(topic)
        else:
            wrong_topics.append(topic)

    score = score_total / len(questions)
    passed = score >= 0.65

    if passed:
        feedback = "Good job. Your responses showed understanding of key concepts."
    else:
        feedback = "Some responses need more detail. Include definitions and a practical example, then retry."

    return {
        "passed": passed,
        "score": round(score, 4),
        "feedback": feedback,
        "wrong_topics": sorted(set(wrong_topics)),
        "correct_topics": sorted(set(correct_topics)),
    }


def _evaluate_task(submission: str) -> Dict[str, Any]:
    text = (submission or "").strip()
    word_count = len([w for w in text.split() if w.strip()])
    passed = word_count >= 30
    score = min(1.0, word_count / 80.0)

    if passed:
        feedback = "Task accepted. You provided enough detail to move forward."
    else:
        feedback = "Please provide a more detailed submission (aim for at least 30 words)."

    return {
        "passed": passed,
        "score": round(score, 4),
        "feedback": feedback,
        "word_count": word_count,
    }


def _compact_content_snapshot(content: Dict[str, Any]) -> Dict[str, Any]:
    lesson_sections = (content.get("lesson") or {}).get("sections") or []
    interaction_questions = (content.get("interaction") or {}).get("questions") or []
    quiz_questions = (content.get("quiz") or {}).get("questions") or []
    game_rounds = (content.get("game") or {}).get("rounds") or []

    return {
        "lesson": lesson_sections[:2],
        "interaction": [
            {
                "prompt": q.get("prompt"),
                "topic": q.get("topic"),
            }
            for q in interaction_questions[:2]
        ],
        "task": {
            "instructions": ((content.get("task") or {}).get("instructions") or [])[:3],
        },
        "quiz": [
            {
                "stem": q.get("stem"),
                "topic": q.get("topic"),
            }
            for q in quiz_questions[:2]
        ],
        "game": [
            {
                "prompt": r.get("prompt"),
                "topic": r.get("topic"),
            }
            for r in game_rounds[:2]
        ],
        "metadata": content.get("metadata") or {},
    }


def _clean_items(items: List[Any], *, max_items: int) -> List[str]:
    cleaned = [str(item).strip() for item in (items or []) if str(item).strip()]
    return cleaned[:max_items]


def _build_assist_prompt(
    *,
    topic: str,
    level: str,
    goal_type: str,
    day_number: int,
    day_title: str,
    stage: str,
    weak_topics: List[str],
    question: str,
    compact_content: Dict[str, Any],
) -> str:
    weak_topics_text = ", ".join(weak_topics) if weak_topics else "None identified"
    content_text = json.dumps(compact_content, ensure_ascii=True)

    return (
        "You are an AI learning mentor.\n"
        "Explain clearly, diagnose confusion, and help the learner move forward with confidence.\n"
        "Return STRICT JSON only:\n"
        "{\n"
        '  "answer": "...",\n'
        '  "understanding_check": "...",\n'
        '  "next_steps": ["..."],\n'
        '  "related_concepts": ["..."]\n'
        "}\n\n"
        "Rules:\n"
        "1) Give a practical, step-by-step answer tied to the learner's current day and stage.\n"
        "2) Keep tone supportive and precise.\n"
        "3) Use examples and analogies only when useful.\n"
        "4) next_steps must be concrete actions the learner can do now.\n"
        "5) understanding_check should be one quick question to verify learning.\n\n"
        f"Learning context:\n"
        f"- Topic: {topic}\n"
        f"- Level: {level}\n"
        f"- Goal type: {goal_type}\n"
        f"- Day: {day_number} ({day_title})\n"
        f"- Current stage: {stage}\n"
        f"- Weak topics: {weak_topics_text}\n"
        f"- Day content snapshot: {content_text[:9000]}\n\n"
        f"Learner question: {question}\n"
    )


async def ask_learning_assist(day_id: str, user_id: str, question: str) -> Dict[str, Any]:
    cleaned_question = str(question or "").strip()
    if not cleaned_question:
        raise LearningEngineError("Question is required", status_code=400)

    day, path, content, session = await _load_context(day_id, user_id)
    weak_topic_rows = await get_weak_topics(user_id, str(path.id), limit=5)
    weak_topics = [str(item.get("topic") or "").strip() for item in weak_topic_rows if str(item.get("topic") or "").strip()]
    compact_content = _compact_content_snapshot(content)

    prompt = _build_assist_prompt(
        topic=str(getattr(path, "topic", "Learning Topic")),
        level=str(getattr(path, "level", "beginner")),
        goal_type=str(getattr(path, "goalType", "concept_mastery")),
        day_number=int(getattr(day, "dayNumber", 1)),
        day_title=str(getattr(day, "title", f"Day {int(getattr(day, 'dayNumber', 1))}")),
        stage=str(getattr(session, "stage", "LESSON")),
        weak_topics=weak_topics,
        question=cleaned_question,
        compact_content=compact_content,
    )

    try:
        structured = await async_invoke_structured(prompt, _LearningAssistOutput, max_retries=1)
        return {
            "answer": structured.answer,
            "understanding_check": structured.understanding_check,
            "next_steps": _clean_items(structured.next_steps, max_items=5),
            "related_concepts": _clean_items(structured.related_concepts, max_items=6),
            "stage": str(getattr(session, "stage", "LESSON")),
            "day_id": str(day.id),
        }
    except Exception as exc:
        logger.warning("Structured learning assist failed for day %s: %s", day_id, exc)

    llm = get_llm(mode="chat", temperature=0.25, max_tokens=1200)
    fallback_prompt = (
        "You are an AI learning mentor. Answer the learner question using the provided context. "
        "Be clear, specific, and practical.\n\n"
        f"Context: {json.dumps(compact_content, ensure_ascii=True)[:9000]}\n\n"
        f"Question: {cleaned_question}"
    )
    response = await llm.ainvoke(fallback_prompt)
    answer_text = getattr(response, "content", str(response)).strip()
    if not answer_text:
        answer_text = "I could not generate a complete answer right now. Please retry your question."

    return {
        "answer": answer_text,
        "understanding_check": "Can you explain the core idea in your own words?",
        "next_steps": [
            "Summarize the concept in 3 bullet points.",
            "Apply it to one concrete example from your work.",
            "Ask a follow-up question about any unclear step.",
        ],
        "related_concepts": weak_topics[:4],
        "stage": str(getattr(session, "stage", "LESSON")),
        "day_id": str(day.id),
    }


async def _load_context(day_id: str, user_id: str) -> tuple[Any, Any, Dict[str, Any], Any]:
    day, path = await get_day_and_path(day_id, user_id)
    if not day or not path:
        raise LearningEngineError("Learning day not found", status_code=404)

    if not bool(day.isUnlocked):
        raise LearningEngineError("This day is locked. Complete previous day first.", status_code=403)

    day, content = await _ensure_generated_content(day, path, False, user_id)
    session = await _ensure_session(user_id, str(path.id), str(day.id))

    if str(day.status) == "pending":
        day = await prisma.learningday.update(
            where={"id": str(day.id)},
            data={"status": "in_progress"},
        )

    return day, path, content, session


async def open_day(day_id: str, user_id: str, force_regenerate: bool = False) -> Dict[str, Any]:
    day, path = await get_day_and_path(day_id, user_id)
    if not day or not path:
        raise LearningEngineError("Learning day not found", status_code=404)

    if not bool(day.isUnlocked):
        raise LearningEngineError("This day is locked. Complete previous day first.", status_code=403)

    day, content = await _ensure_generated_content(day, path, force_regenerate, user_id)
    session = await _ensure_session(user_id, str(path.id), str(day.id))

    if str(day.status) == "pending":
        day = await prisma.learningday.update(
            where={"id": str(day.id)},
            data={"status": "in_progress"},
        )

    return {
        "day": _to_day_payload(day),
        "session": _to_session_payload(session),
        "content": content,
    }


async def submit_interaction(day_id: str, user_id: str, answers: List[dict]) -> Dict[str, Any]:
    day, path, content, session = await _load_context(day_id, user_id)
    if str(session.stage) not in {"LESSON", "INTERACTION"}:
        raise LearningEngineError("Interaction stage is not active", status_code=409)

    interaction = content.get("interaction") or {}
    result = _evaluate_interaction(interaction.get("questions") or [], answers)

    await _record_attempt(
        user_id=user_id,
        path_id=str(path.id),
        day_id=str(day.id),
        stage="INTERACTION",
        attempt_type="interaction",
        input_data={"answers": answers},
        result_data=result,
        score=float(result["score"]),
        passed=bool(result["passed"]),
    )

    await apply_topic_feedback(
        user_id=user_id,
        path_id=str(path.id),
        wrong_topics=result.get("wrong_topics") or [],
        correct_topics=result.get("correct_topics") or [],
    )

    if result["passed"]:
        session = await _set_stage(str(session.id), "TASK")
        next_stage = "TASK"
    else:
        session = await _set_stage(str(session.id), "INTERACTION")
        next_stage = "INTERACTION"

    return {
        "stage": "INTERACTION",
        "passed": bool(result["passed"]),
        "score": float(result["score"]),
        "feedback": result["feedback"],
        "next_stage": next_stage,
        "session": _to_session_payload(session),
    }


async def submit_task(day_id: str, user_id: str, submission: str) -> Dict[str, Any]:
    day, path, _content, session = await _load_context(day_id, user_id)
    if str(session.stage) != "TASK":
        raise LearningEngineError("Task stage is not active", status_code=409)

    result = _evaluate_task(submission)

    await _record_attempt(
        user_id=user_id,
        path_id=str(path.id),
        day_id=str(day.id),
        stage="TASK",
        attempt_type="task",
        input_data={"submission": submission},
        result_data=result,
        score=float(result["score"]),
        passed=bool(result["passed"]),
    )

    if result["passed"]:
        session = await _set_stage(str(session.id), "QUIZ")
        next_stage = "QUIZ"
    else:
        next_stage = "TASK"

    return {
        "stage": "TASK",
        "passed": bool(result["passed"]),
        "score": float(result["score"]),
        "feedback": result["feedback"],
        "next_stage": next_stage,
        "session": _to_session_payload(session),
    }


async def submit_quiz(day_id: str, user_id: str, answers: List[dict]) -> Dict[str, Any]:
    day, path, content, session = await _load_context(day_id, user_id)
    if str(session.stage) != "QUIZ":
        raise LearningEngineError("Quiz stage is not active", status_code=409)

    result = evaluate_quiz(content, answers)

    await _record_attempt(
        user_id=user_id,
        path_id=str(path.id),
        day_id=str(day.id),
        stage="QUIZ",
        attempt_type="quiz",
        input_data={"answers": answers},
        result_data=result,
        score=float(result.get("score") or 0.0),
        passed=bool(result["passed"]),
    )

    await apply_topic_feedback(
        user_id=user_id,
        path_id=str(path.id),
        wrong_topics=result.get("wrong_topics") or [],
        correct_topics=result.get("correct_topics") or [],
    )

    if result["passed"]:
        session = await _set_stage(str(session.id), "GAME")
        next_stage = "GAME"
    else:
        next_stage = "QUIZ"

    await refresh_progress(user_id, str(path.id), touch_last_active=False)

    return {
        "stage": "QUIZ",
        "passed": bool(result["passed"]),
        "score": float(result.get("score") or 0.0),
        "accuracy": float(result.get("accuracy") or 0.0),
        "feedback": result["feedback"],
        "weak_topics": result.get("wrong_topics") or [],
        "next_stage": next_stage,
        "session": _to_session_payload(session),
    }


async def submit_game(day_id: str, user_id: str, moves: List[dict]) -> Dict[str, Any]:
    day, path, content, session = await _load_context(day_id, user_id)
    if str(session.stage) != "GAME":
        raise LearningEngineError("Game stage is not active", status_code=409)

    result = evaluate_game(content, moves)

    await _record_attempt(
        user_id=user_id,
        path_id=str(path.id),
        day_id=str(day.id),
        stage="GAME",
        attempt_type="game",
        input_data={"moves": moves},
        result_data=result,
        score=float(result.get("score") or 0.0),
        passed=bool(result["passed"]),
    )

    if result["passed"]:
        session = await _set_stage(str(session.id), "COMPLETE", can_complete_day=True)
        next_stage = "COMPLETE"
    else:
        next_stage = "GAME"

    return {
        "stage": "GAME",
        "passed": bool(result["passed"]),
        "score": float(result.get("score") or 0.0),
        "xp_awarded": int(result.get("xp_awarded") or 0),
        "feedback": result["feedback"],
        "next_stage": next_stage,
        "session": _to_session_payload(session),
    }


async def complete_day(day_id: str, user_id: str) -> Dict[str, Any]:
    day, path, _content, session = await _load_context(day_id, user_id)

    if str(session.stage) != "COMPLETE" or not bool(session.canCompleteDay):
        raise LearningEngineError("Complete all stages before finishing the day.", status_code=409)

    if str(day.status) != "completed":
        day = await prisma.learningday.update(
            where={"id": str(day.id)},
            data={"status": "completed"},
        )

    next_day = await prisma.learningday.find_first(
        where={"pathId": str(path.id), "dayNumber": int(day.dayNumber) + 1}
    )
    unlocked_next_day_id: Optional[str] = None
    if next_day and not bool(next_day.isUnlocked):
        next_day = await prisma.learningday.update(
            where={"id": str(next_day.id)},
            data={"isUnlocked": True},
        )
        unlocked_next_day_id = str(next_day.id)

    progress = await refresh_progress(user_id, str(path.id), touch_last_active=True)

    remaining = await prisma.learningday.count(
        where={"pathId": str(path.id), "status": {"not": "completed"}}
    )
    if remaining == 0 and str(path.status) != "completed":
        await prisma.learningpath.update(
            where={"id": str(path.id)},
            data={"status": "completed"},
        )

    return {
        "day_id": str(day.id),
        "status": "completed",
        "unlocked_next_day_id": unlocked_next_day_id,
        "progress": progress,
    }
