from __future__ import annotations

import logging
from typing import AsyncIterator, Optional

from app.services.chat_v2.schemas import ToolResult

from .memory import AgentMemory
from .state import AgentState, StepStatus
from .tools_registry import get_available_tools

logger = logging.getLogger(__name__)


async def execute_tool(
    tool_name: str,
    state: AgentState,
    memory: AgentMemory,
) -> AsyncIterator[str | ToolResult]:
    """Run the selected tool and yield SSE events + ToolResult."""
    has_materials = bool(state.material_ids)
    available = get_available_tools(has_materials)

    spec = available.get(tool_name)
    if not spec:
        logger.error("Tool '%s' not found in registry", tool_name)
        yield ToolResult(
            tool_name=tool_name,
            success=False,
            content=f"Tool '{tool_name}' is not available.",
            metadata={"error": "tool_not_found"},
        )
        return

    step = state.current_step
    query = step.description if step else state.goal

    # Enrich query with prior observations so later steps see earlier results
    # (e.g. step 2 python_auto sees step 1 web_search context)
    if state.observations and state.current_step_index > 0:
        prev_context = state.summary_of_observations(max_chars=6000)
        query = (
            f"{query}\n\n"
            f"── Context from previous steps ──\n"
            f"{prev_context}"
        )

    # Inject multi-turn conversation history for generative/code tools only.
    # Do NOT inject into search tools (web_search, rag) — that would corrupt the search query.
    _HISTORY_AWARE_TOOLS = {"python_auto", "research"}
    if tool_name in _HISTORY_AWARE_TOOLS and memory.chat_history:
        chat_ctx = memory.format_chat_history(max_turns=8, max_chars_per_msg=300)
        query = f"{query}\n\n── Prior conversation ──\n{chat_ctx}"

    kwargs = {
        "query": query,
        "user_id": state.user_id,
        "notebook_id": state.notebook_id,
        "session_id": state.session_id,
        "material_ids": state.material_ids,
    }

    state.total_tool_calls += 1

    try:
        async for item in spec.execute_fn(**kwargs):
            yield item
    except Exception as exc:
        logger.error("Tool '%s' raised exception: %s", tool_name, exc)
        yield ToolResult(
            tool_name=tool_name,
            success=False,
            content=f"Tool execution failed: {exc}",
            metadata={"error": str(exc)},
        )


def process_tool_result(
    tool_result: ToolResult,
    state: AgentState,
    memory: AgentMemory,
):
    """Store observations and artifacts from a tool result into memory."""
    memory.add_observation(
        tool_name=tool_result.tool_name,
        content=tool_result.content[:4000] if tool_result.content else "",
        metadata=tool_result.metadata,
    )

    if tool_result.tool_name == "rag" and tool_result.content:
        memory.set_rag_context(tool_result.content)

    if tool_result.tool_name == "web_search" and tool_result.content:
        memory.set_web_context(tool_result.content)
        sources = tool_result.metadata.get("sources", [])
        for src in sources:
            memory.add_source(src)

    if tool_result.tool_name in ("python", "python_auto"):
        code = tool_result.metadata.get("code", "")
        if code:
            memory.add_code_output(code)

    if tool_result.tool_name == "research" and tool_result.content:
        memory.set_web_context(tool_result.content)
        citations = tool_result.metadata.get("citations", [])
        for c in citations:
            memory.add_source(c)

    for artifact in tool_result.artifacts:
        memory.add_artifact(artifact)

    if tool_result.success:
        state.mark_current(StepStatus.COMPLETED, result=tool_result.content[:500] if tool_result.content else "done")
    else:
        state.mark_current(StepStatus.FAILED, error=tool_result.metadata.get("error", "unknown"))
