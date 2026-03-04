"""ChromaDB client and collection management — thread-safe singleton pattern.

Design
------
Single embedding model throughout: BAAI/bge-m3 (1024-dim).
Used for both upsert (ingest) and query (retrieval) — consistent vector space.

Startup sequence (get_collection)
----------------------------------
1. Create PersistentClient.
2. Version-marker check: compare <CHROMA_DIR>/.embedding_version against
   settings.EMBEDDING_VERSION.  If mismatch or file absent → physically wipe
   CHROMA_DIR so no stale HNSW segment or SQLite catalog survives.
3. get_or_create_collection with the bge-m3 EF.
4. Dimension probe: embed a real string with our EF and do a real upsert.
   Only if this succeeds do we write the version marker.
   If probe fails (wrong-dim HNSW somehow survived) → wipe CHROMA_DIR and
   retry once.  If it fails twice → RuntimeError (fundamental misconfiguration).
5. Delete the probe document.  Collection is ready.

This design guarantees the version marker is written ONLY after a confirmed
correct-dimension upsert, eliminating the race condition where the marker was
written before the physical data was fully cleaned up.
"""

from __future__ import annotations

import logging
import os
import shutil
import threading
from pathlib import Path

# ── Silence all Chroma / posthog telemetry before importing chromadb ─────────
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"
logging.getLogger("chromadb").setLevel(logging.ERROR)
logging.getLogger("posthog").setLevel(logging.CRITICAL)

try:
    import posthog  # type: ignore
    posthog.capture = lambda *a, **kw: None  # type: ignore[attr-defined]
    posthog.disabled = True
    posthog.Posthog.disabled = True  # type: ignore[attr-defined]
except Exception:
    pass

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from app.core.config import settings
from app.models.model_schemas import get_local_model_path

# Use the managed models directory for sentence-transformers cache.
os.environ["SENTENCE_TRANSFORMERS_HOME"] = str(
    Path(settings.CHROMA_DIR).parent / "models"
)

logger = logging.getLogger(__name__)

# ── Module-level singletons ───────────────────────────────────────────────────
_client: chromadb.PersistentClient | None = None
_collection: chromadb.Collection | None = None
_ef: SentenceTransformerEmbeddingFunction | None = None

# RLock: get_client() is called inside get_collection() — both hold the lock.
_lock = threading.RLock()

# Constants
_EF_MODEL        = settings.EMBEDDING_MODEL       # "BAAI/bge-m3"
_EF_DIM          = settings.EMBEDDING_DIMENSION   # 1024
_COLLECTION_NAME = "chapters"
_VERSION_MARKER  = ".embedding_version"            # sidecar file in CHROMA_DIR
_PROBE_DOC_ID    = "__dim_probe__"                 # ephemeral document ID


# ─────────────────────────────────────────────────────────────────────────────
# Embedding function
# ─────────────────────────────────────────────────────────────────────────────

def _get_ef() -> SentenceTransformerEmbeddingFunction:
    """Return (or lazily create) the singleton SentenceTransformer EF.

    Runs on CPU to avoid VRAM contention with the GPU-resident reranker.
    Prefers the locally downloaded model in data/models/.
    """
    global _ef
    if _ef is None:
        local_path = get_local_model_path(_EF_MODEL)
        if local_path.is_dir() and any(local_path.iterdir()):
            model_path = str(local_path)
            source = "local"
        else:
            model_path = _EF_MODEL
            source = "HuggingFace hub"
        logger.info("ChromaDB EF: loading %s (source: %s)", _EF_MODEL, source)
        _ef = SentenceTransformerEmbeddingFunction(
            model_name=model_path,
            device="cpu",
        )
    return _ef


# ─────────────────────────────────────────────────────────────────────────────
# Data-directory helpers
# ─────────────────────────────────────────────────────────────────────────────

