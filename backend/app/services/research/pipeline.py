from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any, AsyncIterator, Dict, List, Optional

from app.core.web_search import ddg_search, fetch_url_content
from app.services.llm_service.llm import get_llm
from app.prompts import (
    get_research_decompose_prompt,
    get_research_gap_prompt,
    get_research_report_prompt,
)

logger = logging.getLogger(__name__)

# ── Deep research constants ─────────────────────────────────────────────────
# Target: 40-60 websites across multiple search rounds
_FETCH_TIMEOUT      = 20           # per-URL timeout (seconds)
_RESULTS_PER_QUERY  = 15           # DDG results per search query
_URLS_PER_ROUND     = 15           # max URLs to fetch per round
_MAX_ROUNDS         = 5            # search → fetch rounds (5 × 15 = 75 candidate URLs)
_INITIAL_SUB_QUESTIONS = 8         # initial sub-questions for decomposition
_FOLLOWUP_QUERIES   = 6            # follow-up queries per gap round
_SOURCE_TEXT_LIMIT  = 6000         # chars kept per fetched page
_MIN_SOURCES_TARGET = 50           # stop early if we hit this many sources


def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# ─── Helpers ────────────────────────────────────────────────────────────────

def _parse_json_array(text: str) -> list:
    """Extract the first JSON array from LLM output."""
    m = re.search(r"\[.*\]", text, re.DOTALL)
    return json.loads(m.group()) if m else []


async def _decompose_query(query: str, n: int = _INITIAL_SUB_QUESTIONS) -> List[Dict[str, str]]:
    llm = get_llm(temperature=0.3)
    prompt = get_research_decompose_prompt(query, n)
    resp = await llm.ainvoke(prompt)
    raw = getattr(resp, "content", str(resp)).strip()
    try:
        items = _parse_json_array(raw)
    except Exception:
        items = []
    if not items:
        items = [{"sub_question": query, "search_query": query}]
    return items


async def _search_batch(
    queries: List[Dict[str, str]],
    seen_urls: set,
) -> List[Dict[str, Any]]:
    """Run all queries in parallel, dedup against seen_urls, return new results."""
    async def _one(sq):
        try:
            return await ddg_search(sq["search_query"], max_results=_RESULTS_PER_QUERY)
        except Exception as exc:
            logger.warning("[research] search failed: %s", exc)
            return []

    batches = await asyncio.gather(*(_one(sq) for sq in queries), return_exceptions=True)
    new_results: List[Dict[str, Any]] = []
    for batch in batches:
        if isinstance(batch, Exception):
            continue
        for r in batch:
            url = r.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                new_results.append(r)
    return new_results


async def _fetch_streaming(
    urls: List[str],
    all_sources: List[Dict],
    batch_offset: int,
) -> AsyncIterator:
    """Fetch URLs concurrently, yield research_source SSE per result as it arrives."""
    queue: asyncio.Queue = asyncio.Queue()

    async def _enqueue(url: str):
        try:
            result = await asyncio.wait_for(
                fetch_url_content(url), timeout=_FETCH_TIMEOUT,
            )
            await queue.put(result)
        except Exception:
            await queue.put(None)

    tasks = [asyncio.create_task(_enqueue(u)) for u in urls]
    fetched: List[Dict] = []
    for _ in range(len(urls)):
        result = await queue.get()
        if isinstance(result, dict) and result.get("text"):
            idx = batch_offset + len(fetched) + 1
            yield _sse("research_source", {
                "index": idx,
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "domain": result.get("domain", ""),
                "snippet": result.get("text", "")[:200],
            })
            fetched.append(result)
    await asyncio.gather(*tasks, return_exceptions=True)
    all_sources.extend(fetched)


async def _identify_gaps(
    query: str,
    all_sources: List[Dict],
    previous_queries: List[str],
) -> List[Dict[str, str]]:
    """
    Build a richer coverage summary (not just titles) to help the LLM identify
    real gaps — what topics and subtopics are covered vs. still missing.
    """
    llm = get_llm(temperature=0.3)

    # Build a richer summary: title + first 200 chars of content
    coverage_lines = []
    for s in all_sources[-30:]:
        title = s.get("title", "?")
        domain = s.get("domain", "?")
        snippet = s.get("text", "")[:200].replace("\n", " ")
        coverage_lines.append(f"- [{domain}] {title}: {snippet}")
    sources_summary = "\n".join(coverage_lines)

    prompt = get_research_gap_prompt(query, sources_summary, json.dumps(previous_queries))
    resp = await llm.ainvoke(prompt)
    raw = getattr(resp, "content", str(resp)).strip()
    try:
        return _parse_json_array(raw)
    except Exception:
        return []


def _build_source_context(sources: List[Dict], max_sources: int = 50) -> str:
    """Build a source block for the report-writing LLM, using as many sources as possible."""
    parts = []
    for i, s in enumerate(sources[:max_sources]):
        text = s.get("text", "")[:_SOURCE_TEXT_LIMIT]
        parts.append(
            f"[SOURCE {i+1}] {s.get('title', 'N/A')} — {s.get('domain', '')}\n"
            f"URL: {s.get('url', '')}\n"
            f"{text}"
        )
    return "\n\n---\n\n".join(parts)


