from __future__ import annotations

import logging
import os
import shutil
import threading
from pathlib import Path

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

os.environ["SENTENCE_TRANSFORMERS_HOME"] = str(
    Path(settings.CHROMA_DIR).parent / "models"
)

logger = logging.getLogger(__name__)

_client: chromadb.PersistentClient | None = None
_collection: chromadb.Collection | None = None
_ef: SentenceTransformerEmbeddingFunction | None = None

_lock = threading.RLock()

_EF_MODEL        = settings.EMBEDDING_MODEL
_EF_DIM          = settings.EMBEDDING_DIMENSION
_COLLECTION_NAME = "chapters"
_VERSION_MARKER  = ".embedding_version"
_PROBE_DOC_ID    = "__dim_probe__"

def _get_ef() -> SentenceTransformerEmbeddingFunction:
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

def _wipe_chroma_dir() -> None:
    chroma_dir = Path(settings.CHROMA_DIR)
    if chroma_dir.exists():
        shutil.rmtree(chroma_dir)
        logger.warning("ChromaDB data directory wiped: %s", chroma_dir)
    chroma_dir.mkdir(parents=True, exist_ok=True)

    global _client, _collection
    _client = None
    _collection = None

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
    try:
        p = Path(settings.CHROMA_DIR) / _VERSION_MARKER
        return p.read_text().strip() if p.exists() else None
    except Exception as exc:
        logger.warning("Could not read version marker: %s", exc)
        return None

def _write_version_marker() -> None:
    try:
        p = Path(settings.CHROMA_DIR) / _VERSION_MARKER
        p.write_text(settings.EMBEDDING_VERSION)
        logger.info("Version marker written: %s = '%s'", p, settings.EMBEDDING_VERSION)
    except Exception as exc:
        logger.warning("Could not write version marker: %s", exc)

def _probe_dimension(collection: chromadb.Collection) -> bool:
    ef = _get_ef()
    try:
        vec = [float(x) for x in ef([_PROBE_DOC_ID])[0]]
        collection.upsert(
            ids=[_PROBE_DOC_ID],
            embeddings=[vec],
            documents=[_PROBE_DOC_ID],
            metadatas=[{"probe": "true"}],
        )
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
    if attempt > 2:
        raise RuntimeError(
            f"ChromaDB '{_COLLECTION_NAME}' cannot be verified as {_EF_DIM}-dim "
            f"after two full rebuild attempts. "
            f"Check EMBEDDING_MODEL='{_EF_MODEL}' and EMBEDDING_DIMENSION={_EF_DIM} "
            "in your .env file."
        )

    current_version = settings.EMBEDDING_VERSION

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

    Path(settings.CHROMA_DIR).mkdir(parents=True, exist_ok=True)

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
            break
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
                raise

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

    if not _probe_dimension(collection):
        _wipe_chroma_dir()
        return _bootstrap_collection(attempt=attempt + 1)

    _write_version_marker()

    return client, collection

def get_collection() -> chromadb.Collection:
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
    global _client
    if _client is None:
        get_collection()
    return _client  # type: ignore[return-value]

def reset_singletons() -> None:
    global _client, _collection
    with _lock:
        _client = None
        _collection = None
    logger.info("ChromaDB singletons reset — will re-bootstrap on next access.")

reset_client = reset_singletons