def _wipe_chroma_dir() -> None:
    """Physically delete and recreate the ChromaDB data directory.

    Guarantees no old HNSW segments or stale SQLite catalog survive.
    Called both on version mismatch and on dimension-probe failure.

    IMPORTANT: Also clears the ChromaDB SharedSystemClient singleton cache.
    Without this, ChromaDB reuses the stale System whose SQLite connection
    points to the deleted file, causing "no such table: tenants" on the very
    next PersistentClient() call.
    """
    chroma_dir = Path(settings.CHROMA_DIR)
    if chroma_dir.exists():
        shutil.rmtree(chroma_dir)
        logger.warning("ChromaDB data directory wiped: %s", chroma_dir)
    chroma_dir.mkdir(parents=True, exist_ok=True)

    # Also reset the module-level singletons so the NEXT get_collection() call
    # triggers a fresh _bootstrap_collection() instead of returning the stale
    # references that were valid before the wipe.
    global _client, _collection
    _client = None
    _collection = None

    # Clear the ChromaDB client-system singleton so the next PersistentClient()
    # call creates a brand-new System (and proper SQLite schema) from scratch.
    try:
        from chromadb.api.shared_system_client import (
            SharedSystemClient as _ChromaSSC,
        )
        removed = _ChromaSSC._identifier_to_system.pop(settings.CHROMA_DIR, None)
        if removed is not None:
            logger.debug(
                "ChromaDB system-cache entry cleared for '%s'", settings.CHROMA_DIR
            )
    except Exception as _cache_exc:
        logger.warning(
            "Could not clear ChromaDB system cache (non-fatal): %s", _cache_exc
        )


def _read_version_marker() -> str | None:
    """Return stored embedding version string, or None if absent/unreadable."""
    try:
        p = Path(settings.CHROMA_DIR) / _VERSION_MARKER
        return p.read_text().strip() if p.exists() else None
    except Exception as exc:
        logger.warning("Could not read version marker: %s", exc)
        return None


