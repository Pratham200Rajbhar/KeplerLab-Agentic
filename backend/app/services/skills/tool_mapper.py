"""
Tool Mapper — maps skill step instructions to agent tool names.

Uses keyword heuristics (matching the parser's tool hint detection)
plus a lightweight LLM fallback for ambiguous steps.
"""
from __future__ import annotations

import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)

# ── Keyword-based tool mapping ─────────────────────────────

_TOOL_PATTERNS = {
    "rag": re.compile(
        r"\b(search documents?|search uploaded|find in documents?|retrieve from|"
        r"look up in documents?|query documents?|search materials?|from uploaded|"
        r"search notes?|read from sources?|find in sources?|parse source|"
        r"analyze (.{0,20} )?materials?|extract from documents?|from notebook|from context|"
        r"read through (.{0,20} )?documents?|source material|uploaded material|analyze (.{0,20} )?notes?)\b",
        re.IGNORECASE,
    ),
    "web_search": re.compile(
        r"\b(search (the )?web|search online|web search|google|find online|"
        r"latest news|current events|look up online|search (the )?internet|"
        r"find recent|current data|live information|research online)\b",
        re.IGNORECASE,
    ),
    "research": re.compile(
        r"\b(deep research|research (.{0,20} )?comprehensively|multi-source research|"
        r"in-depth analysis|thorough investigation|comprehensive report|"
        r"exhaustive search|research paper|literature review)\b",
        re.IGNORECASE,
    ),
    "python_auto": re.compile(
        r"\b(generate code|run code|execute code|python|(generate|create) (.{0,20} )?(chart|graph|plot|pdf|csv|file)|"
        r"data analysis|visuali[sz]e|calculate|compute|process data|"
        r"train model|statistics|export|download|convert to|"
        r"scatter plot|histogram|bar chart|pie chart|heatmap|"
        r"pandas|numpy|matplotlib|seaborn)\b",
        re.IGNORECASE,
    ),
}

# Generic LLM handles anything that doesn't trigger a specialized tool.
_LLM_PATTERN = re.compile(
    r"\b(summari[sz]e|synthesize|rewrite|transform|convert text|translate|"
    r"compose|draft|outline|explain|analyze text|extract key|format|"
    r"generate .{0,20}(summary|report|text|response|answer)|"
    r"write .{0,20}(summary|report|conclusion|intro)|"
    r"combine|merge findings|organize|structure|categorize)\b",
    re.IGNORECASE,
)


def map_step_to_tool(
    instruction: str,
    tool_hint: Optional[str] = None,
    has_materials: bool = False,
) -> str:
    """
    Map a step instruction to a tool name.

    Priority:
    1. Explicit tool_hint from parser
    2. Specialized tool pattern matching (RAG, Web Search, Research, Python)
    3. Generic LLM reasoning
    """
    # 1. Use parser's hint if available
    if tool_hint and (tool_hint in _TOOL_PATTERNS or tool_hint == "llm"):
        # Validate: 'rag' needs materials
        if tool_hint == "rag" and not has_materials:
            logger.info("Tool hint 'rag' downgraded to 'web_search' (no materials)")
            return "web_search"
        return tool_hint

    # 2. Specialized keyword matching
    for tool_name, pattern in _TOOL_PATTERNS.items():
        if pattern.search(instruction):
            if tool_name == "rag" and not has_materials:
                # If it looks like RAG but we have no files, try web search fallback
                logger.info("Keyword match 'rag' downgraded to 'web_search' (no materials)")
                return "web_search"
            return tool_name

    # 3. Generic LLM matching or default fallback
    if _LLM_PATTERN.search(instruction):
        return "llm"

    # Default to LLM if nothing else matches
    return "llm"


def map_steps_to_tools(
    steps: List[dict],
    has_materials: bool = False,
) -> List[dict]:
    """
    Map all steps in a compiled plan to tools.
    Returns the steps with 'tool' field populated.
    """
    mapped = []
    for step in steps:
        instruction = step.get("instruction", "")
        hint = step.get("tool_hint")
        tool = map_step_to_tool(instruction, hint, has_materials)
        mapped.append({**step, "tool": tool})
        logger.debug("Step %d → tool=%s: %s", step.get("index", 0), tool, instruction[:80])
    return mapped
