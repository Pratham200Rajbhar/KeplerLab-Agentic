from __future__ import annotations

import asyncio
import logging

from app.db.prisma_client import prisma

logger = logging.getLogger(__name__)

async def _migrate_generated_content() -> int:
    rows = await prisma.generatedcontent.find_many(
        where={"materialIds": {"isEmpty": False}},
    )
    count = 0
    for gc in rows:
        for mid in gc.materialIds:
            try:
                await prisma.generatedcontentmaterial.create(
                    data={
                        "generatedContentId": gc.id,
                        "materialId": mid,
                    },
                )
                count += 1
            except Exception:
                pass
    return count

async def _migrate_podcast_sessions() -> int:
    rows = await prisma.podcastsession.find_many(
        where={"materialIds": {"isEmpty": False}},
    )
    count = 0
    for ps in rows:
        for mid in ps.materialIds:
            try:
                await prisma.podcastsessionmaterial.create(
                    data={
                        "podcastSessionId": ps.id,
                        "materialId": mid,
                    },
                )
                count += 1
            except Exception:
                pass
    return count

async def main() -> None:
    await prisma.connect()
    try:
        gc_count = await _migrate_generated_content()
        logger.info("Migrated %d GeneratedContentMaterial join rows", gc_count)

        ps_count = await _migrate_podcast_sessions()
        logger.info("Migrated %d PodcastSessionMaterial join rows", ps_count)

        logger.info("Done. Total join rows created: %d", gc_count + ps_count)
    finally:
        await prisma.disconnect()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
