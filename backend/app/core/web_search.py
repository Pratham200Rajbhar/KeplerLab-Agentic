"""Shared DuckDuckGo web search and page scraping helpers.

All web search and URL content fetching goes through these functions.
No external search service required — uses duckduckgo-search + trafilatura.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from urllib.parse import urlparse

import httpx
import trafilatura

logger = logging.getLogger(__name__)

_FETCH_TIMEOUT = 10  # seconds per URL


# ── DuckDuckGo Search ────────────────────────────────────────


def _ddg_search_sync(query: str, max_results: int = 5) -> list:
    """Run DuckDuckGo text search (blocking)."""
    from ddgs import DDGS

    d = DDGS()
    return list(d.text(query, max_results=max_results))


async def ddg_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """Async DuckDuckGo web search.

    Returns list of ``{title, url, snippet}``.
    """
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


# ── URL Content Scraping ─────────────────────────────────────


def _fetch_and_extract_sync(url: str) -> Optional[Dict[str, str]]:
    """Download a URL and extract main text content (blocking)."""
    downloaded = trafilatura.fetch_url(url)
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

    # Try to extract title from the HTML
    from trafilatura.metadata import extract_metadata

    meta = extract_metadata(downloaded)
    title = meta.title if meta and meta.title else ""

    return {
        "url": url,
        "title": title,
        "domain": urlparse(url).netloc,
        "text": text[:6000],
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


async def fetch_url_content(url: str) -> Optional[Dict[str, str]]:
    """Async: download URL and extract readable text via trafilatura.

    Returns ``{url, title, domain, text, fetched_at}`` or *None* on failure.
    """
    try:
        return await asyncio.to_thread(_fetch_and_extract_sync, url)
    except Exception as exc:
        logger.debug("[fetch_url] Failed %s: %s", url, exc)
        return None
