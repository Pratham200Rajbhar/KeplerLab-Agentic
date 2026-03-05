"""Deep Web Research Pipeline — iterative multi-pass structured research.

Triggered ONLY when ``intent_override = "WEB_RESEARCH"`` (from /research slash
command).  This is a dedicated pipeline, NOT the agent loop.

Iterative approach (3 passes):
1. Decompose query into sub-questions
2. For each iteration:
   a. Search web for current queries
   b. Fetch content from top URLs
   c. Partial synthesis + gap analysis → generate follow-up queries
3. Final synthesis → markdown report with citations

SSE events emitted: research_start, research_phase, research_source, token,
citations, done, error.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from app.core.config import settings
from app.services.llm_service.llm import get_llm

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────

_FETCH_TIMEOUT = 10  # seconds per URL
_MAX_URLS_PER_SUBQ = 3
_MAX_TOTAL_URLS = 15
_SEARCH_RESULTS_PER_SUBQ = 5
_MAX_ITERATIONS = 3  # research passes


# ── Helpers ───────────────────────────────────────────────────

def _sse(event_type: str, data: Any) -> str:
    # Standard SSE format: event type on its own line, then data payload.
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


async def _web_search(query: str, n: int = _SEARCH_RESULTS_PER_SUBQ) -> List[Dict[str, str]]:
    """Search the web via external search service.

    Returns list of {title, url, snippet}.
    """
    from app.core.config import settings

    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.post(
                f"{settings.SEARCH_SERVICE_URL}/api/search",
                json={"query": query, "engine": "duckduckgo"},
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for r in data.get("organic_results", [])[:n]:
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "snippet": r.get("snippet", ""),
                })
            return results
    except Exception as exc:
        logger.warning("[research] Web search failed: %s", exc)
        return []


async def _fetch_url(url: str) -> Optional[Dict[str, str]]:
    """Fetch a URL via external scrape service. Returns None on failure."""
    from app.core.config import settings
    from urllib.parse import urlparse

    try:
        async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT, follow_redirects=True) as client:
            resp = await client.post(
                f"{settings.SEARCH_SERVICE_URL}/api/scrape",
                json={"url": url},
            )
            resp.raise_for_status()
            scrape_data = resp.json()

        # Scrape API returns {"content": {"url", "title", "content": [paragraphs]}}
        inner = scrape_data.get("content", scrape_data)
        if isinstance(inner, dict):
            title = inner.get("title", "")
            raw_content = inner.get("content", "")
            if isinstance(raw_content, list):
                body = " ".join(raw_content)[:6000]
            else:
                body = str(raw_content)[:6000]
        else:
            title = scrape_data.get("title", "")
            body = str(inner)[:6000]
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


# ── Gap Analysis (for iterative research) ─────────────────────

async def _identify_gaps(
    query: str,
    synthesis: Dict[str, Any],
    previous_queries: List[str],
) -> List[Dict[str, str]]:
    """Analyze synthesis for gaps and generate follow-up queries."""
    llm = get_llm(temperature=0.3)

    findings_summary = json.dumps(synthesis.get("key_findings", [])[:5], default=str)
    conflicts_summary = json.dumps(synthesis.get("conflicting_information", [])[:3], default=str)

    prompt = (
        "You are a research gap analyst. Based on the original query and findings so far, "
        "identify 2-3 information gaps or areas needing deeper investigation.\n\n"
        f"Original query: {query}\n\n"
        f"Key findings so far:\n{findings_summary}\n\n"
        f"Conflicting information:\n{conflicts_summary}\n\n"
        f"Previous search queries (avoid repeating):\n{json.dumps(previous_queries)}\n\n"
        "Return ONLY a JSON array of follow-up queries:\n"
        '[{"sub_question": "...", "search_query": "...", "reason": "..."}]\n\n'
        'If the research is sufficiently complete, return an empty array: []'
    )

    resp = await llm.ainvoke(prompt)
    raw = getattr(resp, "content", str(resp)).strip()

    import re
    try:
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        items = json.loads(m.group()) if m else []
    except Exception:
        items = []

    return items


# ── Public Streaming Entry Point ──────────────────────────────

async def stream_research(
    query: str,
    user_id: str,
    notebook_id: str,
    session_id: str,
) -> AsyncIterator[str]:
    """Run the iterative multi-pass research pipeline and stream SSE events.

    Yields SSE events: research_start, research_phase, research_source, token,
    citations, done, error.
    """
    start_time = time.time()
    all_sources: List[Dict[str, str]] = []
    all_queries_used: List[str] = []
    seen_urls: set = set()

    try:
        # Emit research_start
        yield _sse("research_start", {
            "max_iterations": _MAX_ITERATIONS,
        })

        # ── Initial Decomposition ──
        yield _sse("research_phase", {
            "iteration": 0,
            "phase": "searching",
            "label": "Breaking query into sub-questions",
        })
        sub_questions = await _decompose_query(query)
        current_queries = sub_questions
        all_queries_used.extend([sq["search_query"] for sq in sub_questions])

        yield _sse("research_phase", {
            "iteration": 0,
            "phase": "searching",
            "label": f"Generated {len(sub_questions)} sub-questions",
            "queries": [sq["search_query"] for sq in sub_questions],
        })

        synthesis = None

        for iteration in range(1, _MAX_ITERATIONS + 1):
            # ── Search ──
            yield _sse("research_phase", {
                "iteration": iteration,
                "phase": "searching",
                "label": f"Iteration {iteration}: searching {len(current_queries)} queries",
                "queries": [sq["search_query"] for sq in current_queries],
            })
            search_results = await _parallel_search(current_queries)

            # Deduplicate vs. previously seen
            new_results = []
            for r in search_results:
                url = r.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    new_results.append(r)

            if not new_results and not all_sources:
                yield _sse("token", {
                    "content": "No search results found. Try rephrasing your query.",
                })
                yield _sse("done", {})
                return

            if not new_results:
                yield _sse("research_phase", {
                    "iteration": iteration,
                    "phase": "searching",
                    "label": "No new results found, skipping to synthesis",
                })
                break

            # ── Fetch ──
            yield _sse("research_phase", {
                "iteration": iteration,
                "phase": "reading",
                "label": f"Fetching content from {min(len(new_results), _MAX_TOTAL_URLS)} sources",
            })
            sources = await _parallel_fetch(new_results)

            # Emit individual source events
            for s in sources:
                yield _sse("research_source", {
                    "index": len(all_sources) + 1,
                    "title": s.get("title", ""),
                    "url": s.get("url", ""),
                    "domain": s.get("domain", ""),
                    "snippet": s.get("text", "")[:200],
                    "iteration_found": iteration,
                })

            all_sources.extend(sources)

            yield _sse("research_phase", {
                "iteration": iteration,
                "phase": "reading",
                "label": f"Fetched {len(sources)} sources (total: {len(all_sources)})",
            })

            if not all_sources:
                yield _sse("token", {
                    "content": "Could not fetch content from any sources. Try a different query.",
                })
                yield _sse("done", {})
                return

            # ── Partial Synthesis ──
            yield _sse("research_phase", {
                "iteration": iteration,
                "phase": "analyzing",
                "label": f"Cross-referencing {len(all_sources)} sources",
            })
            synthesis = await _synthesize(query, all_sources)

            # ── Gap Analysis (skip on last iteration) ──
            if iteration < _MAX_ITERATIONS:
                yield _sse("research_phase", {
                    "iteration": iteration,
                    "phase": "analyzing",
                    "label": "Identifying research gaps...",
                })
                follow_ups = await _identify_gaps(query, synthesis, all_queries_used)

                if not follow_ups:
                    yield _sse("research_phase", {
                        "iteration": iteration,
                        "phase": "analyzing",
                        "label": "Research is sufficiently complete",
                    })
                    break

                current_queries = follow_ups
                all_queries_used.extend([fq["search_query"] for fq in follow_ups])

                yield _sse("research_phase", {
                    "iteration": iteration,
                    "phase": "analyzing",
                    "label": f"Found {len(follow_ups)} follow-up queries",
                    "queries": [fq["search_query"] for fq in follow_ups],
                })

        # ── Final Report ──
        if synthesis is None:
            yield _sse("error", {"error": "No synthesis produced"})
            yield _sse("done", {})
            return

        yield _sse("research_phase", {
            "status": "synthesizing",
            "phase": "writing",
            "label": "Writing research report...",
        })
        report = _format_report(synthesis, all_sources)

        # Stream as token events
        CHUNK = 80
        for i in range(0, len(report), CHUNK):
            yield _sse("token", {"content": report[i:i + CHUNK]})

        # Final events
        citations = []
        for i, s in enumerate(all_sources):
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
                "sourcesCount": len(all_sources),
                "queriesCount": len(all_queries_used),
                "elapsedTime": elapsed,
                "sourceUrls": [s.get("url", "") for s in all_sources],
            })
        except Exception as exc:
            logger.warning("[research] DB persist failed (non-fatal): %s", exc)

    except Exception as exc:
        logger.exception("[research] Pipeline error: %s", exc)
        yield _sse("error", {"error": str(exc)})
        yield _sse("done", {})
