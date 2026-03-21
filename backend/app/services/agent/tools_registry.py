from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union

from app.services.chat_v2.schemas import ToolResult

logger = logging.getLogger(__name__)


class ToolSpec:
    """Describes a tool the agent can use."""

    def __init__(
        self,
        name: str,
        description: str,
        execute_fn: Callable[..., AsyncIterator[Union[str, ToolResult]]],
        required_params: Optional[List[str]] = None,
    ):
        self.name = name
        self.description = description
        self.execute_fn = execute_fn
        self.required_params = required_params or []


async def _run_rag(
    query: str,
    material_ids: List[str],
    user_id: str,
    notebook_id: str,
    **kwargs,
) -> AsyncIterator[Union[str, ToolResult]]:
    from app.services.tools.rag_tool import execute
    async for item in execute(query, material_ids, user_id, notebook_id):
        yield item


async def _run_web_search(
    query: str,
    user_id: str,
    **kwargs,
) -> AsyncIterator[Union[str, ToolResult]]:
    from app.services.tools.web_search_tool import execute
    async for item in execute(query, user_id):
        yield item


async def _run_research(
    query: str,
    user_id: str,
    notebook_id: str,
    session_id: str,
    **kwargs,
) -> AsyncIterator[Union[str, ToolResult]]:
    from app.services.tools.research_tool import execute
    async for item in execute(query, user_id, notebook_id, session_id):
        yield item


async def _run_python_auto(
    query: str,
    material_ids: List[str],
    user_id: str,
    notebook_id: str,
    session_id: str,
    **kwargs,
) -> AsyncIterator[Union[str, ToolResult]]:
    """Generate code then immediately execute it and register artifacts."""
    from app.services.tools.python_tool import execute as gen_execute
    from .artifact_executor import execute_code_and_collect_artifacts

    # Step 1: Generate code via LLM
    generated_code = ""
    language = "python"

    async for item in gen_execute(query, material_ids, user_id, notebook_id, session_id):
        if isinstance(item, ToolResult):
            generated_code = item.metadata.get("code", "")
            language = item.metadata.get("language", "python")
            # Don't yield the ToolResult from code gen — we'll yield after execution
        else:
            # Yield SSE events (tool_start, code_block, etc.)
            yield item

    if not generated_code:
        logger.error("python_auto: code generation returned empty code for query: %s",
                      query[:200])
        yield ToolResult(
            tool_name="python",
            success=False,
            content="Code generation produced no code.",
            metadata={"error": "no_code_generated"},
        )
        return

    logger.info("python_auto: generated %d chars of %s code", len(generated_code), language)

    # Step 2: Auto-execute the generated code + register artifacts
    async for item in execute_code_and_collect_artifacts(
        generated_code, user_id, notebook_id, session_id,
        language=language, material_ids=material_ids,
    ):
        yield item


TOOL_REGISTRY: Dict[str, ToolSpec] = {
    "rag": ToolSpec(
        name="rag",
        description=(
            "Search uploaded documents (PDFs, text files, notes) using RAG retrieval. "
            "Best for answering questions from user-uploaded text/document content. "
            "Do NOT use for structured datasets (CSV, Excel) — use 'python' instead."
        ),
        execute_fn=_run_rag,
        required_params=["query", "material_ids", "user_id", "notebook_id"],
    ),
    "web_search": ToolSpec(
        name="web_search",
        description=(
            "Search the internet using DuckDuckGo. ONLY use when the user "
            "explicitly needs current, live, or real-time information (today's "
            "news, stock prices, latest stats). Do NOT use for general knowledge "
            "or well-known facts the LLM already knows."
        ),
        execute_fn=_run_web_search,
        required_params=["query", "user_id"],
    ),
    "research": ToolSpec(
        name="research",
        description=(
            "Perform deep multi-source research with iterative query decomposition, "
            "parallel web searches, and structured synthesis. Use for complex "
            "research questions requiring comprehensive analysis."
        ),
        execute_fn=_run_research,
        required_params=["query", "user_id", "notebook_id", "session_id"],
    ),
    "python_auto": ToolSpec(
        name="python_auto",
        description=(
            "Generate AND execute Python code. Use for ALL data analysis, ML, statistics, "
            "visualization (charts, scatter plots, histograms), and file generation tasks. "
            "Code runs immediately in a sandbox — output images are shown inline, output "
            "files (CSV, PDF, DOCX, etc.) get download buttons. "
            "Always prefer this over 'python' when working with datasets."
        ),
        execute_fn=_run_python_auto,
        required_params=["query", "material_ids", "user_id", "notebook_id", "session_id"],
    ),
}


def get_available_tools(has_materials: bool = False) -> Dict[str, ToolSpec]:
    """Return tools available given context. RAG requires uploaded materials."""
    tools = dict(TOOL_REGISTRY)
    if not has_materials:
        tools.pop("rag", None)
    return tools


def get_tools_description(has_materials: bool = False) -> str:
    """Formatted description of available tools for LLM prompts."""
    tools = get_available_tools(has_materials)
    lines = []
    for name, spec in tools.items():
        lines.append(f"- **{name}**: {spec.description}")
    return "\n".join(lines)
