"""ChromaDB vector store wrapper with tenant-isolated collections."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    """Get or create the ChromaDB client (singleton)."""
    global _client
    if _client is not None:
        return _client

    import chromadb
    from chromadb.config import Settings as ChromaSettings

    chroma_dir = getattr(settings, "CHROMA_DIR", "./data/chroma")
    _client = chromadb.PersistentClient(
        path=chroma_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    logger.info("ChromaDB client initialised at %s", chroma_dir)
    return _client


def _collection_name(notebook_id: str) -> str:
    """Generate a deterministic, tenant-isolated collection name."""
    # ChromaDB collection names: 3-63 chars, alphanumeric + underscore + hyphen
    safe_id = notebook_id.replace("-", "")[:32]
    return f"nb_{safe_id}"


async def upsert_embeddings(
    notebook_id: str,
    ids: List[str],
    embeddings: List[List[float]],
    documents: List[str],
    metadatas: List[Dict[str, Any]],
) -> None:
    """Upsert embeddings into the notebook's ChromaDB collection."""
    await asyncio.to_thread(
        _upsert_sync, notebook_id, ids, embeddings, documents, metadatas
    )


def _upsert_sync(
    notebook_id: str,
    ids: List[str],
    embeddings: List[List[float]],
    documents: List[str],
    metadatas: List[Dict[str, Any]],
) -> None:
    """Synchronous upsert."""
    client = _get_client()
    col_name = _collection_name(notebook_id)
    collection = client.get_or_create_collection(
        name=col_name,
        metadata={"hnsw:space": "cosine"},
    )

    # ChromaDB has batch limits; process in batches of 500
    batch_size = 500
    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i:i + batch_size]
        batch_embeddings = embeddings[i:i + batch_size]
        batch_documents = documents[i:i + batch_size]
        batch_metadatas = metadatas[i:i + batch_size]

        collection.upsert(
            ids=batch_ids,
            embeddings=batch_embeddings,
            documents=batch_documents,
            metadatas=batch_metadatas,
        )

    logger.info("Upserted %d vectors into collection %s", len(ids), col_name)


async def query_similar(
    notebook_id: str,
    query_embedding: List[float],
    n_results: int = 20,
    where: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Query for similar chunks in a notebook's collection."""
    return await asyncio.to_thread(
        _query_sync, notebook_id, query_embedding, n_results, where
    )


def _query_sync(
    notebook_id: str,
    query_embedding: List[float],
    n_results: int,
    where: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Synchronous query."""
    client = _get_client()
    col_name = _collection_name(notebook_id)

    try:
        collection = client.get_collection(name=col_name)
    except Exception:
        logger.warning("Collection %s not found", col_name)
        return []

    kwargs: Dict[str, Any] = {
        "query_embeddings": [query_embedding],
        "n_results": min(n_results, collection.count()),
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where

    if collection.count() == 0:
        return []

    results = collection.query(**kwargs)

    items = []
    for idx in range(len(results["ids"][0])):
        items.append({
            "id": results["ids"][0][idx],
            "document": results["documents"][0][idx] if results["documents"] else "",
            "metadata": results["metadatas"][0][idx] if results["metadatas"] else {},
            "distance": results["distances"][0][idx] if results["distances"] else 0.0,
        })

    return items


async def delete_by_source(notebook_id: str, source_id: str) -> int:
    """Delete all vectors for a specific source from the collection."""
    return await asyncio.to_thread(_delete_source_sync, notebook_id, source_id)


def _delete_source_sync(notebook_id: str, source_id: str) -> int:
    """Synchronous delete."""
    client = _get_client()
    col_name = _collection_name(notebook_id)

    try:
        collection = client.get_collection(name=col_name)
    except Exception:
        return 0

    try:
        collection.delete(where={"source_id": source_id})
    except Exception as e:
        logger.warning("Failed to delete vectors for source %s: %s", source_id, e)
        return 0

    return 1


async def delete_collection(notebook_id: str) -> None:
    """Delete an entire notebook's collection."""
    await asyncio.to_thread(_delete_collection_sync, notebook_id)


def _delete_collection_sync(notebook_id: str) -> None:
    client = _get_client()
    col_name = _collection_name(notebook_id)
    try:
        client.delete_collection(name=col_name)
        logger.info("Deleted collection %s", col_name)
    except Exception:
        pass
