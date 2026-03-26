from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_CACHE_LOCK = asyncio.Lock()
_CACHE: Optional[Dict[str, Dict[str, Any]]] = None
_INFLIGHT_LOCK = asyncio.Lock()
_INFLIGHT: Dict[str, asyncio.Task] = {}
_SEARCH_SEMAPHORE = asyncio.Semaphore(3)
_CACHE_FILE = os.path.abspath(
    os.path.join(settings.GENERATED_OUTPUT_DIR, "..", "notebook_thumbnails.json")
)


def _cache_key(user_id: str, notebook_id: str) -> str:
    return f"{user_id}:{notebook_id}"


def _fallback_query(name: str, description: Optional[str]) -> str:
    seed = (description or "").strip() or name.strip() or "learning"
    compact = re.sub(r"\s+", " ", seed).strip()
    words = [w for w in re.findall(r"[a-zA-Z0-9]+", compact.lower()) if len(w) > 2]
    core = " ".join(words[:5]) or "learning"
    return f"{core} minimal abstract notebook cover"


async def _load_cache() -> Dict[str, Dict[str, Any]]:
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    if not os.path.exists(_CACHE_FILE):
        _CACHE = {}
        return _CACHE

    try:
        with open(_CACHE_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
            _CACHE = raw if isinstance(raw, dict) else {}
    except Exception as exc:
        logger.warning("Thumbnail cache load failed: %s", exc)
        _CACHE = {}
    return _CACHE


async def _save_cache(cache: Dict[str, Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(_CACHE_FILE), exist_ok=True)
    tmp_path = f"{_CACHE_FILE}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(cache, f)
    os.replace(tmp_path, _CACHE_FILE)


async def _generate_search_query(name: str, description: Optional[str]) -> str:
    # Keep query generation deterministic and fast to avoid LLM rate-limit bottlenecks.
    return _fallback_query(name, description)


async def _search_images(query: str, num_images: int = 10) -> List[str]:
    if not settings.WEB_IMAGE_SEARCH_ENDPOINT:
        return []

    params = {
        "query": query,
        "engine": "bing",
        "num_images": str(num_images),
    }

    try:
        async with _SEARCH_SEMAPHORE:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(settings.WEB_IMAGE_SEARCH_ENDPOINT, params=params)
                response.raise_for_status()
                payload = response.json()
    except Exception as exc:
        logger.warning("Image search request failed: %s", exc)
        return []

    images = payload.get("images", []) if isinstance(payload, dict) else []
    urls: List[str] = []
    for item in images:
        if not isinstance(item, dict):
            continue
        url = item.get("image_url")
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            urls.append(url)
    return urls


def _domain_penalty(url: str) -> int:
    domain = (urlparse(url).netloc or "").lower()
    if any(bad in domain for bad in ("dreamstime", "freepik", "shutterstock", "istock")):
        return 2
    if any(good in domain for good in ("unsplash", "pexels", "pixabay", "wikimedia")):
        return -1
    return 0


async def _pick_best_image(name: str, description: Optional[str], query: str, image_urls: List[str]) -> int:
    if not image_urls:
        return -1

    scored = sorted(
        enumerate(image_urls),
        key=lambda pair: (_domain_penalty(pair[1]), len(pair[1])),
    )
    return int(scored[0][0]) if scored else 0


async def _build_thumbnail_payload(name: str, description: Optional[str]) -> Dict[str, Any]:
    query = await _generate_search_query(name=name, description=description)
    image_urls = await _search_images(query=query)
    best_index = await _pick_best_image(name=name, description=description, query=query, image_urls=image_urls)
    thumbnail_url = image_urls[best_index] if 0 <= best_index < len(image_urls) else None
    return {
        "thumbnail_url": thumbnail_url,
        "thumbnail_query": query,
        "thumbnail_updated_at": datetime.now(timezone.utc).isoformat(),
    }


async def get_cached_notebook_thumbnail(notebook_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    async with _CACHE_LOCK:
        cache = await _load_cache()
        item = cache.get(_cache_key(user_id, notebook_id))
        if not item:
            return None
        return {
            "thumbnail_url": item.get("thumbnail_url"),
            "thumbnail_query": item.get("thumbnail_query"),
            "thumbnail_updated_at": item.get("thumbnail_updated_at"),
        }


async def ensure_notebook_thumbnail(
    notebook_id: str,
    user_id: str,
    name: str,
    description: Optional[str],
    force: bool = False,
) -> Dict[str, Any]:
    key = _cache_key(user_id, notebook_id)

    async with _CACHE_LOCK:
        cache = await _load_cache()
        existing = cache.get(key)
        if existing and existing.get("thumbnail_url") and not force:
            return {
                "thumbnail_url": existing.get("thumbnail_url"),
                "thumbnail_query": existing.get("thumbnail_query"),
                "thumbnail_updated_at": existing.get("thumbnail_updated_at"),
            }

    if force:
        result = await _build_thumbnail_payload(name=name, description=description)
        async with _CACHE_LOCK:
            cache = await _load_cache()
            cache[key] = result
            await _save_cache(cache)
        return result

    created_task = False
    async with _INFLIGHT_LOCK:
        task = _INFLIGHT.get(key)
        if task is None:
            task = asyncio.create_task(_build_thumbnail_payload(name=name, description=description))
            _INFLIGHT[key] = task
            created_task = True

    try:
        result = await task
    finally:
        if created_task:
            async with _INFLIGHT_LOCK:
                if _INFLIGHT.get(key) is task:
                    _INFLIGHT.pop(key, None)

    async with _CACHE_LOCK:
        cache = await _load_cache()
        cache[key] = result
        await _save_cache(cache)

    return result


async def invalidate_notebook_thumbnail(notebook_id: str, user_id: str) -> None:
    async with _CACHE_LOCK:
        cache = await _load_cache()
        key = _cache_key(user_id, notebook_id)
        if key in cache:
            cache.pop(key, None)
            await _save_cache(cache)
