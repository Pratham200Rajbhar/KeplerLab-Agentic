from __future__ import annotations

from typing import Any, Dict, Iterable, List


def evaluate_quiz(content: Dict[str, Any], answers: Iterable[dict]) -> Dict[str, Any]:
    """Evaluate quiz answers against generated day content."""
    quiz = (content or {}).get("quiz") or {}
    questions = quiz.get("questions") or []
    pass_score = float(quiz.get("pass_score") or 0.7)

    submitted = {
        str(a.get("question_id") or ""): str(a.get("selected_option") or "").strip().upper()
        for a in (answers or [])
    }

    if not questions:
        return {
            "passed": True,
            "score": 1.0,
            "accuracy": 1.0,
            "wrong_topics": [],
            "correct_topics": [],
            "feedback": "No quiz questions were generated for this day.",
        }

    correct = 0
    wrong_topics: List[str] = []
    correct_topics: List[str] = []

    for q in questions:
        qid = str(q.get("id") or "")
        expected = str(q.get("correct_option") or "").strip().upper()
        selected = submitted.get(qid, "")
        topic = str(q.get("topic") or "core concepts")

        if selected and selected == expected:
            correct += 1
            correct_topics.append(topic)
        else:
            wrong_topics.append(topic)

    total = len(questions)
    score = (correct / total) if total else 0.0
    passed = score >= pass_score

    if passed:
        feedback = f"Great work. You answered {correct}/{total} correctly."
    else:
        feedback = f"You answered {correct}/{total} correctly. Review weak areas and retry."

    return {
        "passed": passed,
        "score": round(score, 4),
        "accuracy": round(score, 4),
        "wrong_topics": sorted(set(wrong_topics)),
        "correct_topics": sorted(set(correct_topics)),
        "feedback": feedback,
    }
