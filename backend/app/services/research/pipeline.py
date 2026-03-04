"""Deep Web Research Pipeline — 5-step structured research.

Triggered ONLY when ``intent_override = "WEB_RESEARCH"`` (from /research slash
command).  This is a dedicated pipeline, NOT the agent loop.

Steps
-----
1. Query Decomposer — break user query into 4-6 sub-questions
2. Parallel Web Search — concurrent search for all sub-questions
3. Parallel Content Fetching — fetch top URLs, extract text
4. Synthesizer — LLM cross-references all sources into structured JSON
5. Report Formatter — convert JSON → markdown with streaming + citations
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings
from app.services.llm_service.llm import get_llm

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────

_FETCH_TIMEOUT = 10  # seconds per URL
_MAX_URLS_PER_SUBQ = 3
_MAX_TOTAL_URLS = 15
_SEARCH_RESULTS_PER_SUBQ = 5


# ── Helpers ───────────────────────────────────────────────────

def _sse(event_type: str, data: Any) -> str:
    # Standard SSE format: event type on its own line, then data payload.
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


async def _web_search(query: str, n: int = _SEARCH_RESULTS_PER_SUBQ) -> List[Dict[str, str]]:
    """Search the web using the existing research graph helpers or DuckDuckGo.

    Returns list of {title, url, snippet}.
    """
    try:
        from app.services.agent.subgraphs.research_graph import _execute_searches, _generate_queries
        urls = await _execute_searches([query], time.time())
        return [{"title": "", "url": u, "snippet": ""} for u in urls[:n]]
    except Exception:
        pass

    # Fallback: DuckDuckGo lite
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=n):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", r.get("link", "")),
                    "snippet": r.get("body", ""),
                })
        return results
    except Exception as exc:
        logger.warning("[research] Web search failed: %s", exc)
        return []


async def _fetch_url(url: str) -> Optional[Dict[str, str]]:
    """Fetch a URL and extract text content. Returns None on failure."""
    try:
        async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "KeplerLab/1.0 Research Bot"})
            resp.raise_for_status()
            html = resp.text

        soup = BeautifulSoup(html, "html.parser")
        # Remove nav, footer, script, style
        for tag in soup(["nav", "footer", "script", "style", "header", "aside"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        body = soup.get_text(separator="\n", strip=True)

        # Trim to reasonable size
        body = body[:6000]
        from urllib.parse import urlparse
        domain = urlparse(url).netloc

        return {
            "url": url,
            "title": title,
            "domain": domain,
            "text": body,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.debug("[research] Failed to fetch %s: %s", url, exc)
        return None


# ── Step 1: Query Decomposer ─────────────────────────────────

async def _decompose_query(query: str) -> List[Dict[str, str]]:
    """Break user query into 4-6 targeted sub-questions."""
    llm = get_llm(temperature=0.3)
    prompt = (
        "You are a research query decomposer. Break this query into 4-6 targeted "
        "sub-questions that together fully cover the topic.\n\n"
        f"Query: {query}\n\n"
        "Return ONLY a JSON array:\n"
        '[{"sub_question": "...", "search_query": "..."}]\n\n'
        "The search_query should be optimised for web search engines."
    )
    resp = await llm.ainvoke(prompt)
    raw = getattr(resp, "content", str(resp)).strip()

    import re
    try:
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        items = json.loads(m.group()) if m else []
    except Exception:
        items = [{"sub_question": query, "search_query": query}]

    if not items:
        items = [{"sub_question": query, "search_query": query}]

    return items


# ── Step 2: Parallel Web Search ───────────────────────────────

async def _parallel_search(sub_questions: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Run all sub-question searches concurrently, deduplicate URLs."""
    tasks = [_web_search(sq["search_query"]) for sq in sub_questions]
    results_per_sq = await asyncio.gather(*tasks, return_exceptions=True)

    seen_urls: set = set()
    all_results: List[Dict[str, Any]] = []

    for i, results in enumerate(results_per_sq):
        if isinstance(results, Exception):
            logger.warning("[research] Search %d failed: %s", i, results)
            continue
        for r in results:
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_results.append({
                    **r,
                    "sub_question_index": i,
                })

    return all_results