# ─── Main streaming pipeline ───────────────────────────────────────────────

async def stream_research(
    query: str,
    user_id: str,
    notebook_id: str,
    session_id: str,
) -> AsyncIterator[str]:
    start = time.time()
    all_sources: List[Dict[str, str]] = []
    all_queries_used: List[str] = []
    seen_urls: set = set()

    try:
        yield _sse("research_start", {})

        # ── Round 0: decompose query into sub-questions ──
        yield _sse("research_phase", {
            "phase": "searching",
            "label": "Preparing search plan…",
        })
        sub_questions = await _decompose_query(query, _INITIAL_SUB_QUESTIONS)
        current_queries = sub_questions
        all_queries_used.extend(sq["search_query"] for sq in sub_questions)

        yield _sse("research_phase", {
            "phase": "searching",
            "label": f"Searching {len(sub_questions)} angles simultaneously…",
            "queries": [sq["search_query"] for sq in sub_questions],
        })

        # ── Search → Fetch rounds ──
        for rnd in range(1, _MAX_ROUNDS + 1):
            yield _sse("research_phase", {
                "phase": "searching",
                "label": f"Round {rnd}: looking up {len(current_queries)} queries…",
                "queries": [sq["search_query"] for sq in current_queries],
            })
            new_results = await _search_batch(current_queries, seen_urls)

            if not new_results and not all_sources:
                yield _sse("token", {"content": "No search results found. Try rephrasing your query."})
                yield _sse("done", {})
                return

            if not new_results:
                logger.info("[research] No new URLs in round %d — stopping early", rnd)
                break

            # Fetch — stream each source as it arrives
            urls_to_fetch = [r["url"] for r in new_results[:_URLS_PER_ROUND] if r.get("url")]
            yield _sse("research_phase", {
                "phase": "reading",
                "label": f"Opening {len(urls_to_fetch)} websites…",
                "sources_fetched": len(all_sources),
            })

            async for evt in _fetch_streaming(urls_to_fetch, all_sources, len(all_sources)):
                yield evt

            yield _sse("research_phase", {
                "phase": "reading",
                "label": f"Read {len(all_sources)} websites so far",
                "sources_fetched": len(all_sources),
            })

            if not all_sources:
                yield _sse("token", {"content": "Could not read any sources. Try a different query."})
                yield _sse("done", {})
                return

            logger.info("[research] Round %d complete — %d total sources", rnd, len(all_sources))

            # Stop if we've hit our target
            if len(all_sources) >= _MIN_SOURCES_TARGET or rnd >= _MAX_ROUNDS:
                logger.info(
                    "[research] Stopping after round %d — %d sources collected (target: %d)",
                    rnd, len(all_sources), _MIN_SOURCES_TARGET
                )
                break

            # Identify gaps for next round using richer coverage summary
            yield _sse("research_phase", {
                "phase": "synthesizing",
                "label": f"Analyzing coverage gaps ({len(all_sources)} sources so far)…",
            })
            follow_ups = await _identify_gaps(query, all_sources, all_queries_used)
            if not follow_ups:
                logger.info("[research] No gaps identified — stopping after round %d", rnd)
                break

            current_queries = follow_ups[:_FOLLOWUP_QUERIES]
            all_queries_used.extend(sq["search_query"] for sq in current_queries)

            yield _sse("research_phase", {
                "phase": "searching",
                "label": f"Exploring {len(current_queries)} uncovered angles…",
                "queries": [sq["search_query"] for sq in current_queries],
            })

        # ── Write the detailed report via LLM streaming ──
        yield _sse("research_phase", {
            "phase": "writing",
            "label": f"Writing comprehensive analysis from {len(all_sources)} sources…",
        })

        source_ctx = _build_source_context(all_sources, max_sources=_MIN_SOURCES_TARGET)
        llm = get_llm(temperature=0.3)

        report_prompt = get_research_report_prompt(query, source_ctx, len(all_sources))

        full_report = []
        async for chunk in llm.astream(report_prompt):
            token = getattr(chunk, "content", str(chunk))
            if token:
                full_report.append(token)
                yield _sse("token", {"content": token})

        # Citations
        citations = []
        for i, s in enumerate(all_sources):
            citations.append({
                "index": i + 1,
                "title": s.get("title", ""),
                "url": s.get("url", ""),
                "domain": s.get("domain", ""),
                "accessed_at": s.get("fetched_at", ""),
            })
        yield _sse("citations", {"citations": citations})

        elapsed = round(time.time() - start, 2)
        yield _sse("done", {"elapsed": elapsed, "sources_count": len(all_sources)})

        # Persist
        report_text = "".join(full_report)
        try:
            from app.db.prisma_client import prisma
            await prisma.researchsession.create(data={
                "userId": user_id,
                "notebookId": notebook_id,
                "query": query,
                "report": report_text,
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
