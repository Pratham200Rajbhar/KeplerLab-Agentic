from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.db.prisma_client import prisma
from app.services.learning.curriculum_generator import generate_curriculum
from app.services.learning.progress_tracker import ensure_progress, refresh_progress

logger = logging.getLogger(__name__)


def _to_path_dict(path: Any, progress: Optional[Any] = None) -> Dict[str, Any]:
    return {
        "id": str(path.id),
        "title": str(path.title),
        "topic": str(path.topic),
        "duration_days": int(path.durationDays),
        "level": str(path.level),
        "goal_type": str(path.goalType),
        "status": str(path.status),
        "created_at": path.createdAt.isoformat() if path.createdAt else None,
        "updated_at": path.updatedAt.isoformat() if path.updatedAt else None,
        "completion_percentage": float(progress.completionPercentage) if progress else 0.0,
        "current_day": int(progress.currentDay) if progress else 1,
        "streak": int(progress.streak) if progress else 0,
    }


def _to_day_dict(day: Any) -> Dict[str, Any]:
    return {
        "id": str(day.id),
        "day_number": int(day.dayNumber),
        "title": str(day.title),
        "description": str(day.description) if day.description else None,
        "status": str(day.status),
        "is_unlocked": bool(day.isUnlocked),
        "has_generated_content": bool(day.generatedContent),
        "generated_at": day.generatedAt.isoformat() if day.generatedAt else None,
    }


async def create_path(
    user_id: str,
    topic: str,
    duration_days: int,
    level: str,
    goal_type: str,
    title: Optional[str] = None,
) -> Dict[str, Any]:
    cleaned_topic = topic.strip()
    final_title = title.strip() if title else f"{cleaned_topic} ({duration_days} Days)"

    curriculum = generate_curriculum(
        topic=cleaned_topic,
        duration_days=duration_days,
        level=level,
        goal_type=goal_type,
    )

    path = await prisma.learningpath.create(
        data={
            "userId": user_id,
            "title": final_title,
            "topic": cleaned_topic,
            "durationDays": duration_days,
            "level": level,
            "goalType": goal_type,
            "status": "active",
        }
    )

    try:
        await prisma.learningday.create_many(
            data=[
                {
                    "pathId": str(path.id),
                    "dayNumber": int(item["day_number"]),
                    "title": str(item["title"]),
                    "description": str(item["description"]),
                    "status": "pending",
                    "isUnlocked": int(item["day_number"]) == 1,
                }
                for item in curriculum
            ]
        )
        await ensure_progress(user_id, str(path.id))
    except Exception:
        logger.exception("Path creation failed after path row insert; rolling back path %s", path.id)
        await prisma.learningpath.delete(where={"id": str(path.id)})
        raise

    progress = await prisma.learningprogress.find_first(
        where={"userId": user_id, "pathId": str(path.id)}
    )
    return _to_path_dict(path, progress)


async def list_paths(user_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
    where: Dict[str, Any] = {"userId": user_id}
    if status:
        where["status"] = status

    paths = await prisma.learningpath.find_many(
        where=where,
        order={"updatedAt": "desc"},
    )

    if not paths:
        return []

    path_ids = [str(p.id) for p in paths]
    progress_rows = await prisma.learningprogress.find_many(
        where={"userId": user_id, "pathId": {"in": path_ids}}
    )
    progress_map = {str(p.pathId): p for p in progress_rows}

    return [_to_path_dict(p, progress_map.get(str(p.id))) for p in paths]


async def get_path(path_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    path = await prisma.learningpath.find_first(where={"id": path_id, "userId": user_id})
    if not path:
        return None

    progress = await prisma.learningprogress.find_first(
        where={"userId": user_id, "pathId": path_id}
    )
    if not progress:
        await ensure_progress(user_id, path_id)
        progress = await prisma.learningprogress.find_first(
            where={"userId": user_id, "pathId": path_id}
        )

    return _to_path_dict(path, progress)


async def list_days(path_id: str, user_id: str) -> Optional[List[Dict[str, Any]]]:
    path = await prisma.learningpath.find_first(where={"id": path_id, "userId": user_id})
    if not path:
        return None

    days = await prisma.learningday.find_many(
        where={"pathId": path_id},
        order={"dayNumber": "asc"},
    )
    return [_to_day_dict(day) for day in days]


async def get_day_and_path(day_id: str, user_id: str) -> Tuple[Optional[Any], Optional[Any]]:
    day = await prisma.learningday.find_unique(where={"id": day_id})
    if not day:
        return None, None

    path = await prisma.learningpath.find_first(
        where={"id": str(day.pathId), "userId": user_id}
    )
    if not path:
        return None, None

    return day, path


async def get_path_progress(path_id: str, user_id: str) -> Optional[dict]:
    path = await prisma.learningpath.find_first(where={"id": path_id, "userId": user_id})
    if not path:
        return None
    return await refresh_progress(user_id, path_id, touch_last_active=False)
