"""ChromaDB client and collection management — thread-safe singleton pattern."""

from __future__ import annotations

import os
import logging
import threading

# ── Disable ALL Chroma / posthog telemetry before importing chromadb ──────────
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

logging.getLogger("chromadb").setLevel(logging.ERROR)
logging.getLogger("posthog").setLevel(logging.CRITICAL)

try:
    import posthog  # type: ignore
    posthog.capture = lambda *args, **kwargs: None  # type: ignore[attr-defined]
    posthog.disabled = True
    posthog.Posthog.disabled = True  # type: ignore[attr-defined]
except Exception:
    pass

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from app.core.config import settings
from app.models.model_schemas import get_local_model_path

# Point sentence-transformers cache to our managed models directory so that
# models downloaded by download_models.py are reused here too.
os.environ["SENTENCE_TRANSFORMERS_HOME"] = str(
    os.path.join(os.path.dirname(settings.CHROMA_DIR), "models")
)

logger = logging.getLogger(__name__)

_client: chromadb.PersistentClient | None = None
_collection: chromadb.Collection | None = None
_ef: SentenceTransformerEmbeddingFunction | None = None
_lock = threading.RLock()  # RLock: get_collection() → get_client() re-enters the lock


def _purge_stale_segments() -> None:
    """Remove HNSW segment folders whose index_metadata.pickle was written by
    an incompatible older chromadb version.

    Symptom: pickle.load() returns a plain dict instead of PersistentData,
    so accessing .dimensionality raises AttributeError.  This happens after
    upgrading chromadb (e.g. 0.5.5 → 0.5.20) when the old pickle is still
    on disk.

    Only the binary HNSW files are removed — the SQLite catalog is left intact
    so chromadb can recreate the segment cleanly on next startup.
    """
    import pickle
    import shutil
    from pathlib import Path

    chroma_dir = Path(settings.CHROMA_DIR)
    if not chroma_dir.is_dir():
        return

    for pickle_file in chroma_dir.rglob("index_metadata.pickle"):
        try:
            data = pickle.load(open(pickle_file, "rb"))
            if not hasattr(data, "dimensionality"):
                segment_dir = pickle_file.parent
                logger.warning(
                    "Stale HNSW segment detected (chromadb version mismatch) — "
                    "removing %s and letting chromadb recreate it.",
                    segment_dir,
                )
                shutil.rmtree(segment_dir)
        except Exception as exc:
            logger.warning("Could not inspect %s: %s — leaving as-is", pickle_file, exc)


_CHROMA_EF_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _get_ef() -> SentenceTransformerEmbeddingFunction:
    """Lazily create a singleton SentenceTransformer EF (CPU, avoids VRAM contention).

    Prefers the locally saved copy in data/models/ (pre-seeded by
    ``python -m cli.download_models``) over downloading from HuggingFace hub.

    Path resolution priority:
    1. Direct save path:  data/models/sentence-transformers--all-MiniLM-L6-v2/
       (created by ``model.save()`` in download_models.py)
    2. HuggingFace hub name — sentence-transformers uses SENTENCE_TRANSFORMERS_HOME
       to cache at data/models/models--sentence-transformers--all-MiniLM-L6-v2/
    """
    global _ef
    if _ef is None:
        direct = get_local_model_path(_CHROMA_EF_MODEL)
        if direct.is_dir() and any(direct.iterdir()):
            # Use explicit local directory — fully offline
            model_path = str(direct)
            source = "local"
        else:
            # Fall through to HuggingFace (SENTENCE_TRANSFORMERS_HOME cache applies)
            model_path = _CHROMA_EF_MODEL
            source = "HuggingFace hub"
        logger.info("ChromaDB EF: loading %s (source: %s)", _CHROMA_EF_MODEL, source)
        _ef = SentenceTransformerEmbeddingFunction(
            model_name=model_path,
            device="cpu",  # Keep separate from GPU-resident reranker
        )
    return _ef


def get_client() -> chromadb.PersistentClient:
    """Thread-safe lazily initialised singleton ChromaDB client.

    Calls _purge_stale_segments() once before the first initialisation to
    remove any HNSW pickle files that are incompatible with the current
    chromadb version (avoids 'dict has no attribute dimensionality' crashes).
    """
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                _purge_stale_segments()
                try:
                    _client = chromadb.PersistentClient(
                        path=settings.CHROMA_DIR,
                        settings=ChromaSettings(anonymized_telemetry=False),
                    )
                    logger.info("ChromaDB client initialised at %s", settings.CHROMA_DIR)
                except Exception:
                    logger.exception("Failed to initialise ChromaDB client")
                    raise
    return _client


def get_collection() -> chromadb.Collection:
    """Thread-safe singleton shared collection."""
    global _collection
    if _collection is None:
        with _lock:
            if _collection is None:
                try:
                    _collection = get_client().get_or_create_collection(
                        name="chapters",
                        embedding_function=_get_ef(),
                        metadata={"hnsw:space": "cosine"},
                    )
                    logger.info("ChromaDB collection 'chapters' ready")
                except Exception:
                    logger.exception("Failed to get/create ChromaDB collection")
                    raise
    return _collection


def reset_client() -> None:
    """Reset singletons — useful for reconnecting after ChromaDB failures."""
    global _client, _collection
    with _lock:
        _client = None
        _collection = None
        logger.info("ChromaDB client and collection reset")


def backup_chroma(backup_dir: str | None = None) -> str:
    """Create a backup of the ChromaDB data directory.

    Copies the entire CHROMA_DIR to a timestamped subdirectory.
    Returns the path to the backup directory.

    Args:
        backup_dir: Parent directory for backups. Defaults to
                    ``{CHROMA_DIR}/../chroma_backups/``.

    Returns:
        Absolute path of the created backup.
    """
    import shutil
    from datetime import datetime

    source = settings.CHROMA_DIR
    if backup_dir is None:
        backup_dir = os.path.join(os.path.dirname(source), "chroma_backups")

    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(backup_dir, f"chroma_backup_{timestamp}")

    shutil.copytree(source, dest)
    logger.info("ChromaDB backup created: %s", dest)
    return dest


def get_collection_stats() -> dict:
    """Return basic statistics about the ChromaDB collection.

    Returns:
        Dict with count, name, and metadata.
    """
    try:
        collection = get_collection()
        count = collection.count()
        return {
            "name": collection.name,
            "count": count,
            "chroma_dir": settings.CHROMA_DIR,
        }
    except Exception as e:
        logger.error("Failed to get ChromaDB stats: %s", e)
        return {"error": str(e)}