def _write_version_marker() -> None:
    """Write settings.EMBEDDING_VERSION to the sidecar file.

    Called ONLY after a successful dimension probe — never speculatively.
    """
    try:
        p = Path(settings.CHROMA_DIR) / _VERSION_MARKER
        p.write_text(settings.EMBEDDING_VERSION)
        logger.info("Version marker written: %s = '%s'", p, settings.EMBEDDING_VERSION)
    except Exception as exc:
        logger.warning("Could not write version marker: %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# Collection bootstrap
# ─────────────────────────────────────────────────────────────────────────────

def _probe_dimension(collection: chromadb.Collection) -> bool:
    """Verify the collection accepts our %d-dim vectors via a real upsert+delete.

    Returns True on success.  Returns False if a dimension error is raised so
    the caller can wipe and retry.  Any other exception is re-raised.
    """
    ef = _get_ef()
    try:
        vec = [float(x) for x in ef([_PROBE_DOC_ID])[0]]
        collection.upsert(
            ids=[_PROBE_DOC_ID],
            embeddings=[vec],
            documents=[_PROBE_DOC_ID],
            metadatas=[{"probe": "true"}],
        )
        # Clean up immediately.
        try:
            collection.delete(ids=[_PROBE_DOC_ID])
        except Exception:
            pass
        logger.debug("Dimension probe passed (%d-dim OK).", len(vec))
        return True
    except Exception as exc:
        if "dimension" in str(exc).lower() or "dimensionality" in str(exc).lower():
            logger.error(
                "Dimension probe FAILED — collection has wrong dimensionality. "
                "Expected %d-dim (%s). Raw error: %s",
                _EF_DIM, _EF_MODEL, exc,
            )
            return False
        raise


def _bootstrap_collection(
    attempt: int = 1,
) -> tuple[chromadb.PersistentClient, chromadb.Collection]:
    """Build a fully verified client+collection pair.

    Attempt 1 — normal path:
      a. Version-marker check.  Mismatch/absent → wipe CHROMA_DIR.
      b. Create client + get_or_create_collection.
      c. Dimension probe.
         Pass  → write marker, return.
         Fail  → wipe + recurse(attempt=2).

    Attempt 2 — recovery:
      Skip version check (we know data is bad), always wipe, rebuild.
      If probe fails again → raise RuntimeError.
    """
    if attempt > 2:
        raise RuntimeError(
            f"ChromaDB '{_COLLECTION_NAME}' cannot be verified as {_EF_DIM}-dim "
            f"after two full rebuild attempts. "
            f"Check EMBEDDING_MODEL='{_EF_MODEL}' and EMBEDDING_DIMENSION={_EF_DIM} "
            "in your .env file."
        )

    current_version = settings.EMBEDDING_VERSION

    # -- Step 1: version-marker check (attempt 1 only) --------
    if attempt == 1:
        stored = _read_version_marker()
        if stored != current_version:
            msg = (
                f"No version marker — wiping data dir to ensure {_EF_DIM}-dim collection."
                if stored is None
                else (
                    f"Embedding version changed '{stored}' → '{current_version}' "
                    f"(model={_EF_MODEL}, dim={_EF_DIM}). Wiping data dir. "
                    "Re-index via: python -m cli.reindex --include-failed"
                )
            )
            logger.warning(msg)
            _wipe_chroma_dir()
        else:
            logger.debug("Version marker matches '%s' — proceeding.", current_version)
    else:
        logger.warning("Recovery attempt %d: wiping ChromaDB data and rebuilding.", attempt)
        _wipe_chroma_dir()

    # -- Step 2: create client + collection -------------------
    Path(settings.CHROMA_DIR).mkdir(parents=True, exist_ok=True)

    # ChromaDB 0.5.x has a known race-condition where PersistentClient's
    # _validate_tenant_database() fires before the internal SQLite schema
    # (including the `tenants` table) is written.  Retry a few times with a
    # brief sleep to let the background initialisation complete.
    import time as _time
    _MAX_CHROMA_INIT_RETRIES = 5
    _client_exc: Exception | None = None
    client: chromadb.PersistentClient | None = None
    for _retry in range(_MAX_CHROMA_INIT_RETRIES):
        try:
            client = chromadb.PersistentClient(
                path=settings.CHROMA_DIR,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            _client_exc = None
            break  # success
        except (ValueError, Exception) as _exc:
            _client_exc = _exc
            _hint = str(_exc).lower()
            if "tenant" in _hint or "no such table" in _hint or "default_tenant" in _hint:
                logger.warning(
                    "ChromaDB init attempt %d/%d failed ('%s') — "
                    "wiping & retrying in 0.5 s …",
                    _retry + 1, _MAX_CHROMA_INIT_RETRIES, _exc,
                )
                _wipe_chroma_dir()
                _time.sleep(0.5)
            else:
                raise  # non-retryable error

    if client is None:
        raise RuntimeError(
            f"ChromaDB PersistentClient failed to initialise after "
            f"{_MAX_CHROMA_INIT_RETRIES} attempts: {_client_exc}"
        )

    logger.info("ChromaDB client initialised at %s", settings.CHROMA_DIR)

    collection = client.get_or_create_collection(
        name=_COLLECTION_NAME,
        embedding_function=_get_ef(),
        metadata={"hnsw:space": "cosine"},
    )
    logger.info("ChromaDB collection '%s' obtained.", _COLLECTION_NAME)

    # -- Step 3: dimension probe (the only source of truth) ---
    if not _probe_dimension(collection):
        # Stale HNSW survived despite the wipe — nuke and retry.
        _wipe_chroma_dir()
        return _bootstrap_collection(attempt=attempt + 1)

    # -- Step 4: write marker ONLY after confirmed success ----
    _write_version_marker()

    return client, collection


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def get_collection() -> chromadb.Collection:
    """Return the singleton verified collection, bootstrapping on first call."""
    global _client, _collection
    if _collection is None:
        with _lock:
            if _collection is None:
                try:
                    _client, _collection = _bootstrap_collection()
                    logger.info(
                        "ChromaDB collection '%s' ready (%d existing chunks).",
                        _COLLECTION_NAME, _collection.count(),
                    )
                except Exception:
                    logger.exception("Failed to bootstrap ChromaDB collection")
                    raise
    return _collection


def get_client() -> chromadb.PersistentClient:
    """Return the singleton client, bootstrapping via get_collection if needed."""
    global _client
    if _client is None:
        get_collection()  # bootstraps both _client and _collection
    return _client  # type: ignore[return-value]


def reset_singletons() -> None:
    """Reset singletons, forcing a full re-bootstrap on next access.

    Call this after a ChromaDB mid-request failure to force reconnection.
    Aliased as reset_client() for backwards compatibility.
    """
    global _client, _collection
    with _lock:
        _client = None
        _collection = None
    logger.info("ChromaDB singletons reset — will re-bootstrap on next access.")


# Backwards-compat alias used by some existing callers.
reset_client = reset_singletons


def get_collection_stats() -> dict:
    """Return basic statistics about the ChromaDB collection."""
    try:
        col = get_collection()
        return {
            "name": col.name,
            "count": col.count(),
            "chroma_dir": settings.CHROMA_DIR,
            "embedding_model": _EF_MODEL,
            "embedding_dim": _EF_DIM,
            "embedding_version": settings.EMBEDDING_VERSION,
        }
    except Exception as exc:
        logger.error("Failed to get ChromaDB stats: %s", exc)
        return {"error": str(exc)}


def backup_chroma(backup_dir: str | None = None) -> str:
    """Copy CHROMA_DIR to a timestamped backup directory; return the path."""
    from datetime import datetime
    source = settings.CHROMA_DIR
    parent = str(Path(source).parent / "chroma_backups") if backup_dir is None else backup_dir
    os.makedirs(parent, exist_ok=True)
    dest = os.path.join(parent, f"chroma_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    shutil.copytree(source, dest)
    logger.info("ChromaDB backup created: %s", dest)
    return dest
