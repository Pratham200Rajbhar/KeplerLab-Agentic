from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings                # noqa: E402
from app.db.chroma import get_collection            # noqa: E402
from app.db.prisma_client import prisma              # noqa: E402
from app.services.rag.embedder import embed_and_store  # noqa: E402
from app.services.text_processing.chunker import chunk_text  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger("cli.reindex")

_GET_BATCH = 5000

def _delete_material_chunks(collection, material_id: str) -> int:
    deleted = 0
    while True:
        result = collection.get(
            where={"material_id": material_id},
            include=[],
            limit=_GET_BATCH,
        )
        ids = result.get("ids", [])
        if not ids:
            break
        collection.delete(ids=ids)
        deleted += len(ids)
    return deleted

async def _reindex(
    *,
    user_id: str | None = None,
    material_id: str | None = None,
    dry_run: bool = False,
    include_failed: bool = False,
) -> dict:

    await prisma.connect()

    try:
        statuses = ["completed"]
        if include_failed:
            statuses.append("failed")

        where: dict = {"status": {"in": statuses}}
        if user_id:
            where["userId"] = user_id
        if material_id:
            where["id"] = material_id

        materials = await prisma.material.find_many(where=where)
        logger.info(
            "Found %d material(s) to reindex (statuses: %s).",
            len(materials), ", ".join(statuses),
        )

        if dry_run:
            for m in materials:
                text_len = len(m.originalText) if m.originalText else 0
                logger.info(
                    "  [DRY-RUN] material=%s  user=%s  text=%d chars",
                    m.id, m.userId, text_len,
                )
            return {"total": len(materials), "reindexed": 0, "skipped": 0, "failed": 0}

        collection = get_collection()
        stats = {"total": len(materials), "reindexed": 0, "skipped": 0, "failed": 0}

        for idx, mat in enumerate(materials, 1):
            mid = mat.id
            uid = mat.userId
            nid = mat.notebookId

            if not mat.originalText or len(mat.originalText.strip()) < 10:
                logger.warning(
                    "[%d/%d] Skipping material=%s — no/short originalText.",
                    idx, stats["total"], mid,
                )
                stats["skipped"] += 1
                continue

            try:
                deleted = _delete_material_chunks(collection, mid)
                logger.info(
                    "[%d/%d] Deleted %d old chunks for material=%s",
                    idx, stats["total"], deleted, mid,
                )

                chunks = chunk_text(mat.originalText)

                embed_and_store(
                    chunks,
                    material_id=mid,
                    user_id=uid,
                    notebook_id=nid,
                )

                await prisma.material.update(
                    where={"id": mid},
                    data={"chunkCount": len(chunks), "status": "completed"},
                )

                logger.info(
                    "[%d/%d] Reindexed material=%s  user=%s  chunks=%d  emb_version=%s",
                    idx, stats["total"], mid, uid, len(chunks), settings.EMBEDDING_VERSION,
                )
                stats["reindexed"] += 1

            except Exception:
                logger.exception(
                    "[%d/%d] FAILED to reindex material=%s", idx, stats["total"], mid
                )
                stats["failed"] += 1

        return stats

    finally:
        await prisma.disconnect()

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Re-embed all materials (safe, tenant-isolated reindex).",
    )
    parser.add_argument(
        "--user-id",
        default=None,
        help="Restrict to materials owned by this user UUID.",
    )
    parser.add_argument(
        "--material-id",
        default=None,
        help="Reindex a single material by UUID.",
    )
    parser.add_argument(
        "--include-failed",
        action="store_true",
        default=False,
        help="Also reindex materials whose status is 'failed' (e.g. after fixing an embedding mismatch).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="List materials that would be reindexed without writing.",
    )
    args = parser.parse_args(argv)

    stats = asyncio.run(
        _reindex(
            user_id=args.user_id,
            material_id=args.material_id,
            dry_run=args.dry_run,
            include_failed=args.include_failed,
        )
    )

    print(
        f"\n✔ Reindex complete — "
        f"total={stats['total']}  "
        f"reindexed={stats['reindexed']}  "
        f"skipped={stats['skipped']}  "
        f"failed={stats['failed']}"
    )

if __name__ == "__main__":
    main()
