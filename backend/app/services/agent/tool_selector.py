from __future__ import annotations

import logging
import re
from datetime import date

from app.services.llm_service.llm import get_llm_structured

from .log_utils import log_stage
from .memory import AgentMemory
from .prompts import TOOL_SELECTOR_PROMPT
from .state import AgentState
from .tools_registry import get_available_tools, get_tools_description

logger = logging.getLogger(__name__)

# Explicit "web search" in user goal → always web_search
_EXPLICIT_WEB_SEARCH = re.compile(
    r"\bweb\s*search\b|\bsearch\s+the\s+web\b|\bdo\s+a\s+search\b|\binternet\s+search\b",
    re.IGNORECASE,
)

# Explicit "research" / "deep research" in user goal → research tool
_EXPLICIT_RESEARCH_REQUEST = re.compile(
    r"\bdo\s+research\b|\bdeep\s+research\b|\bcomprehensive\s+research\b|"
    r"\bconduct\s+research\b|\bin.?depth\s+research\b",
    re.IGNORECASE,
)

# Keywords that strongly indicate data/analysis work → python_auto
_DATA_KEYWORDS = re.compile(
    r"\b(csv|excel|xlsx|xls|tsv|dataset|dataframe|statistic|chart|plot|"
    r"visuali[sz]|histogram|regression|cluster|correlat|compute|calculat|"
    r"generate.*report|load.*data|analyze.*data|data\s*analysis)\b",
    re.IGNORECASE,
)

# Keywords that strongly indicate document/knowledge retrieval → rag
_DOC_KEYWORDS = re.compile(
    r"\b(pdf|document|paper|passage|section|summar|extract.*text|retrieve|"
    r"knowledge|notes|find.*in.*document)\b",
    re.IGNORECASE,
)

# Keywords that indicate file/artifact generation → python_auto
_FILE_GEN_KEYWORDS = re.compile(
    r"\b(generat|creat|export|produc|build|save|write).*"
    r"(pdf|csv|docx|xlsx|image|chart|file|report|document|png|jpg|svg|html)\b",
    re.IGNORECASE,
)

# Keywords that indicate web/live data needs
_WEB_KEYWORDS = re.compile(
    r"\b(current|latest|today|live|real.?time|news|recent|updated?|search|web|internet)\b",
    re.IGNORECASE,
)

# Keywords that indicate deep research
_RESEARCH_KEYWORDS = re.compile(
    r"\b(research|deep\s*dive|comprehensive|in.?depth\s*analysis)\b",
    re.IGNORECASE,
)


