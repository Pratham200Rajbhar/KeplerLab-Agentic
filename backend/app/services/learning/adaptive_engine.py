from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List

from app.db.prisma_client import prisma


def _normalize_topic(topic: str) -> str:
    return " ".join((topic or "").strip().split()).lower()


def _to_serializable(rows: list) -> List[dict]:
    data: List[dict] = []
    for row in rows:
        data.append(
            {
                "id": str(row.id),
                "topic": str(row.topic),
                "confidence": float(row.confidence or 0.0),
                "mistake_count": int(row.mistakeCount or 0),
                "last_observed_at": row.lastObservedAt.isoformat() if row.lastObservedAt else None,
            }
        )
    return data


async def get_weak_topics(user_id: str, path_id: str, limit: int = 5) -> List[dict]:
    rows = await prisma.learningweaktopic.find_many(
        where={"userId": user_id, "pathId": path_id},
        order={"updatedAt": "desc"},
    )
    rows.sort(key=lambda r: (float(r.confidence or 0.5), -int(r.mistakeCount or 0)))
    return _to_serializable(rows[:limit])


async def apply_topic_feedback(
    user_id: str,
    path_id: str,
    wrong_topics: Iterable[str],
    correct_topics: Iterable[str] | None = None,
) -> None:
    """Update weak-topic profile using latest assessment feedback."""
    now = datetime.now(timezone.utc)

    wrong_set = {_normalize_topic(t) for t in (wrong_topics or []) if _normalize_topic(t)}
    correct_set = {_normalize_topic(t) for t in (correct_topics or []) if _normalize_topic(t)}
    correct_set = correct_set - wrong_set

    for topic in wrong_set:
        existing = await prisma.learningweaktopic.find_first(
            where={"userId": user_id, "pathId": path_id, "topic": topic}
        )
        if existing:
            updated_confidence = max(0.0, float(existing.confidence or 0.5) - 0.08)
            await prisma.learningweaktopic.update(
                where={"id": str(existing.id)},
                data={
                    "confidence": updated_confidence,
                    "mistakeCount": int(existing.mistakeCount or 0) + 1,
                    "lastObservedAt": now,
                },
            )
        else:
            await prisma.learningweaktopic.create(
                data={
                    "userId": user_id,
                    "pathId": path_id,
                    "topic": topic,
                    "confidence": 0.42,
                    "mistakeCount": 1,
                    "lastObservedAt": now,
                }
            )

    for topic in correct_set:
        existing = await prisma.learningweaktopic.find_first(
            where={"userId": user_id, "pathId": path_id, "topic": topic}
        )
        if not existing:
            continue
        updated_confidence = min(1.0, float(existing.confidence or 0.5) + 0.03)
        await prisma.learningweaktopic.update(
            where={"id": str(existing.id)},
            data={
                "confidence": updated_confidence,
                "lastObservedAt": now,
            },
        )
