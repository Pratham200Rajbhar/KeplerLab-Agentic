from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List

from pydantic import BaseModel, Field

from app.services.llm_service.structured_invoker import async_invoke_structured

logger = logging.getLogger(__name__)


class _LessonSection(BaseModel):
    heading: str = Field(..., min_length=4, max_length=180)
    text: str = Field(..., min_length=24, max_length=1600)


class _InteractionQuestion(BaseModel):
    prompt: str = Field(..., min_length=12, max_length=500)
    expected_keywords: List[str] = Field(default_factory=list, min_length=2, max_length=7)
    topic: str = Field(..., min_length=2, max_length=160)


class _Choice(BaseModel):
    label: str = Field(..., min_length=1, max_length=2)
    text: str = Field(..., min_length=2, max_length=500)


class _QuizQuestion(BaseModel):
    stem: str = Field(..., min_length=16, max_length=500)
    options: List[_Choice] = Field(..., min_length=4, max_length=4)
    correct_option: str = Field(..., min_length=1, max_length=2)
    topic: str = Field(..., min_length=2, max_length=160)
    explanation: str = Field(..., min_length=12, max_length=700)


class _GameRound(BaseModel):
    prompt: str = Field(..., min_length=12, max_length=500)
    choices: List[_Choice] = Field(..., min_length=3, max_length=3)
    correct_choice: str = Field(..., min_length=1, max_length=2)
    topic: str = Field(..., min_length=2, max_length=160)


class _AIDayContent(BaseModel):
    lesson_sections: List[_LessonSection] = Field(..., min_length=3, max_length=5)
    interaction_questions: List[_InteractionQuestion] = Field(..., min_length=2, max_length=4)
    task_instructions: List[str] = Field(..., min_length=3, max_length=6)
    task_completion_criteria: List[str] = Field(..., min_length=3, max_length=6)
    quiz_questions: List[_QuizQuestion] = Field(..., min_length=4, max_length=6)
    game_rounds: List[_GameRound] = Field(..., min_length=3, max_length=5)
    reinforcement_focus: str = Field(..., min_length=2, max_length=200)
    estimated_minutes: int = Field(default=30, ge=15, le=90)


def _extract_weak_topics(weak_topics: Iterable[dict]) -> List[str]:
    topics: List[str] = []
    for row in weak_topics:
        topic = str(row.get("topic") or "").strip()
        if topic:
            topics.append(topic)
    return topics


def _topic_keywords(topic: str) -> List[str]:
    words = [w.strip().lower() for w in topic.replace("/", " ").replace("-", " ").split() if w.strip()]
    if not words:
        return ["concept", "application"]
    return list(dict.fromkeys(words[:4]))


def _normalize_label(value: str, allowed: List[str], default: str) -> str:
    candidate = str(value or "").strip().upper()
    if candidate in allowed:
        return candidate
    return default


def _normalize_choices(options: List[dict], expected_labels: List[str], fallback_prefix: str) -> List[dict]:
    normalized: List[dict] = []
    for idx, label in enumerate(expected_labels):
        option = options[idx] if idx < len(options) else {}
        text = str(option.get("text") or "").strip()
        if not text:
            text = f"{fallback_prefix} {label}"
        normalized.append({"label": label, "text": text})
    return normalized


def _build_ai_prompt(
    topic: str,
    level: str,
    goal_type: str,
    day_number: int,
    day_title: str,
    weak_topic_names: List[str],
) -> str:
    weak_topics_text = ", ".join(weak_topic_names) if weak_topic_names else "None identified"

    return (
        "You are an elite AI learning designer creating a daily lesson pack.\n"
        "Return STRICT JSON only (no markdown, no commentary) using exactly this schema:\n"
        "{\n"
        '  "lesson_sections": [{"heading": "...", "text": "..."}],\n'
        '  "interaction_questions": [{"prompt": "...", "expected_keywords": ["..."], "topic": "..."}],\n'
        '  "task_instructions": ["..."],\n'
        '  "task_completion_criteria": ["..."],\n'
        '  "quiz_questions": [{"stem": "...", "options": [{"label": "A", "text": "..."}, {"label": "B", "text": "..."}, {"label": "C", "text": "..."}, {"label": "D", "text": "..."}], "correct_option": "A", "topic": "...", "explanation": "..."}],\n'
        '  "game_rounds": [{"prompt": "...", "choices": [{"label": "A", "text": "..."}, {"label": "B", "text": "..."}, {"label": "C", "text": "..."}], "correct_choice": "A", "topic": "..."}],\n'
        '  "reinforcement_focus": "...",\n'
        '  "estimated_minutes": 30\n'
        "}\n\n"
        "Rules:\n"
        "1) Fully customize to the provided context. Avoid generic filler.\n"
        "2) Make quiz and game scenario-based and conceptually meaningful.\n"
        "3) Interaction prompts should diagnose misunderstanding, not simple recall.\n"
        "4) Keep language clear and precise for the learner level.\n"
        "5) Use realistic practical framing for task instructions.\n\n"
        f"Context:\n"
        f"- Topic: {topic}\n"
        f"- Level: {level}\n"
        f"- Goal type: {goal_type}\n"
        f"- Day number: {day_number}\n"
        f"- Day title: {day_title}\n"
        f"- Weak topics from prior attempts: {weak_topics_text}\n"
    )


