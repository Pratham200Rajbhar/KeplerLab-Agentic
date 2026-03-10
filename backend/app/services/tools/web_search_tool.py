import asyncio
import json
import logging
from typing import AsyncIterator

from app.services.chat_v2.schemas import ToolResult
from app.services.chat_v2.streaming import (
    sse_tool_start,
    sse_tool_result,
    sse_web_sources,
    sse_web_search_update,
)

logger = logging.getLogger(__name__)

async def execute(
    query: str,
    user_id: str,
) -> AsyncIterator[str | ToolResult]:
    yield sse_tool_start("web_search", label="Searching the web…")
    
    search_state = {
        "status": "searching",
        "queries": [],
        "scraping_urls": []
    }

    try:
        from app.services.llm_service.llm import get_llm
        llm = get_llm(temperature=0)
        
        prompt = (
            "Generate 2-3 short, distinct web search queries to find the most up-to-date information "
            "to answer: {query}\n"
            "Return ONLY a JSON list of strings."
        ).format(query=query)
        
        try:
            resp = await llm.ainvoke(prompt)
            content = getattr(resp, "content", str(resp)).strip()
            if "```" in content:
                content = content.split("```")[1].strip()
                if content.startswith("json"):
                    content = content[4:].strip()
            
            queries = json.loads(content)
            if not isinstance(queries, list):
                queries = [query]
        except Exception as e:
            logger.warning("LLM query gen failed: %s", e)
            queries = [query]

        search_state["queries"] = queries
        yield sse_web_search_update(**search_state)

        from app.core.web_search import ddg_search, fetch_url_content
        
        all_results = []
        seen_urls = set()

        # Run all search queries in parallel
        async def _search_one(q):
            try:
                return await ddg_search(q, max_results=5)
            except Exception as e:
                logger.error("DDG search error for %s: %s", q, e)
                return []

        batch = await asyncio.gather(*(_search_one(q) for q in queries))
        for hits in batch:
            for h in hits:
                url = h.get("url")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append({
                        "title": h.get("title", ""),
                        "url": url,
                        "snippet": h.get("snippet", ""),
                    })

        if not all_results:
            raise Exception("No search results found.")

        search_state["status"] = "reading"
        to_scrape = all_results[:5]
        search_state["scraping_urls"] = [{"url": r["url"], "status": "fetching"} for r in to_scrape]
        yield sse_web_search_update(**search_state)

        scraped_data = []

        async def scrape_one(index, item):
            url = item["url"]
            try:
                fetched = await fetch_url_content(url)
                if fetched and fetched.get("text"):
                    search_state["scraping_urls"][index]["status"] = "done"
                    scraped_data.append({
                        "title": fetched.get("title") or item["title"],
                        "url": url,
                        "content": fetched["text"][:4000],
                        "snippet": item["snippet"]
                    })
                else:
                    search_state["scraping_urls"][index]["status"] = "failed"
            except Exception:
                search_state["scraping_urls"][index]["status"] = "failed"

        # Scrape URLs in parallel for better performance
        await asyncio.gather(*(scrape_one(i, item) for i, item in enumerate(to_scrape)))
        yield sse_web_search_update(**search_state)

        scraped_data = scraped_data[:5]
        if not scraped_data:
            scraped_data = [{
                "title": r["title"], "url": r["url"], 
                "content": r["snippet"], "snippet": r["snippet"]
            } for r in to_scrape]

        context = "\n\n".join([
            f"Source [{i+1}]: {s['title']}\nURL: {s['url']}\nContent: {s['content']}"
            for i, s in enumerate(scraped_data)
        ])

        sources = [
            {"title": s["title"], "url": s["url"], "index": i + 1}
            for i, s in enumerate(scraped_data)
        ]

        yield sse_web_sources(sources)
        yield sse_tool_result("web_search", True, f"Found {len(sources)} sources")
        
        yield ToolResult(
            tool_name="web_search",
            success=True,
            content=context,
            metadata={"queries": queries, "sources": sources}
        )

    except Exception as e:
        logger.exception("Web search tool failed")
        yield sse_tool_result("web_search", False, str(e))
        yield ToolResult(
            tool_name="web_search",
            success=False,
            content=f"Error during web search: {str(e)}",
            metadata={"error": str(e)}
        )
