from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from urllib.parse import urlparse

import trafilatura
from trafilatura.settings import use_config as _use_trafila_config

logger = logging.getLogger(__name__)

_FETCH_TIMEOUT = 30

# Longer HTTP timeout so deep-research can spend time on slow pages
_TRAFILA_CONFIG = _use_trafila_config()
_TRAFILA_CONFIG.set("DEFAULT", "TIMEOUT", "30")


def _ddg_search_sync(query: str, max_results: int = 5) -> list:
    """
    Search using DuckDuckGo's html endpoint, falling back to auto.
    Retries up to 2 times with back-off on rate-limit errors.
    """
    import time
    from ddgs import DDGS

    # DDGS v9.x: 'html' is DuckDuckGo native; 'auto' tries all engines
    backends = ["html", "auto"]
    last_exc: Optional[Exception] = None

    for backend in backends:
        for attempt in range(2):
            try:
                d = DDGS()
                results = list(d.text(query, max_results=max_results, backend=backend))
                if results:
                    return results
                break  # empty but no error — try next backend
            except Exception as exc:
                last_exc = exc
                msg = str(exc).lower()
                if any(k in msg for k in ("ratelimit", "202", "timeout", "429", "blocked")):
                    wait = 1.5 * (attempt + 1)
                    logger.debug(
                        "[ddg_search] %s backend rate-limited (attempt %d), retrying in %.1fs",
                        backend, attempt + 1, wait,
                    )
                    time.sleep(wait)
                    continue
                logger.debug("[ddg_search] %s backend error: %s", backend, exc)
                break

    if last_exc is not None:
        raise last_exc
    return []


async def ddg_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """Async wrapper — used by /web, /research, and /search/web fallback."""
    try:
        raw = await asyncio.to_thread(_ddg_search_sync, query, max_results)
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            }
            for r in raw
            if r.get("href")
        ]
    except Exception as exc:
        logger.warning("[ddg_search] Failed for query=%r: %s", query, exc)
        return []


def _fetch_and_extract_sync(url: str) -> Optional[Dict[str, str]]:
    downloaded = trafilatura.fetch_url(url, config=_TRAFILA_CONFIG)
    if not downloaded:
        return None

    text = trafilatura.extract(
        downloaded,
        include_comments=False,
        include_tables=True,
        no_fallback=False,
    )
    if not text:
        return None

    from trafilatura.metadata import extract_metadata

    meta = extract_metadata(downloaded)
    title = meta.title if meta and meta.title else ""

    return {
        "url": url,
        "title": title,
        "domain": urlparse(url).netloc,
        "text": text[:8000],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


async def fetch_url_content(url: str) -> Optional[Dict[str, str]]:
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_fetch_and_extract_sync, url),
            timeout=_FETCH_TIMEOUT,
        )
    except asyncio.TimeoutError:
        logger.debug("[fetch_url] Timeout fetching %s", url)
        return None
    except Exception as exc:
        logger.debug("[fetch_url] Failed %s: %s", url, exc)
        return None
