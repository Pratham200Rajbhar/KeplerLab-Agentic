from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from app.db.prisma_client import prisma

logger = logging.getLogger(__name__)


def _as_json_object(value: Any) -> dict | None:
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return None
    return None


async def main() -> None:
    await prisma.connect()
    updated = 0
    skipped = 0

    try:
        materials = await prisma.material.find_many(where={"metadata": {"not": None}})
        for mat in materials:
            parsed = _as_json_object(getattr(mat, "metadata", None))
            if parsed is None:
                skipped += 1
                continue

            if isinstance(getattr(mat, "metadata", None), dict):
                continue

            await prisma.material.update(
                where={"id": mat.id},
                data={"metadata": parsed},
            )
            updated += 1

        logger.info(
            "Material metadata migration complete: updated=%d skipped=%d total=%d",
            updated,
            skipped,
            len(materials),
        )
    finally:
        await prisma.disconnect()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