def _deterministic_route(step_desc: str, state: AgentState, available: dict) -> str | None:
    """Apply resource-aware deterministic rules before falling back to LLM.
    
    Uses task_type from intent classification + resource profile for fast routing.
    """
    rp = state.resource_profile
    has_python = "python_auto" in available
    has_rag = "rag" in available
    task_type = state.task_type
    step_lower = step_desc.lower()

    # ─── Highest priority: honour explicit tool request in user's original goal ──
    # "web search" in goal → always web_search (never research)
    if _EXPLICIT_WEB_SEARCH.search(state.goal):
        if "web_search" in available:
            return "web_search"

    # "deep research / do research" → research tool
    if _EXPLICIT_RESEARCH_REQUEST.search(state.goal):
        if "research" in available:
            return "research"

    # ─── Step-level keyword detection ─────────────────────────────
    _step_wants_search = any(
        kw in step_lower
        for kw in ("search the web", "web search", "search for", "look up", "find out")
    )
    _step_wants_generate = any(
        kw in step_lower
        for kw in ("generate", "create", "produce", "build", "using the research", "using the findings")
    )

    if _step_wants_search and not _step_wants_generate:
        # If user also explicitly said "web search" in goal, never use research
        if _EXPLICIT_WEB_SEARCH.search(state.goal) and "web_search" in available:
            return "web_search"
        if "research" in available and _RESEARCH_KEYWORDS.search(step_desc):
            return "research"
        if "web_search" in available:
            return "web_search"

    if _step_wants_generate and not _step_wants_search:
        if has_python:
            return "python_auto"

    # ─── Rule 0: Route by task_type (from intent classification) ──
    if task_type in ("dataset_analysis", "file_generation", "coding_task", "visualization"):
        if has_python:
            return "python_auto"

    if task_type == "document_analysis":
        if has_rag:
            return "rag"
        if has_python:
            return "python_auto"

    if task_type == "web_research":
        # If user explicitly said "web search", never use research tool
        if _EXPLICIT_WEB_SEARCH.search(state.goal):
            if "web_search" in available:
                return "web_search"
        if "research" in available and _RESEARCH_KEYWORDS.search(step_desc):
            return "research"
        if "web_search" in available:
            return "web_search"

    if task_type == "knowledge_query" and has_python:
        return "python_auto"

    # Rule 1: Explicit file generation → python_auto
    if has_python and _FILE_GEN_KEYWORDS.search(step_desc):
        return "python_auto"

    # Rule 2: Data keywords with datasets present → python_auto
    if has_python and rp and rp.has_datasets and _DATA_KEYWORDS.search(step_desc):
        return "python_auto"

    # Rule 3: Only datasets (no documents), non-web step → python_auto
    needs_web = _WEB_KEYWORDS.search(step_desc)
    if has_python and rp and rp.has_datasets and not rp.has_documents and not needs_web:
        return "python_auto"

    # Rule 4: Document keywords with documents present → rag
    if has_rag and rp and rp.has_documents and _DOC_KEYWORDS.search(step_desc):
        return "rag"

    # Rule 5: File generation goal + non-web step → python_auto
    if has_python and state.is_file_generation and not needs_web:
        return "python_auto"

    # Rule 6: No materials, research/web routing
    if rp and not rp.has_materials and not state.is_file_generation:
        if "research" in available and _RESEARCH_KEYWORDS.search(step_desc):
            return "research"
        if "web_search" in available and needs_web:
            return "web_search"

    return None


async def select_tool(state: AgentState, memory: AgentMemory) -> str:
    """Use resource-aware routing + LLM reasoning to pick the best tool."""
    step = state.current_step
    if not step:
        raise ValueError("No current step to select tool for.")

    has_materials = bool(state.material_ids)
    available = get_available_tools(has_materials)

    # Fast path 1: honour the plan's tool_hint — planner already chose the right
    # tool per step, so trust it before any other routing logic.
    if step.tool_hint and step.tool_hint in available:
        log_stage(logger, "Tool Selected", {
            "tool":   step.tool_hint,
            "method": "hint",
            "step":   step.description[:56],
        })
        return step.tool_hint

    # Fast path 2: deterministic resource-based routing (no hint present)
    det = _deterministic_route(step.description, state, available)
    if det:
        log_stage(logger, "Tool Selected", {
            "tool":   det,
            "method": "deterministic",
            "step":   step.description[:56],
        })
        return det

    # LLM fallback with resource context
    tools_desc = get_tools_description(has_materials)
    observations = state.summary_of_observations(max_chars=2000)
    resource_info = memory.get_resource_info_for_prompt()

    prompt = TOOL_SELECTOR_PROMPT.format(
        today=date.today().strftime("%B %d, %Y"),
        goal=state.goal,
        step_description=step.description,
        tool_hint=step.tool_hint or "none",
        resource_info=resource_info,
        tools_description=tools_desc,
        observations=observations or "None yet.",
    )

    llm = get_llm_structured(temperature=0.0)
    response = await llm.ainvoke(prompt)
    raw = getattr(response, "content", str(response)).strip().lower()

    # Extract tool name from response
    for tool_name in available:
        if tool_name in raw:
            log_stage(logger, "Tool Selected", {
                "tool":   tool_name,
                "method": "LLM",
                "step":   step.description[:56],
            })
            return tool_name

    # Fallback: use tool hint or first available
    if step.tool_hint and step.tool_hint in available:
        logger.warning(
            "Tool selector output '%s' not recognized; falling back to hint '%s'",
            raw, step.tool_hint,
        )
        return step.tool_hint

    fallback = next(iter(available))
    logger.warning("Tool selector fallback to '%s'", fallback)
    return fallback
