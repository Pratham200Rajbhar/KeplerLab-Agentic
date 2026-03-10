from __future__ import annotations

import json
import logging
from typing import AsyncIterator, List

from app.services.chat_v2.schemas import ToolResult
from app.services.chat_v2.streaming import sse_tool_start, sse_tool_result

logger = logging.getLogger(__name__)

async def execute(
    query: str,
    user_id: str,
    notebook_id: str,
    session_id: str,
) -> AsyncIterator[str | ToolResult]:
    yield sse_tool_start("research", label="Starting deep research…")

    try:
        from app.services.research.pipeline import stream_research

        full_response: List[str] = []
        citations: list = []

        async for event in stream_research(
            query=query,
            user_id=user_id,
            notebook_id=notebook_id,
            session_id=session_id,
        ):
            yield event

            if isinstance(event, str):
                if event.startswith("event: token\n"):
                    for line in event.split("\n"):
                        if line.startswith("data: "):
                            try:
                                payload = json.loads(line[len("data: "):])
                                full_response.append(payload.get("content", ""))
                            except json.JSONDecodeError:
                                pass
                elif event.startswith("event: citations\n"):
                    for line in event.split("\n"):
                        if line.startswith("data: "):
                            try:
                                payload = json.loads(line[len("data: "):])
                                citations = payload.get("citations", [])
                            except json.JSONDecodeError:
                                pass

        complete = "".join(full_response)
        yield sse_tool_result("research", success=True, summary=f"Research complete — {len(citations)} sources")

        yield ToolResult(
            tool_name="research",
            success=True,
            content=complete,
            metadata={"intent": "WEB_RESEARCH", "sources_count": len(citations), "citations": citations},
        )

    except Exception as exc:
        logger.error("Research pipeline failed: %s", exc)
        yield sse_tool_result("research", success=False, summary="Research failed")
        yield ToolResult(
            tool_name="research",
            success=False,
            content="",
            metadata={"error": str(exc)},
        )
