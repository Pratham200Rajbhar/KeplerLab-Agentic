"""
/web tool — iterative web search with answer-quality checking.

Pipeline (like Perplexity):
  1. Generate 4-5 diverse queries from the user's question
  2. Search + scrape up to 10 URLs in parallel → Round 1
  3. Ask LLM: "Is this fully answered? What's missing?"
  4. If incomplete → generate follow-up queries → Round 2 (up to 3 rounds total)
  5. Stream the final synthesized answer with inline citations
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncIterator, Dict, List, Optional

from app.services.chat_v2.schemas import ToolResult
from app.services.chat_v2.streaming import (
    sse_tool_start,
    sse_tool_result,
    sse_web_sources,
    sse_web_search_update,
)

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────
_MAX_ROUNDS = 3          # max iterative search rounds
_URLS_PER_ROUND = 10     # URLs to scrape per round
_DDG_RESULTS = 8         # DDG results requested per query
_CONTENT_LIMIT = 5000    # chars kept per scraped page for synthesis
_COMPLETENESS_THRESHOLD = 80   # confidence % above which we stop iterating


# ── Helper: generate search queries ───────────────────────────────────────

async def _generate_queries(question: str) -> List[str]:
    """Ask LLM to produce 4-5 diverse, targeted search queries."""
    from app.services.llm_service.llm import get_llm
    llm = get_llm(temperature=0)
    prompt = (
        f"Generate 4-5 short, distinct web search queries to comprehensively answer:\n"
        f'"{question}"\n\n'
        "Make them diverse — cover different angles, time frames, and specifics. "
        "Return ONLY a JSON array of strings, no other text."
    )
    try:
        resp = await llm.ainvoke(prompt)
        raw = getattr(resp, "content", str(resp)).strip()
        # strip markdown fences if present
        if "```" in raw:
            raw = raw.split("```")[1].strip()
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()
        queries = json.loads(raw)
        if isinstance(queries, list) and queries:
            return [str(q) for q in queries[:5]]
    except Exception as exc:
        logger.warning("[web] Query generation failed: %s", exc)
    return [question]


# ── Helper: search + scrape a batch of queries ────────────────────────────

async def _search_and_scrape(
    queries: List[str],
    seen_urls: set,
) -> List[Dict]:
    """Run queries in parallel, scrape up to _URLS_PER_ROUND unique new URLs."""
    from app.core.web_search import ddg_search, fetch_url_content

    # Search all queries in parallel
    async def _one_search(q: str) -> List[Dict]:
        try:
            return await ddg_search(q, max_results=_DDG_RESULTS)
        except Exception as exc:
            logger.warning("[web] DDG error for %r: %s", q, exc)
            return []

    batches = await asyncio.gather(*(_one_search(q) for q in queries))

    # Collect new unseen URLs preserving order
    candidate_urls: List[Dict] = []
    for batch in batches:
        for hit in batch:
            url = hit.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                candidate_urls.append(hit)

    to_scrape = candidate_urls[:_URLS_PER_ROUND]

    # Scrape all in parallel
    async def _one_scrape(hit: Dict) -> Optional[Dict]:
        url = hit["url"]
        try:
            fetched = await fetch_url_content(url)
            if fetched and fetched.get("text"):
                return {
                    "title": fetched.get("title") or hit.get("title", ""),
                    "url": url,
                    "domain": fetched.get("domain", ""),
                    "content": fetched["text"][:_CONTENT_LIMIT],
                    "snippet": hit.get("snippet", ""),
                }
        except Exception:
            pass
        # Fallback to snippet if scraping fails
        if hit.get("snippet"):
            return {
                "title": hit.get("title", ""),
                "url": url,
                "domain": "",
                "content": hit["snippet"],
                "snippet": hit["snippet"],
            }
        return None

    results = await asyncio.gather(*(_one_scrape(h) for h in to_scrape))
    return [r for r in results if r is not None]


# ── Helper: check answer completeness ─────────────────────────────────────

async def _check_completeness(question: str, scraped: List[Dict]) -> Dict:
    """
    Ask the LLM if the current scraped content fully answers the question.
    Returns dict with: is_complete, confidence, missing_aspects, follow_up_queries
    """
    from app.services.llm_service.llm import get_llm
    from app.prompts import get_web_completeness_prompt

    # Build a compact context for the completeness check (2000 chars per source)
    context_parts = []
    for i, s in enumerate(scraped[:8]):
        context_parts.append(
            f"[{i+1}] {s['title']} ({s.get('domain', s['url'])})\n{s['content'][:2000]}"
        )
    context = "\n\n".join(context_parts)

    llm = get_llm(temperature=0)
    prompt = get_web_completeness_prompt(question=question, search_results=context)

    try:
        resp = await llm.ainvoke(prompt)
        raw = getattr(resp, "content", str(resp)).strip()
        if "```" in raw:
            raw = raw.split("```")[1].strip()
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()
        data = json.loads(raw)
        return {
            "is_complete": bool(data.get("is_complete", False)),
            "confidence": int(data.get("confidence", 0)),
            "missing_aspects": data.get("missing_aspects", []),
            "follow_up_queries": data.get("follow_up_queries", []),
        }
    except Exception as exc:
        logger.warning("[web] Completeness check failed: %s", exc)
        # If check fails, assume incomplete to trigger another round
        return {
            "is_complete": False,
            "confidence": 0,
            "missing_aspects": [],
            "follow_up_queries": [question],
        }


# ── Main tool entry point ─────────────────────────────────────────────────

async def execute(
    query: str,
    user_id: str,
    step_index: Optional[int] = None,
) -> AsyncIterator[str | ToolResult]:
    yield sse_tool_start("web_search", label="Searching the web…")

    seen_urls: set = set()
    all_scraped: List[Dict] = []
    all_queries_used: List[str] = []

    search_state = {
        "status": "searching",
        "queries": [],
        "scraping_urls": [],
    }

    try:
        # ── Round 0: generate initial queries ─────────────────────────────
        queries = await _generate_queries(query)
        all_queries_used.extend(queries)
        search_state["queries"] = queries
        yield sse_web_search_update(**search_state)

        # ── Iterative search rounds ────────────────────────────────────────
        for rnd in range(1, _MAX_ROUNDS + 1):
            round_label = f"Round {rnd}: reading {len(queries)} queries…" if rnd > 1 else f"Searching {len(queries)} queries…"
            search_state["status"] = "reading"
            search_state["scraping_urls"] = [{"url": q, "status": "fetching"} for q in queries]
            yield sse_web_search_update(**search_state)

            logger.info("[web] Round %d — queries: %s", rnd, queries)

            scraped = await _search_and_scrape(queries, seen_urls)
            all_scraped.extend(scraped)

            logger.info("[web] Round %d — scraped %d pages, total %d", rnd, len(scraped), len(all_scraped))

            # Update scraping status
            search_state["scraping_urls"] = [{"url": s["url"], "status": "done"} for s in scraped]
            yield sse_web_search_update(**search_state)

            if not all_scraped:
                break

            # Don't check completeness on last round — just synthesize
            if rnd >= _MAX_ROUNDS:
                break

            # ── Completeness check ─────────────────────────────────────────
            search_state["status"] = "analyzing"
            yield sse_web_search_update(**search_state)

            check = await _check_completeness(query, all_scraped)
            logger.info(
                "[web] Completeness check round %d — complete=%s confidence=%d%% missing=%s",
                rnd, check["is_complete"], check["confidence"], check["missing_aspects"]
            )

            if check["is_complete"] or check["confidence"] >= _COMPLETENESS_THRESHOLD:
                logger.info("[web] Answer deemed complete at round %d (confidence=%d%%)", rnd, check["confidence"])
                break

            # Not complete — prepare follow-up queries for next round
            follow_ups = check.get("follow_up_queries", [])
            if not follow_ups:
                break

            queries = follow_ups[:4]
            all_queries_used.extend(queries)
            search_state["queries"] = queries
            search_state["status"] = "searching"
            yield sse_web_search_update(**search_state)
            logger.info("[web] Needs more info — follow-up queries: %s", queries)

        # ── Build source list ──────────────────────────────────────────────
        if not all_scraped:
            raise Exception("No content could be retrieved from the web.")

        sources = [
            {"title": s["title"], "url": s["url"], "index": i + 1}
            for i, s in enumerate(all_scraped)
        ]
        yield sse_web_sources(sources)

        # ── Build context for synthesis ────────────────────────────────────
        context = "\n\n".join([
            f"Source [{i+1}]: {s['title']}\nURL: {s['url']}\nContent: {s['content']}"
            for i, s in enumerate(all_scraped)
        ])

        yield sse_tool_result("web_search", True, f"Found {len(sources)} sources across {min(_MAX_ROUNDS, len(all_queries_used))} search rounds", step_index=step_index)

        yield ToolResult(
            tool_name="web_search",
            success=True,
            content=context,
            metadata={
                "queries": all_queries_used,
                "sources": sources,
                "rounds": len([q for q in all_queries_used]),
            },
        )

    except Exception as exc:
        logger.exception("[web] Web search tool failed")
        yield sse_tool_result("web_search", False, str(exc), step_index=step_index)
        yield ToolResult(
            tool_name="web_search",
            success=False,
            content=f"Web search failed: {exc}",
            metadata={"error": str(exc)},
        )
