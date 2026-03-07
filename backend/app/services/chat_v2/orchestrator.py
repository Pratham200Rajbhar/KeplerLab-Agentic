"""Chat V2 — Conversation orchestrator.

Coordinates:
1. Determine capability via router_logic
2. Run tool if needed
3. Build LLM context
4. Stream LLM tokens
5. Return accumulated response

This is the heart of the new pipeline.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, AsyncIterator, Dict, List, Optional

from app.core.config import settings
from app.services.llm_service.llm import get_llm, extract_chunk_content

from . import context_builder, message_store
from .router_logic import route_capability
from .schemas import Capability, ToolResult
from .streaming import (
    sse_token,
    sse_error,
    sse_done,
    sse_blocks,
    sse_meta,
)

logger = logging.getLogger(__name__)


async def run(
    message: str,
    notebook_id: str,
    user_id: str,
    session_id: str,
    material_ids: List[str],
    intent_override: Optional[str] = None,
) -> AsyncIterator[str]:
    """Execute the full chat pipeline as an async SSE stream.

    Flow:
        1. Route to capability
        2. Execute tool (if needed)
        3. Build LLM context
        4. Stream LLM tokens
        5. Persist and return

    Yields:
        SSE-formatted event strings for StreamingResponse.
    """
    start_time = time.time()
    capability = route_capability(message, material_ids, intent_override)

    # ── AGENT: delegate entirely to agent pipeline ────────────
    if capability == Capability.AGENT:
        async for event in _handle_agent(message, notebook_id, user_id, session_id, material_ids, start_time):
            yield event
        return

    # ── WEB_RESEARCH: delegate to research pipeline ───────────
    if capability == Capability.WEB_RESEARCH:
        async for event in _handle_research(message, notebook_id, user_id, session_id, start_time):
            yield event
        return

    # ── CODE_EXECUTION: generate code (no LLM synthesis) ──────
    if capability == Capability.CODE_EXECUTION:
        async for event in _handle_code_execution(message, notebook_id, user_id, session_id, material_ids, start_time):
            yield event
        return

    # ── RAG / WEB_SEARCH / NORMAL_CHAT ────────────────────────
    tool_result: Optional[ToolResult] = None

    # Run tool if needed
    if capability == Capability.RAG:
        async for item in _run_rag_tool(message, material_ids, user_id, notebook_id):
            if isinstance(item, ToolResult):
                tool_result = item
            else:
                yield item  # SSE events

    elif capability == Capability.WEB_SEARCH:
        async for item in _run_web_search_tool(message, user_id):
            if isinstance(item, ToolResult):
                tool_result = item
            else:
                yield item

    # Handle empty RAG results
    if capability == Capability.RAG and tool_result and tool_result.metadata.get("empty"):
        msg = (
            "I couldn't find relevant information in your selected materials "
            "for that question. Try rephrasing your query or selecting different materials."
        )
        yield sse_token(msg)
        elapsed = round(time.time() - start_time, 2)
        yield sse_meta({"intent": capability.value, "chunks_used": 0, "elapsed": elapsed})
        yield sse_done({"elapsed": elapsed})

        # Persist the "no results" response
        await _persist(notebook_id, user_id, session_id, message, msg, {"intent": capability.value, "chunks_used": 0})
        return

    # ── Build LLM context ─────────────────────────────────────
    history = await message_store.get_history(notebook_id, user_id, session_id)

    if capability == Capability.RAG and tool_result and tool_result.content:
        # RAG: use the full RAG prompt template
        messages = context_builder.build_messages(
            user_message=message,
            history=history,
            rag_context=tool_result.content,
        )
    elif capability == Capability.WEB_SEARCH and tool_result and tool_result.content:
        # Web search: inject search results as tool context
        synth_prompt = (
            f"Based on these web search results, answer the user's question. "
            f"Cite sources inline with [1] [2] [3] format.\n\n"
            f"Search Results:\n{tool_result.content}\n\n"
            f"User Question: {message}\n\n"
            f"Provide a clear, comprehensive answer with inline citations:"
        )
        messages = [{"role": "user", "content": synth_prompt}]
    else:
        # Normal chat: no tool context
        messages = context_builder.build_messages(
            user_message=message,
            history=history,
        )

    # ── Stream LLM tokens ─────────────────────────────────────
    try:
        llm = get_llm(temperature=0.3 if capability == Capability.WEB_SEARCH else None)
        full_response: List[str] = []

        # Convert messages to prompt string or pass as-is depending on provider
        prompt = _messages_to_prompt(messages)

        async for chunk in llm.astream(prompt):
            content = extract_chunk_content(chunk)
            if content:
                full_response.append(content)
                yield sse_token(content)

        answer = "".join(full_response).strip()

        # Citation validation for RAG
        if capability == Capability.RAG and tool_result:
            chunks_used = tool_result.metadata.get("chunks_used", 0)
            if chunks_used > 0:
                try:
                    from app.services.rag.citation_validator import validate_citations
                    validation = validate_citations(response=answer, num_sources=chunks_used, strict=True)
                    if not validation["is_valid"]:
                        logger.warning("Citation validation failed: %s", validation.get("error_message"))
                except Exception:
                    pass

        # Emit metadata
        elapsed = round(time.time() - start_time, 2)
        meta = _build_meta(capability, tool_result, elapsed)
        yield sse_meta(meta)

        # Persist
        blocks = await _persist(notebook_id, user_id, session_id, message, answer, meta)
        if blocks:
            yield sse_blocks(blocks)

        yield sse_done({"elapsed": elapsed, **meta})

    except Exception as exc:
        logger.error("LLM streaming failed: %s", exc)
        yield sse_error(str(exc))
        yield sse_done({"elapsed": round(time.time() - start_time, 2)})


# ── Tool runners (yield SSE + ToolResult) ─────────────────────


async def _run_rag_tool(message, material_ids, user_id, notebook_id):
    from app.services.tools.rag_tool import execute
    async for item in execute(message, material_ids, user_id, notebook_id):
        yield item


async def _run_web_search_tool(message, user_id):
    from app.services.tools.web_search_tool import execute
    async for item in execute(message, user_id):
        yield item


# ── Delegate handlers ─────────────────────────────────────────


async def _handle_agent(message, notebook_id, user_id, session_id, material_ids, start_time):
    """Delegate to the existing agent pipeline with persistence."""
    from app.services.agent.pipeline import stream_agent

    full_response: List[str] = []
    tools_used: List[str] = []
    steps_count = 0

    try:
        async for event in stream_agent(
            message=message,
            notebook_id=notebook_id,
            material_ids=material_ids,
            session_id=session_id,
            user_id=user_id,
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
                elif event.startswith("event: done\n"):
                    for line in event.split("\n"):
                        if line.startswith("data: "):
                            try:
                                payload = json.loads(line[len("data: "):])
                                tools_used = payload.get("tools_used", [])
                                steps_count = payload.get("steps", 0)
                            except json.JSONDecodeError:
                                pass

        complete = "".join(full_response)
        if complete:
            meta = {"intent": "AGENT", "tools_used": tools_used, "steps_count": steps_count}
            blocks = await _persist(notebook_id, user_id, session_id, message, complete, meta)
            if blocks:
                yield sse_blocks(blocks)

            elapsed = time.time() - start_time
            await message_store.log_agent_execution(user_id, notebook_id, meta, elapsed)

    except Exception as exc:
        logger.error("Agent pipeline failed: %s", exc)
        yield sse_error(str(exc))


async def _handle_research(message, notebook_id, user_id, session_id, start_time):
    """Delegate to research pipeline with persistence."""
    from app.services.tools.research_tool import execute

    full_response: List[str] = []
    tool_result: Optional[ToolResult] = None

    async for item in execute(message, user_id, notebook_id, session_id):
        if isinstance(item, ToolResult):
            tool_result = item
        else:
            yield item

    if tool_result and tool_result.content:
        meta = {
            "intent": "WEB_RESEARCH",
            "sources_count": tool_result.metadata.get("sources_count", 0),
        }
        blocks = await _persist(notebook_id, user_id, session_id, message, tool_result.content, meta)
        if blocks:
            yield sse_blocks(blocks)

    elapsed = round(time.time() - start_time, 2)
    yield sse_done({"elapsed": elapsed})


async def _handle_code_execution(message, notebook_id, user_id, session_id, material_ids, start_time):
    """Generate code via python_tool, persist, and emit events."""
    from app.services.tools.python_tool import execute

    tool_result: Optional[ToolResult] = None

    async for item in execute(message, material_ids, user_id, notebook_id, session_id):
        if isinstance(item, ToolResult):
            tool_result = item
        else:
            yield item

    if tool_result:
        answer = tool_result.content or "Code generated."
        meta = {
            "intent": "CODE_EXECUTION",
            "original_code": tool_result.metadata.get("code", ""),
            "phase": tool_result.metadata.get("phase", "generated"),
        }
        await _persist(notebook_id, user_id, session_id, message, answer, meta)

    elapsed = round(time.time() - start_time, 2)
    yield sse_done({"intent": "CODE_EXECUTION", "elapsed": elapsed})


# ── Helpers ───────────────────────────────────────────────────


def _messages_to_prompt(messages: List[Dict[str, str]]) -> str:
    """Convert message list to a single prompt string.

    LangChain's ChatOllama, ChatGoogleGenerativeAI, etc. accept either
    a string prompt or a list of BaseMessage objects. We use a string
    here for maximum provider compatibility.
    """
    parts: List[str] = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            parts.append(content)
        elif role == "user":
            parts.append(content)
        elif role == "assistant":
            parts.append(f"Assistant: {content}")
    return "\n\n".join(parts)


def _build_meta(
    capability: Capability,
    tool_result: Optional[ToolResult],
    elapsed: float,
) -> Dict[str, Any]:
    """Build metadata dict for the response."""
    meta: Dict[str, Any] = {"intent": capability.value, "elapsed": elapsed}
    if tool_result:
        if "chunks_used" in tool_result.metadata:
            meta["chunks_used"] = tool_result.metadata["chunks_used"]
        if "sources" in tool_result.metadata:
            meta["sources"] = tool_result.metadata["sources"]
        if "queries" in tool_result.metadata:
            meta["queries_used"] = tool_result.metadata["queries"]
    return meta


async def _persist(
    notebook_id: str,
    user_id: str,
    session_id: str,
    user_message: str,
    assistant_answer: str,
    agent_meta: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Save user + assistant messages and response blocks. Returns blocks."""
    try:
        # Save user message
        await message_store.save_user_message(notebook_id, user_id, session_id, user_message)

        # Save assistant message
        msg_id = await message_store.save_assistant_message(
            notebook_id, user_id, session_id, assistant_answer, agent_meta
        )

        # Save response blocks
        blocks = await message_store.save_response_blocks(msg_id, assistant_answer)
        return blocks
    except Exception as exc:
        logger.error("Persistence failed: %s", exc)
        return []
