from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.db.prisma_client import prisma
from app.services.learning.adaptive_engine import get_weak_topics


async def get_review_recommendations(path_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    path = await prisma.learningpath.find_first(where={"id": path_id, "userId": user_id})
    if not path:
        return None

    weak_topics = await get_weak_topics(user_id, path_id, limit=8)
    recommendations: List[dict] = []
    for item in weak_topics:
        confidence = float(item.get("confidence") or 0.0)
        reason = "Low confidence from recent checks" if confidence < 0.5 else "Recommended reinforcement"
        recommendations.append(
            {
                "topic": item.get("topic"),
                "reason": reason,
                "suggested_actions": ["mini_lesson", "practice_quiz", "guided_task"],
                "confidence": confidence,
            }
        )

    return {
        "path_id": path_id,
        "recommendations": recommendations,
    }