async def _generate_ai_raw_content(
    topic: str,
    level: str,
    goal_type: str,
    day_number: int,
    day_title: str,
    weak_topic_names: List[str],
) -> _AIDayContent:
    prompt = _build_ai_prompt(
        topic=topic,
        level=level,
        goal_type=goal_type,
        day_number=day_number,
        day_title=day_title,
        weak_topic_names=weak_topic_names,
    )
    return await async_invoke_structured(prompt, _AIDayContent, max_retries=2)


def _to_runtime_payload(
    ai_content: _AIDayContent,
    topic: str,
    day_number: int,
    day_title: str,
    weak_topic_names: List[str],
) -> Dict[str, Any]:
    lesson_sections = [
        {"heading": section.heading, "text": section.text}
        for section in ai_content.lesson_sections
    ]

    interaction_questions: List[dict] = []
    for idx, question in enumerate(ai_content.interaction_questions, start=1):
        keywords = [str(k).strip().lower() for k in question.expected_keywords if str(k).strip()]
        if len(keywords) < 2:
            keywords = _topic_keywords(question.topic)
        interaction_questions.append(
            {
                "id": f"interaction_{day_number}_{idx}",
                "prompt": question.prompt,
                "expected_keywords": keywords[:5],
                "topic": question.topic,
            }
        )

    quiz_questions: List[dict] = []
    for idx, question in enumerate(ai_content.quiz_questions, start=1):
        options = _normalize_choices(
            [item.model_dump() for item in question.options],
            expected_labels=["A", "B", "C", "D"],
            fallback_prefix="Option",
        )
        correct_option = _normalize_label(question.correct_option, ["A", "B", "C", "D"], "A")
        quiz_questions.append(
            {
                "id": f"quiz_{day_number}_{idx}",
                "stem": question.stem,
                "options": options,
                "correct_option": correct_option,
                "topic": question.topic,
                "explanation": question.explanation,
            }
        )

    game_rounds: List[dict] = []
    for idx, round_item in enumerate(ai_content.game_rounds, start=1):
        choices = _normalize_choices(
            [item.model_dump() for item in round_item.choices],
            expected_labels=["A", "B", "C"],
            fallback_prefix="Choice",
        )
        correct_choice = _normalize_label(round_item.correct_choice, ["A", "B", "C"], "A")
        game_rounds.append(
            {
                "id": f"game_{day_number}_{idx}",
                "prompt": round_item.prompt,
                "choices": choices,
                "correct_choice": correct_choice,
                "topic": round_item.topic,
            }
        )

    reinforcement_focus = ai_content.reinforcement_focus.strip() or (weak_topic_names[0] if weak_topic_names else topic)

    return {
        "lesson": {
            "title": day_title,
            "sections": lesson_sections,
        },
        "interaction": {
            "questions": interaction_questions,
        },
        "task": {
            "title": f"Applied Task - Day {day_number}",
            "instructions": [str(item).strip() for item in ai_content.task_instructions if str(item).strip()],
            "completion_criteria": [
                str(item).strip() for item in ai_content.task_completion_criteria if str(item).strip()
            ],
        },
        "quiz": {
            "pass_score": 0.7,
            "questions": quiz_questions,
        },
        "game": {
            "type": "rapid_choice",
            "rounds": game_rounds,
        },
        "metadata": {
            "topic": topic,
            "day_number": day_number,
            "reinforcement_focus": reinforcement_focus,
            "weak_topics": weak_topic_names,
            "estimated_minutes": int(ai_content.estimated_minutes),
            "generation_source": "ai",
        },
    }