# ── Step 3: Parallel Content Fetching ─────────────────────────

async def _parallel_fetch(search_results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Fetch top URLs concurrently, up to _MAX_TOTAL_URLS."""
    urls_to_fetch = [r["url"] for r in search_results[:_MAX_TOTAL_URLS] if r.get("url")]
    tasks = [_fetch_url(url) for url in urls_to_fetch]
    fetched = await asyncio.gather(*tasks, return_exceptions=True)

    sources = []
    for result in fetched:
        if isinstance(result, dict) and result.get("text"):
            sources.append(result)

    return sources


# ── Step 4: Synthesizer ──────────────────────────────────────

async def _synthesize(query: str, sources: List[Dict[str, str]]) -> Dict[str, Any]:
    """Cross-reference all fetched sources into structured analysis."""
    llm = get_llm(temperature=0.2)

    source_block = "\n\n---\n\n".join(
        f"SOURCE {i + 1} [{s.get('domain', 'unknown')}] ({s.get('url', '')}):\n"
        f"Title: {s.get('title', 'N/A')}\n"
        f"{s.get('text', '')[:2000]}"
        for i, s in enumerate(sources[:10])
    )

    prompt = (
        "You are a research analyst. Synthesize these sources into a structured analysis.\n\n"
        f"Research query: {query}\n\n"
        f"{source_block}\n\n"
        "Return ONLY valid JSON with this structure:\n"
        "{\n"
        '  "executive_summary": "2-3 sentence overview",\n'
        '  "key_findings": [\n'
        '    {"finding": "...", "confidence": "high|medium|low", "source_indices": [1,2]}\n'
        '  ],\n'
        '  "conflicting_information": [\n'
        '    {"topic": "...", "positions": ["view A", "view B"], "source_indices": [[1], [3]]}\n'
        '  ],\n'
        '  "source_quality": [\n'
        '    {"index": 1, "domain": "...", "recency": "...", "relevance_score": 0.9, "rating": "high|medium|low"}\n'
        '  ]\n'
        "}\n"
    )

    resp = await llm.ainvoke(prompt)
    raw = getattr(resp, "content", str(resp)).strip()

    import re
    try:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(m.group()) if m else {}
    except Exception:
        data = {
            "executive_summary": "Synthesis failed — raw output available.",
            "key_findings": [],
            "conflicting_information": [],
            "source_quality": [],
        }

    return data


# ── Step 5: Report Formatter ─────────────────────────────────

def _format_report(synthesis: Dict[str, Any], sources: List[Dict[str, str]]) -> str:
    """Convert structured synthesis JSON into markdown report."""
    parts = []

    # Executive Summary
    parts.append("## Executive Summary\n")
    parts.append(synthesis.get("executive_summary", "No summary available."))
    parts.append("")

    # Key Findings
    findings = synthesis.get("key_findings", [])
    if findings:
        parts.append("## Key Findings\n")
        for f in findings:
            finding = f.get("finding", "")
            confidence = f.get("confidence", "medium")
            src_indices = f.get("source_indices", [])
            citations = "".join(f" [{i}]" for i in src_indices)
            parts.append(f"- {finding}{citations} *({confidence} confidence)*")
        parts.append("")

    # Conflicting Information
    conflicts = synthesis.get("conflicting_information", [])
    if conflicts:
        parts.append("## Conflicting Information\n")
        for c in conflicts:
            topic = c.get("topic", "")
            positions = c.get("positions", [])
            parts.append(f"**{topic}:**")
            for p in positions:
                parts.append(f"  - {p}")
        parts.append("")

    # Source Quality & Bibliography
    sq = synthesis.get("source_quality", [])
    parts.append("## Source Quality & Bibliography\n")
    parts.append("| # | Domain | Rating | Recency | Relevance |")
    parts.append("|---|--------|--------|---------|-----------|")
    for s in sq:
        idx = s.get("index", "?")
        domain = s.get("domain", "unknown")
        rating = s.get("rating", "medium")
        recency = s.get("recency", "unknown")
        relevance = s.get("relevance_score", 0.0)
        parts.append(f"| {idx} | {domain} | {rating} | {recency} | {relevance:.1f} |")
    parts.append("")

    # Full citations
    if sources:
        parts.append("### References\n")
        for i, s in enumerate(sources):
            title = s.get("title", "Untitled")
            url = s.get("url", "")
            domain = s.get("domain", "unknown")
            parts.append(f"{i + 1}. [{title}]({url}) — {domain}")

    return "\n".join(parts)


# ── Public Streaming Entry Point ──────────────────────────────

async def stream_research(
    query: str,
    user_id: str,
    notebook_id: str,
    session_id: str,
) -> AsyncIterator[str]:
    """Run the 5-step research pipeline and stream SSE events.

    Yields SSE events: research_phase, research_source, token, citations, done.
    """
    start_time = time.time()

    try:
        # Step 1: Decompose
        yield _sse("research_phase", {
            "phase": "decomposing",
            "detail": "Breaking query into sub-questions",
        })
        sub_questions = await _decompose_query(query)
        yield _sse("research_phase", {
            "phase": "decomposing",
            "detail": f"Generated {len(sub_questions)} sub-questions",
        })

        # Step 2: Parallel Search
        yield _sse("research_phase", {
            "phase": "searching",
            "detail": f"Running {len(sub_questions)} parallel searches",
        })
        search_results = await _parallel_search(sub_questions)
        yield _sse("research_phase", {
            "phase": "searching",
            "detail": f"Found {len(search_results)} unique URLs",
        })

        if not search_results:
            yield _sse("token", {
                "content": "No search results found. Try rephrasing your query.",
            })
            yield _sse("done", {})
            return

        # Step 3: Parallel Fetch
        yield _sse("research_phase", {
            "phase": "fetching",
            "detail": f"Fetching content from {min(len(search_results), _MAX_TOTAL_URLS)} sources",
        })
        sources = await _parallel_fetch(search_results)
        yield _sse("research_phase", {
            "phase": "fetching",
            "detail": f"Successfully fetched {len(sources)} sources",
        })

        # Emit individual source events
        for i, s in enumerate(sources):
            yield _sse("research_source", {
                "source": {
                    "index": i + 1,
                    "title": s.get("title", ""),
                    "url": s.get("url", ""),
                    "domain": s.get("domain", ""),
                    "snippet": s.get("text", "")[:200],
                    "relevance_score": 0.0,  # Set by synthesizer
                },
            })

        if not sources:
            yield _sse("token", {
                "content": "Could not fetch content from any sources. Try a different query.",
            })
            yield _sse("done", {})
            return

        # Step 4: Synthesize
        yield _sse("research_phase", {
            "phase": "synthesizing",
            "detail": f"Cross-referencing {len(sources)} sources",
        })
        synthesis = await _synthesize(query, sources)

        # Step 5: Format & Stream Report
        yield _sse("research_phase", {"phase": "formatting"})
        report = _format_report(synthesis, sources)

        # Stream as token events
        CHUNK = 80
        for i in range(0, len(report), CHUNK):
            yield _sse("token", {"content": report[i:i + CHUNK]})

        # Final events
        citations = []
        for i, s in enumerate(sources):
            citations.append({
                "index": i + 1,
                "title": s.get("title", ""),
                "url": s.get("url", ""),
                "domain": s.get("domain", ""),
                "rating": "medium",
                "accessed_at": s.get("fetched_at", ""),
            })
        yield _sse("citations", {"citations": citations})

        elapsed = round(time.time() - start_time, 2)
        yield _sse("done", {"elapsed": elapsed})

        # Persist research session
        try:
            from app.db.prisma_client import prisma
            await prisma.researchsession.create(data={
                "userId": user_id,
                "notebookId": notebook_id,
                "query": query,
                "report": report,
                "sourcesCount": len(sources),
                "queriesCount": len(sub_questions),
                "elapsedTime": elapsed,
                "sourceUrls": [s.get("url", "") for s in sources],
            })
        except Exception as exc:
            logger.warning("[research] DB persist failed (non-fatal): %s", exc)

    except Exception as exc:
        logger.exception("[research] Pipeline error: %s", exc)
        yield _sse("error", {"error": str(exc)})
        yield _sse("done", {})
