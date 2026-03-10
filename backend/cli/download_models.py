from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings                                   # noqa: E402
from app.models.model_schemas import (                                 # noqa: E402
    REQUIRED_MODELS,
    ModelConfig,
    get_local_model_path,
    is_model_local,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("cli.download_models")

def _resolve_model_name(cfg: ModelConfig) -> str:
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu" and cfg.fallback_name and "large" in cfg.name:
        logger.info("No GPU detected — will download fallback model %s", cfg.fallback_name)
        return cfg.fallback_name
    return cfg.name

def _download_sentence_transformer(model_name: str) -> Path:
    from sentence_transformers import SentenceTransformer

    local = get_local_model_path(model_name)
    if is_model_local(model_name):
        logger.info("[skip] %s  →  %s (already downloaded)", model_name, local)
        return local

    logger.info("Downloading sentence-transformer: %s", model_name)
    t0 = time.time()
    model = SentenceTransformer(model_name)
    model.save(str(local))
    logger.info("Saved to %s  (%.1fs)", local, time.time() - t0)
    return local

def _download_cross_encoder(model_name: str) -> Path:
    from sentence_transformers import CrossEncoder

    local = get_local_model_path(model_name)
    if is_model_local(model_name):
        logger.info("[skip] %s  →  %s (already downloaded)", model_name, local)
        return local

    logger.info("Downloading cross-encoder: %s", model_name)
    t0 = time.time()
    model = CrossEncoder(model_name, max_length=512, trust_remote_code=False)
    model.save(str(local))
    logger.info("Saved to %s  (%.1fs)", local, time.time() - t0)
    return local

def download_model(key: str, cfg: ModelConfig) -> bool:
    effective_name = _resolve_model_name(cfg)
    logger.info("─── [%s] %s (%s)", key, effective_name, cfg.type)

    try:
        if cfg.type == "sentence_transformer":
            _download_sentence_transformer(effective_name)
        elif cfg.type == "cross_encoder":
            _download_cross_encoder(effective_name)
        elif cfg.type == "tts":
            logger.info("[skip] TTS models are bundled with edge-tts (no download needed)")
        elif cfg.type == "whisper":
            logger.warning(
                "[skip] Whisper models are downloaded automatically on first transcription use"
            )
        else:
            logger.warning("Unknown model type %r — skipping", cfg.type)
            return False
        return True
    except Exception as exc:
        logger.error("Failed to download %s: %s", effective_name, exc)
        return False

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download AI models listed in the model registry to data/models/",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print registered models and exit without downloading",
    )
    parser.add_argument(
        "--id",
        metavar="KEY",
        help="Only download the model with this registry key (e.g. embedding, reranker)",
    )
    args = parser.parse_args()

    models_dir = Path(settings.MODELS_DIR)
    models_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Models directory: %s", models_dir.resolve())

    if args.list:
        print(f"\n{'KEY':<16} {'TYPE':<22} {'MODEL NAME':<45} {'LOCAL?'}")
        print("─" * 100)
        for key, cfg in REQUIRED_MODELS.items():
            effective = _resolve_model_name(cfg)
            local_ok = is_model_local(effective)
            status = "✓" if local_ok else "✗"
            req = " [required]" if cfg.required else ""
            print(f"{key:<16} {cfg.type:<22} {effective:<45} {status}{req}")
        print()
        return 0

    targets: dict[str, ModelConfig]
    if args.id:
        if args.id not in REQUIRED_MODELS:
            valid = ", ".join(REQUIRED_MODELS)
            logger.error("Unknown model key %r  (valid: %s)", args.id, valid)
            return 1
        targets = {args.id: REQUIRED_MODELS[args.id]}
    else:
        targets = dict(REQUIRED_MODELS)

    results: dict[str, bool] = {}
    for key, cfg in targets.items():
        results[key] = download_model(key, cfg)

    ok = sum(results.values())
    total = len(results)
    print()
    for key, success in results.items():
        mark = "✓" if success else "✗"
        print(f"  {mark}  {key}")
    print(f"\n{ok}/{total} model(s) ready in {models_dir.resolve()}")

    return 0 if ok == total else 1

if __name__ == "__main__":
    sys.exit(main())