def _generate_fallback_content(path: Any, day: Any, weak_topics: Iterable[dict]) -> Dict[str, Any]:
    topic = str(getattr(path, "topic", "Learning Topic"))
    level = str(getattr(path, "level", "beginner"))
    goal_type = str(getattr(path, "goalType", "concept_mastery"))
    day_number = int(getattr(day, "dayNumber", 1))
    day_title = str(getattr(day, "title", f"Day {day_number}"))

    weak_topic_names = _extract_weak_topics(weak_topics)
    reinforcement_focus = weak_topic_names[0] if weak_topic_names else topic
    keywords = _topic_keywords(reinforcement_focus)

    quiz_questions = []
    for i in range(1, 6):
        correct_letter = ["A", "B", "C", "D"][i % 4]
        options = {
            "A": f"Foundational view of {reinforcement_focus}",
            "B": f"Practical application of {reinforcement_focus}",
            "C": f"Common misconception about {reinforcement_focus}",
            "D": f"Unrelated approach to {reinforcement_focus}",
        }
        quiz_questions.append(
            {
                "id": f"quiz_{day_number}_{i}",
                "stem": f"Which option best supports day {day_number} objective for {reinforcement_focus}?",
                "options": [
                    {"label": "A", "text": options["A"]},
                    {"label": "B", "text": options["B"]},
                    {"label": "C", "text": options["C"]},
                    {"label": "D", "text": options["D"]},
                ],
                "correct_option": correct_letter,
                "topic": reinforcement_focus,
                "explanation": f"Option {correct_letter} aligns best with the learning objective.",
            }
        )

    game_rounds = []
    for i in range(1, 4):
        correct_choice = ["A", "B", "C"][i % 3]
        game_rounds.append(
            {
                "id": f"game_{day_number}_{i}",
                "prompt": f"Choose the strongest action for practicing {reinforcement_focus}.",
                "choices": [
                    {"label": "A", "text": "Review one concept and explain it in your own words"},
                    {"label": "B", "text": f"Apply {reinforcement_focus} to a small practical scenario"},
                    {"label": "C", "text": "Skip checks and jump to unrelated material"},
                ],
                "correct_choice": correct_choice,
                "topic": reinforcement_focus,
            }
        )

    return {
        "lesson": {
            "title": day_title,
            "sections": [
                {
                    "heading": f"Day {day_number} Learning Goal",
                    "text": (
                        f"Today you will build confidence in {topic} with a focus on {reinforcement_focus}. "
                        f"Level: {level}. Goal type: {goal_type}."
                    ),
                },
                {
                    "heading": "Key Ideas",
                    "text": (
                        f"Concentrate on these concepts: {', '.join(keywords)}. "
                        "Understand definitions first, then apply them to examples."
                    ),
                },
                {
                    "heading": "How to Succeed Today",
                    "text": "Move in sequence: learn, interact, practice, validate, then challenge yourself.",
                },
            ],
        },
        "interaction": {
            "questions": [
                {
                    "id": f"interaction_{day_number}_1",
                    "prompt": f"In your own words, explain why {reinforcement_focus} matters in {topic}.",
                    "expected_keywords": keywords[:2],
                    "topic": reinforcement_focus,
                },
                {
                    "id": f"interaction_{day_number}_2",
                    "prompt": f"Give one practical scenario where {reinforcement_focus} would be useful.",
                    "expected_keywords": keywords[1:3] or keywords[:2],
                    "topic": reinforcement_focus,
                },
            ]
        },
        "task": {
            "title": f"Applied Task - Day {day_number}",
            "instructions": [
                f"Create a short workflow using {reinforcement_focus}.",
                "Write the steps, assumptions, and expected result.",
                "Mention one risk and how you would mitigate it.",
            ],
            "completion_criteria": [
                "Includes at least 3 clear steps",
                "Explains expected outcome",
                "Includes one realistic risk",
            ],
        },
        "quiz": {
            "pass_score": 0.7,
            "questions": quiz_questions,
        },
        "game": {
            "type": "rapid_choice",
            "rounds": game_rounds,
        },
        "metadata": {
            "topic": topic,
            "day_number": day_number,
            "reinforcement_focus": reinforcement_focus,
            "weak_topics": weak_topic_names,
            "estimated_minutes": 25,
            "generation_source": "fallback",
        },
    }


async def generate_day_content(path: Any, day: Any, weak_topics: Iterable[dict]) -> Dict[str, Any]:
    """Generate structured daily content payload with AI-first strategy and robust fallback."""
    topic = str(getattr(path, "topic", "Learning Topic"))
    level = str(getattr(path, "level", "beginner"))
    goal_type = str(getattr(path, "goalType", "concept_mastery"))
    day_number = int(getattr(day, "dayNumber", 1))
    day_title = str(getattr(day, "title", f"Day {day_number}"))
    weak_topic_names = _extract_weak_topics(weak_topics)

    try:
        ai_content = await _generate_ai_raw_content(
            topic=topic,
            level=level,
            goal_type=goal_type,
            day_number=day_number,
            day_title=day_title,
            weak_topic_names=weak_topic_names,
        )
        return _to_runtime_payload(
            ai_content=ai_content,
            topic=topic,
            day_number=day_number,
            day_title=day_title,
            weak_topic_names=weak_topic_names,
        )
    except Exception as exc:
        logger.warning(
            "AI day generation failed for path '%s' day %s; using fallback. error=%s",
            topic,
            day_number,
            exc,
        )
        return _generate_fallback_content(path, day, weak_topics)
