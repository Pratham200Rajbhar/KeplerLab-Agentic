"""Web search tool — Multi-query web search + scrape + LLM synthesis.

Queries an external search service, scrapes top results, scores them,
and returns synthesised context with inline citations.
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator, Dict, List
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.services.chat_v2.schemas import ToolResult
from app.services.chat_v2.streaming import (
    sse_tool_start,
    sse_tool_result,
    sse,
    sse_web_sources,
)

logger = logging.getLogger(__name__)


async def execute(
    query: str,
    user_id: str,
) -> AsyncIterator[str | ToolResult]:
    """Run multi-query web search, scrape, and return context.

    Yields:
        SSE events for streaming progress (tool_start, web_start, web_scraping, web_sources, tool_result).
        Final yield is always a ToolResult.
    """
    yield sse_tool_start("web_search", label="Searching the web…")

    try:
        # Step 1: Generate search queries via LLM
        from app.services.llm_service.llm import get_llm

        llm_planner = get_llm(temperature=0.1)
        query_prompt = (
            f"Generate 1-3 optimized web search queries to answer this question. "
            f"Return ONLY a JSON array of strings, nothing else.\n\n"
            f"Question: {query}\n\nQueries:"
        )
        query_response = await llm_planner.ainvoke(query_prompt)
        query_text = getattr(query_response, "content", str(query_response)).strip()

        queries = [query]  # fallback
        try:
            parsed = json.loads(query_text.strip().strip("```json").strip("```"))
            if isinstance(parsed, list) and len(parsed) > 0:
                queries = [str(q) for q in parsed[:3]]
        except Exception:
            pass

        yield sse("web_start", {"queries": queries})

        # Step 2: Search via external service
        all_results: List[Dict[str, Any]] = []
        seen_urls: set = set()

        for q in queries:
            try:
                async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                    resp = await client.post(
                        f"{settings.SEARCH_SERVICE_URL}/api/search",
                        json={"query": q, "engine": "duckduckgo"},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    for r in data.get("organic_results", []):
                        url = r.get("link", "")
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_results.append({
                                "title": r.get("title", ""),
                                "url": url,
                                "snippet": r.get("snippet", ""),
                            })
            except Exception:
                pass

        # Step 3: Scrape top 5
        scraped: List[Dict[str, Any]] = []
        for r in all_results[:5]:
            url = r["url"]
            yield sse("web_scraping", {"url": url, "status": "fetching"})
            try:
                async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                    resp = await client.post(
                        f"{settings.SEARCH_SERVICE_URL}/api/scrape",
                        json={"url": url},
                    )
                    resp.raise_for_status()
                    scrape_data = resp.json()
                    inner = scrape_data.get("content", scrape_data)
                    if isinstance(inner, dict):
                        title = inner.get("title", r["title"])
                        raw_content = inner.get("content", r["snippet"])
                        body = (" ".join(raw_content) if isinstance(raw_content, list) else str(raw_content))[:4000]
                    else:
                        title = r["title"]
                        body = str(inner)[:4000]
                    domain = urlparse(url).netloc

                    yield sse("web_scraping", {"url": url, "status": "done"})
                    scraped.append({
                        "title": title, "url": url, "domain": domain,
                        "content": body, "snippet": r["snippet"],
                    })
            except Exception:
                yield sse("web_scraping", {"url": url, "status": "failed"})
                scraped.append({
                    "title": r["title"], "url": url,
                    "domain": urlparse(url).netloc,
                    "content": r["snippet"], "snippet": r["snippet"],
                })

        # Step 4: Score and filter
        for s in scraped:
            content_score = min(len(s.get("content", "")), 2000) / 2000
            msg_words = set(query.lower().split())
            content_words = set(s.get("content", "").lower().split()[:200])
            overlap = len(msg_words & content_words)
            s["_score"] = content_score * 0.5 + min(overlap / max(len(msg_words), 1), 1.0) * 0.5

        scraped.sort(key=lambda x: x.get("_score", 0), reverse=True)
        scraped = scraped[:5]

        # Build context for LLM synthesis
        context = "\n\n".join(
            f"[{i+1}] {s['title']}\nURL: {s['url']}\n{s['content'][:2000]}"
            for i, s in enumerate(scraped)
        )

        sources = [
            {"title": s["title"], "url": s["url"], "index": i + 1}
            for i, s in enumerate(scraped)
        ]
        yield sse_web_sources(sources)
        yield sse_tool_result("web_search", success=True, summary=f"Found {len(scraped)} sources")

        yield ToolResult(
            tool_name="web_search",
            success=True,
            content=context,
            metadata={"queries": queries, "sources": sources},
        )

    except Exception as exc:
        logger.error("Web search failed: %s", exc)
        yield sse_tool_result("web_search", success=False, summary="Web search failed")
        yield ToolResult(
            tool_name="web_search",
            success=False,
            content="",
            metadata={"error": str(exc)},
        )
