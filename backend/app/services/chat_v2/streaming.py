from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

def sse(event_type: str, data: Any) -> str:
    if isinstance(data, str):
        json_data = json.dumps({"content": data})
    else:
        json_data = json.dumps(data, default=str)
    return f"event: {event_type}\ndata: {json_data}\n\n"

def sse_token(content: str) -> str:
    return sse("token", {"content": content})

def sse_tool_start(tool: str, label: Optional[str] = None) -> str:
    data: Dict[str, Any] = {"tool": tool}
    if label:
        data["label"] = label
    return sse("tool_start", data)

def sse_tool_result(tool: str, success: bool = True, summary: Optional[str] = None) -> str:
    data: Dict[str, Any] = {"tool": tool, "success": success}
    if summary:
        data["summary"] = summary
    return sse("tool_result", data)

def sse_error(error: str) -> str:
    return sse("error", {"error": error})

def sse_done(metadata: Optional[Dict[str, Any]] = None) -> str:
    return sse("done", metadata or {})

def sse_blocks(blocks: List[Dict[str, Any]]) -> str:
    return sse("blocks", {"blocks": blocks})

def sse_meta(metadata: Dict[str, Any]) -> str:
    return sse("meta", metadata)

def sse_code_block(code: str, language: str = "python", session_id: str = "") -> str:
    return sse("code_block", {"code": code, "language": language, "session_id": session_id})

def sse_web_sources(sources: List[Dict[str, Any]]) -> str:
    return sse("web_sources", {"sources": sources})

def sse_web_search_update(
    status: str,
    queries: Optional[List[str]] = None,
    scraping_urls: Optional[List[Dict[str, str]]] = None,
) -> str:
    data: Dict[str, Any] = {"status": status}
    if queries is not None:
        data["queries"] = queries
    if scraping_urls is not None:
        data["scrapingUrls"] = scraping_urls
    return sse("web_search_update", data)

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}
