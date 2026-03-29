from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.db.prisma_client import prisma
from app.services.learning.adaptive_engine import get_weak_topics


def _to_iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


async def ensure_progress(user_id: str, path_id: str):
    progress = await prisma.learningprogress.find_first(
        where={"userId": user_id, "pathId": path_id}
    )
    if progress:
        return progress

    return await prisma.learningprogress.create(
        data={
            "userId": user_id,
            "pathId": path_id,
            "currentDay": 1,
            "completionPercentage": 0.0,
            "streak": 0,
        }
    )


async def refresh_progress(user_id: str, path_id: str, touch_last_active: bool = False) -> dict:
    progress = await ensure_progress(user_id, path_id)
    days = await prisma.learningday.find_many(
        where={"pathId": path_id},
        order={"dayNumber": "asc"},
    )

    total_days = len(days)
    completed_days = sum(1 for d in days if str(d.status) == "completed")
    completion_percentage = round((completed_days / total_days) * 100.0, 2) if total_days else 0.0

    unlocked_pending = [d for d in days if bool(d.isUnlocked) and str(d.status) != "completed"]
    current_day = int(unlocked_pending[0].dayNumber) if unlocked_pending else (total_days or 1)

    quiz_attempts = await prisma.learningattempt.find_many(
        where={
            "userId": user_id,
            "pathId": path_id,
            "attemptType": "quiz",
        }
    )
    scores = [float(a.score) for a in quiz_attempts if a.score is not None]
    quiz_accuracy = round(sum(scores) / len(scores), 4) if scores else None

    streak = int(progress.streak or 0)
    last_active = progress.lastActive

    if touch_last_active:
        now = datetime.now(timezone.utc)
        if last_active:
            day_delta = (now.date() - last_active.date()).days
            if day_delta == 0:
                streak = max(streak, 1)
            elif day_delta == 1:
                streak = streak + 1 if streak > 0 else 1
            else:
                streak = 1
        else:
            streak = 1
        last_active = now

    updated = await prisma.learningprogress.update(
        where={"id": str(progress.id)},
        data={
            "currentDay": current_day,
            "completionPercentage": completion_percentage,
            "streak": streak,
            "quizAccuracy": quiz_accuracy,
            "lastActive": last_active,
        },
    )

    weak_topics = await get_weak_topics(user_id, path_id)

    return {
        "path_id": str(path_id),
        "current_day": int(updated.currentDay),
        "completion_percentage": float(updated.completionPercentage or 0.0),
        "streak": int(updated.streak or 0),
        "quiz_accuracy": float(updated.quizAccuracy) if updated.quizAccuracy is not None else None,
        "last_active": _to_iso(updated.lastActive),
        "weak_topics": weak_topics,
    }
