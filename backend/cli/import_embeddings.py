from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.chroma import get_collection  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger("cli.import")

_BATCH = 256

def _import(
    src: Path,
    *,
    dry_run: bool = False,
    skip_existing: bool = False,
) -> int:

    with src.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)

    meta = payload.get("meta", {})
    records = payload.get("records", [])

    logger.info(
        "Import file: model=%s  version=%s  records=%d  collection=%s",
        meta.get("embedding_model", "?"),
        meta.get("embedding_version", "?"),
        len(records),
        meta.get("collection_name", "?"),
    )

    if dry_run:
        logger.info("Dry-run — no records will be written.")
        return len(records)

    collection = get_collection()

    existing_ids: set[str] = set()
    if skip_existing:
        all_ids = collection.get(include=[])["ids"]
        existing_ids = set(all_ids)
        logger.info("Collection already has %d records.", len(existing_ids))

    inserted = 0

    for start in range(0, len(records), _BATCH):
        batch = records[start: start + _BATCH]

        ids: list[str] = []
        docs: list[str] = []
        metas: list[dict] = []
        embeddings: list[list[float]] | None = None

        has_embeddings = "embedding" in batch[0] if batch else False
        if has_embeddings:
            embeddings = []

        for rec in batch:
            rid = rec["id"]
            if skip_existing and rid in existing_ids:
                continue
            ids.append(rid)
            docs.append(rec.get("document", ""))
            metas.append(rec.get("metadata", {}))
            if has_embeddings and embeddings is not None:
                embeddings.append(rec["embedding"])

        if not ids:
            continue

        add_kwargs: dict = {
            "ids": ids,
            "documents": docs,
            "metadatas": metas,
        }
        if has_embeddings and embeddings:
            add_kwargs["embeddings"] = embeddings

        if skip_existing:
            collection.add(**add_kwargs)
        else:
            collection.upsert(**add_kwargs)

        inserted += len(ids)
        logger.info("Imported %d / %d records …", inserted, len(records))

    logger.info("Import complete: %d records written.", inserted)
    return inserted

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Import ChromaDB embeddings from a JSON file.",
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Source JSON file path (produced by export_embeddings).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Parse the file and report stats without writing anything.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=False,
        help="Skip records whose IDs already exist in the collection.",
    )
    args = parser.parse_args(argv)

    if not args.input.exists():
        print(f"✘ File not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    count = _import(
        args.input,
        dry_run=args.dry_run,
        skip_existing=args.skip_existing,
    )
    print(f"✔ Imported {count} records from {args.input}")

if __name__ == "__main__":
    main()
