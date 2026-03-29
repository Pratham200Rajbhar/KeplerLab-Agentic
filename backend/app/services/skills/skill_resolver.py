"""
Skill Resolver — looks up skills by slug with notebook→global fallback.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.db.prisma_client import prisma

logger = logging.getLogger(__name__)


async def resolve_skill(
    slug: str,
    user_id: str,
    notebook_id: Optional[str] = None,
):
    """
    Resolve a skill by slug.

    Priority:
    1. Notebook-scoped skill (if notebook_id provided)
    2. User's global skill (isGlobal=True, notebookId=null)
    3. None

    Returns the Prisma Skill record or None.
    """
    # 1. Try notebook-scoped
    if notebook_id:
        skill = await prisma.skill.find_first(
            where={
                "slug": slug,
                "userId": user_id,
                "notebookId": notebook_id,
            }
        )
        if skill:
            logger.info("Resolved skill '%s' at notebook scope (id=%s)", slug, skill.id)
            return skill

    # 2. Try global (user-owned, no notebook)
    skill = await prisma.skill.find_first(
        where={
            "slug": slug,
            "userId": user_id,
            "isGlobal": True,
        }
    )
    if skill:
        logger.info("Resolved skill '%s' at global scope (id=%s)", slug, skill.id)
        return skill

    # 3. Try global by any user (shared global skills)
    skill = await prisma.skill.find_first(
        where={
            "slug": slug,
            "isGlobal": True,
        }
    )
    if skill:
        logger.info("Resolved skill '%s' from shared global pool (id=%s)", slug, skill.id)
        return skill

    logger.warning("Skill '%s' not found for user=%s notebook=%s", slug, user_id, notebook_id)
    return None


async def resolve_skill_by_id(skill_id: str, user_id: str):
    """Resolve a skill by its ID, verifying user ownership."""
    skill = await prisma.skill.find_first(
        where={
            "id": skill_id,
            "userId": user_id,
        }
    )
    if not skill:
        logger.warning("Skill id=%s not found for user=%s", skill_id, user_id)
    return skill
