from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import List, Optional

from app.core.config import settings
from app.db.chroma import get_collection, reset_singletons

logger = logging.getLogger(__name__)

_BATCH_SIZE  = 200
_MAX_RETRIES = 3

def warm_up_embeddings() -> None:
    try:
        from app.db.chroma import _get_ef
        col = get_collection()
        count = col.count()
        _get_ef()(["warm-up"])
        logger.info("Embedding model warm-up complete (%d existing chunks).", count)
    except Exception as exc:
        logger.warning("Embedding warm-up failed (non-fatal): %s", exc)

def _invalidate_version_marker() -> None:
    try:
        p = Path(settings.CHROMA_DIR) / ".embedding_version"
        if p.exists():
            p.unlink()
            logger.info("Version marker deleted — next restart will rebuild collection.")
    except Exception as exc:
        logger.warning("Could not delete version marker: %s", exc)

def embed_and_store(
    chunks: List[dict],
    material_id: Optional[str] = None,
    user_id: str = "",
    notebook_id: Optional[str] = None,
    filename: Optional[str] = None,
) -> None:
    if not chunks:
        return

    if not user_id:
        logger.error(
            "embed_and_store called without user_id — skipping to prevent "
            "tenant isolation breach  material=%s", material_id,
        )
        return

    collection = get_collection()

    base_meta: dict = {
        "source": "chapter",
        "embedding_version": settings.EMBEDDING_VERSION,
        "user_id": user_id,
    }
    if material_id:
        base_meta["material_id"] = material_id
    if notebook_id:
        base_meta["notebook_id"] = notebook_id
    if filename:
        base_meta["filename"] = filename[:200]

    stored = 0
    failed_batches = 0

    for start in range(0, len(chunks), _BATCH_SIZE):
        batch  = chunks[start : start + _BATCH_SIZE]
        ids    = [c["id"]   for c in batch]
        docs   = [c["text"] for c in batch]
        metas  = [base_meta.copy() for _ in batch]

        for i, chunk in enumerate(batch):
            if "section_title" in chunk:
                metas[i]["section_title"] = str(chunk["section_title"])[:200]
            if "chunk_index" in chunk:
                metas[i]["chunk_index"] = str(chunk["chunk_index"])
            if chunk.get("chunk_type") == "structured_summary":
                metas[i]["is_structured"] = "true"
            if chunk.get("_raw_file_path"):
                metas[i]["raw_file_path"] = str(chunk["_raw_file_path"])[:500]

        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                collection.upsert(ids=ids, documents=docs, metadatas=metas)
                stored += len(batch)
                break
            except Exception as exc:
                last_exc = exc
                if "dimension" in str(exc).lower() or "dimensionality" in str(exc).lower():
                    logger.error(
                        "Dimension mismatch during upsert  material=%s  start=%d: %s\n"
                        "Invalidating version marker and resetting singletons. "
                        "Restart the server — the collection will be auto-rebuilt.",
                        material_id, start, exc,
                    )
                    _invalidate_version_marker()
                    reset_singletons()
                    raise RuntimeError(
                        f"Embedding dimension mismatch for material {material_id}. "
                        "Restart the server — auto-rebuild will kick in on startup."
                    ) from exc
                wait = 0.5 * attempt
                logger.warning(
                    "Upsert attempt %d/%d failed  start=%d  material=%s: %s — retry in %.1fs",
                    attempt, _MAX_RETRIES, start, material_id, exc, wait,
                )
                threading.Event().wait(timeout=wait)
        else:
            failed_batches += 1
            logger.error(
                "Batch permanently failed  start=%d  size=%d  material=%s: %s",
                start, len(batch), material_id, last_exc,
            )

    if failed_batches:
        logger.error(
            "embed_and_store: %d batch(es) failed — %d/%d chunks stored  material=%s",
            failed_batches, stored, len(chunks), material_id,
        )
        if stored == 0:
            raise RuntimeError(
                f"All embedding batches failed for material {material_id}: {last_exc}"
            )
    else:
        logger.info(
            "Stored %d/%d chunks  material=%s  user=%s",
            stored, len(chunks), material_id, user_id,
        )

def delete_material_embeddings(material_id: str, user_id: str) -> int:
    try:
        collection = get_collection()
        results = collection.get(
            where={"$and": [{"material_id": material_id}, {"user_id": user_id}]},
            include=[],
        )
        ids_to_delete = results.get("ids", [])
        if ids_to_delete:
            collection.delete(ids=ids_to_delete)
            logger.info(
                "Deleted %d chunks  material=%s  user=%s",
                len(ids_to_delete), material_id, user_id,
            )
        return len(ids_to_delete)
    except Exception as exc:
        logger.error("Failed to delete embeddings for material %s: %s", material_id, exc)
        raise RuntimeError(f"Embedding deletion failed for material {material_id}") from exc
