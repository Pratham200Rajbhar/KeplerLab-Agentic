"""Chat V2 — SSE streaming utilities.

Provides consistent Server-Sent Event formatting for all streaming responses.
Supported events: token, tool_start, tool_result, error, done, blocks, meta.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


def sse(event_type: str, data: Any) -> str:
    """Format data as an SSE event string.

    Args:
        event_type: Event name (token, tool_start, tool_result, error, done, etc.).
        data: Payload — dict or string (will be JSON-encoded).

    Returns:
        SSE-formatted string ready to yield from a StreamingResponse.
    """
    if isinstance(data, str):
        json_data = json.dumps({"content": data})
    else:
        json_data = json.dumps(data, default=str)
    return f"event: {event_type}\ndata: {json_data}\n\n"


# ── Convenience helpers ───────────────────────────────────────


def sse_token(content: str) -> str:
    """Emit a token (text chunk) event."""
    return sse("token", {"content": content})


def sse_tool_start(tool: str, label: Optional[str] = None) -> str:
    """Emit a tool_start event."""
    data: Dict[str, Any] = {"tool": tool}
    if label:
        data["label"] = label
    return sse("tool_start", data)


def sse_tool_result(tool: str, success: bool = True, summary: Optional[str] = None) -> str:
    """Emit a tool_result event."""
    data: Dict[str, Any] = {"tool": tool, "success": success}
    if summary:
        data["summary"] = summary
    return sse("tool_result", data)


def sse_error(error: str) -> str:
    """Emit an error event."""
    return sse("error", {"error": error})


def sse_done(metadata: Optional[Dict[str, Any]] = None) -> str:
    """Emit a done event signaling stream completion."""
    return sse("done", metadata or {})


def sse_blocks(blocks: List[Dict[str, Any]]) -> str:
    """Emit response blocks for the frontend."""
    return sse("blocks", {"blocks": blocks})


def sse_meta(metadata: Dict[str, Any]) -> str:
    """Emit metadata about the response."""
    return sse("meta", metadata)


def sse_code_block(code: str, language: str = "python", session_id: str = "") -> str:
    """Emit a code_block event for code review."""
    return sse("code_block", {"code": code, "language": language, "session_id": session_id})


def sse_web_sources(sources: List[Dict[str, Any]]) -> str:
    """Emit web search sources."""
    return sse("web_sources", {"sources": sources})


# ── SSE response headers ─────────────────────────────────────

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}
