from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any, AsyncIterator, Dict, List, Optional

from app.core.web_search import ddg_search, fetch_url_content
from app.services.llm_service.llm import get_llm

logger = logging.getLogger(__name__)

# ── Deep research constants ──
# Target: 30-50 websites across multiple search rounds
_FETCH_TIMEOUT = 15          # per-URL timeout (seconds)
_RESULTS_PER_QUERY = 10      # DDG results per search query
_URLS_PER_ROUND = 10          # max URLs to fetch per round
_MAX_ROUNDS = 3               # search → fetch rounds
_INITIAL_SUB_QUESTIONS = 5    # sub-questions on first decomposition
_FOLLOWUP_QUERIES = 3         # follow-up queries per gap round
_SOURCE_TEXT_LIMIT = 4000     # chars kept per fetched page


def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# ─── Helpers ────────────────────────────────────────────────────────────────

def _parse_json_array(text: str) -> list:
    """Extract the first JSON array from LLM output."""
    m = re.search(r"\[.*\]", text, re.DOTALL)
    return json.loads(m.group()) if m else []


async def _decompose_query(query: str, n: int = _INITIAL_SUB_QUESTIONS) -> List[Dict[str, str]]:
    llm = get_llm(temperature=0.3)
    prompt = (
        f"You are a research query decomposer. Break this query into {n} targeted, "
        "diverse sub-questions that together fully cover every angle of the topic.\n\n"
        f"Query: {query}\n\n"
        "Return ONLY a JSON array:\n"
        '[{"sub_question": "...", "search_query": "..."}]\n\n'
        "Make each search_query short and optimised for web search engines. "
        "Cover different perspectives, time periods, and aspects."
    )
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
    # ensure all tasks finished
    await asyncio.gather(*tasks, return_exceptions=True)
    # extend caller's list
    all_sources.extend(fetched)


async def _identify_gaps(
    query: str,
    sources_summary: str,
    previous_queries: List[str],
) -> List[Dict[str, str]]:
    llm = get_llm(temperature=0.3)
    prompt = (
        "You are a research gap analyst. Based on the original query and source "
        "summaries so far, identify 3-4 information gaps or angles not yet covered.\n\n"
        f"Original query: {query}\n\n"
        f"Sources collected so far (titles/domains):\n{sources_summary}\n\n"
        f"Previous search queries used (do NOT repeat):\n{json.dumps(previous_queries)}\n\n"
        "Return ONLY a JSON array of NEW follow-up search queries:\n"
        '[{"sub_question": "...", "search_query": "..."}]\n\n'
        "Return an empty array [] ONLY if you are fully confident every angle is covered."
    )
    resp = await llm.ainvoke(prompt)
    raw = getattr(resp, "content", str(resp)).strip()
    try:
        return _parse_json_array(raw)
    except Exception:
        return []


def _build_source_context(sources: List[Dict], max_sources: int = 30) -> str:
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

        # ── Round 0: decompose query ──
        yield _sse("research_phase", {
            "phase": "searching",
            "label": "Preparing search queries…",
        })
        sub_questions = await _decompose_query(query, _INITIAL_SUB_QUESTIONS)
        current_queries = sub_questions
        all_queries_used.extend(sq["search_query"] for sq in sub_questions)

        yield _sse("research_phase", {
            "phase": "searching",
            "label": f"Searching across {len(sub_questions)} topics…",
            "queries": [sq["search_query"] for sq in sub_questions],
        })

        # ── Search → Fetch rounds ──
        for rnd in range(1, _MAX_ROUNDS + 1):
            # Search
            yield _sse("research_phase", {
                "phase": "searching",
                "label": f"Looking up {len(current_queries)} queries…",
                "queries": [sq["search_query"] for sq in current_queries],
            })
            new_results = await _search_batch(current_queries, seen_urls)

            if not new_results and not all_sources:
                yield _sse("token", {"content": "No search results found. Try rephrasing your query."})
                yield _sse("done", {})
                return

            if not new_results:
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

            # Check if we have enough sources or need more rounds
            if len(all_sources) >= 30 or rnd >= _MAX_ROUNDS:
                break

            # Find gaps for next round
            yield _sse("research_phase", {
                "phase": "synthesizing",
                "label": "Checking what else to look up…",
            })
            sources_summary = "\n".join(
                f"- {s.get('title', '?')} ({s.get('domain', '?')})"
                for s in all_sources[-20:]
            )
            follow_ups = await _identify_gaps(query, sources_summary, all_queries_used)
            if not follow_ups:
                break

            current_queries = follow_ups[:_FOLLOWUP_QUERIES]
            all_queries_used.extend(sq["search_query"] for sq in current_queries)

            yield _sse("research_phase", {
                "phase": "searching",
                "label": f"Exploring {len(current_queries)} more angles…",
                "queries": [sq["search_query"] for sq in current_queries],
            })

        # ── Write the detailed report via LLM streaming ──
        yield _sse("research_phase", {
            "phase": "writing",
            "label": f"Writing detailed analysis from {len(all_sources)} sources…",
        })

        source_ctx = _build_source_context(all_sources, max_sources=30)
        llm = get_llm(temperature=0.3)

        report_prompt = (
            "You are a world-class research analyst. You have been given content from "
            f"{len(all_sources)} real web sources about the following topic.\n\n"
            f"RESEARCH TOPIC: {query}\n\n"
            f"SOURCES:\n{source_ctx}\n\n"
            "YOUR TASK: Write a **very detailed, comprehensive, in-depth research report**.\n\n"
            "RULES:\n"
            "- This is deep research. DO NOT write a summary. Write a FULL, DETAILED analysis.\n"
            "- Cover every aspect, sub-topic, perspective, and nuance found in the sources.\n"
            "- Use markdown headers (##, ###) to organize sections clearly.\n"
            "- Include specific data, numbers, statistics, names, dates from the sources.\n"
            "- The report should be at least 2000-3000 words. Be thorough.\n"
            "- Include: introduction, detailed analysis of each angle, comparisons, "
            "real-world implications, expert opinions found in sources, conclusion.\n"
            "- DO NOT start with 'Here is' or 'I found'. Write directly as a report.\n"
            "- DO NOT include any URLs, hyperlinks, or web addresses anywhere in the report.\n"
            "- DO NOT include any inline citations, bracketed numbers (like [1], [2]), or source references.\n"
            "- DO NOT include a 'Sources' or 'References' section at the end.\n"
            "- Focus purely on the content and analysis, providing a clean, professional report.\n"
        )

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
