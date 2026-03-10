from __future__ import annotations

import logging
import asyncio
from pathlib import Path
from typing import Dict

from app.core.config import settings
from app.models.model_schemas import REQUIRED_MODELS, ModelConfig, get_local_model_path, is_model_local

logger = logging.getLogger(__name__)

class ModelManager:
    def __init__(self):
        self.models_dir = Path(settings.MODELS_DIR)
        self.models_dir.mkdir(parents=True, exist_ok=True)

        self.required_models: Dict[str, ModelConfig] = REQUIRED_MODELS

    async def validate_and_load_models(self) -> Dict[str, bool]:
        logger.info("Starting model validation …")
        results: Dict[str, bool] = {}
        loop = asyncio.get_running_loop()

        for model_id, cfg in self.required_models.items():
            try:
                ok = await loop.run_in_executor(None, self._ensure_model, cfg.model_dump())
                results[model_id] = ok
                logger.info(f"Model {model_id}: {'ready' if ok else 'FAILED'}")
            except Exception as e:
                logger.error(f"Error with model {model_id}: {e}")
                results[model_id] = False

        ready = sum(results.values())
        logger.info(f"Model validation complete: {ready}/{len(results)} ready")
        return results

    def get_model_info(self) -> dict:
        return {
            "models_directory": str(self.models_dir),
            "required_models": {k: v.model_dump() for k, v in self.required_models.items()},
            "cache_size": self._human_cache_size(),
        }

    def _ensure_model(self, cfg: dict) -> bool:
        name = cfg["name"]
        mtype = cfg["type"]

        if mtype == "sentence_transformer":
            return self._ensure_sentence_transformer(name)
        if mtype == "cross_encoder":
            return self._ensure_cross_encoder(name, cfg.get("fallback_name"))
        if mtype == "tts":
            return True
        logger.error(f"Unknown model type: {mtype}")
        return False

    def _ensure_sentence_transformer(self, name: str) -> bool:
        try:
            from sentence_transformers import SentenceTransformer

            if is_model_local(name):
                load_path = str(get_local_model_path(name))
                logger.info("Loading embedding from local cache: %s", load_path)
            else:
                logger.info("Downloading embedding model: %s", name)
                load_path = name

            model = SentenceTransformer(load_path)

            if not is_model_local(name):
                local = get_local_model_path(name)
                model.save(str(local))
                logger.info("Saved embedding model to %s", local)

            emb = model.encode("test")
            if emb is not None and len(emb) > 0:
                return True
            logger.error("%s: produced invalid embedding", name)
            return False
        except Exception as e:
            logger.error("%s: load/verify failed — %s", name, e)
            return False

    def _ensure_cross_encoder(self, name: str, fallback_name: str | None = None) -> bool:
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model_name = name
        if device == "cpu" and fallback_name and "large" in name:
            model_name = fallback_name
            logger.info("No GPU — using fallback reranker: %s", model_name)

        try:
            from sentence_transformers import CrossEncoder

            if is_model_local(model_name):
                load_path = str(get_local_model_path(model_name))
                logger.info("Loading reranker from local cache: %s", load_path)
            else:
                logger.info("Downloading cross-encoder model: %s", model_name)
                load_path = model_name

            model = CrossEncoder(load_path, max_length=512, trust_remote_code=False)

            if not is_model_local(model_name):
                local = get_local_model_path(model_name)
                model.save(str(local))
                logger.info("Saved reranker model to %s", local)

            scores = model.predict([["test query", "test document"]], show_progress_bar=False)
            if scores is not None and len(scores) > 0:
                return True
            logger.error("%s: produced invalid reranker score", model_name)
            return False
        except Exception as e:
            logger.error("%s: load/verify failed — %s", model_name, e)
            return False

    def _is_model_cached(self, name: str) -> bool:
        return is_model_local(name)

    @staticmethod
    def _human_cache_size(path: Path | None = None) -> str:
        target = path or Path(settings.MODELS_DIR)
        try:
            total = sum(
                f.stat().st_size for f in target.rglob("*") if f.is_file()
            )
        except Exception:
            return "Unknown"
        for unit in ("B", "KB", "MB", "GB"):
            if total < 1024.0:
                return f"{total:.1f} {unit}"
            total /= 1024.0
        return f"{total:.1f} TB"

model_manager = ModelManager()