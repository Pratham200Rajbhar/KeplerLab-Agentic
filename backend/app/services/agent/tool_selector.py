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


async def select_tool(state: AgentState, memory: AgentMemory) -> str:
    """Pick the best tool for the current step.

    Priority:
    1. Plan's tool_hint (the LLM planner already chose)
    2. Minimal resource-based shortcuts (datasets→python, documents→rag)
    3. LLM-based selection for everything else
    """
    step = state.current_step
    if not step:
        raise ValueError("No current step to select tool for.")

    has_materials = bool(state.material_ids)
    available = get_available_tools(has_materials)

    # ── Priority 1: trust the planner's tool_hint ──────────────────
    if step.tool_hint and step.tool_hint in available:
        log_stage(logger, "Tool Selected", {
            "tool":   step.tool_hint,
            "method": "hint",
            "step":   step.description[:56],
        })
        return step.tool_hint

    # ── Priority 2: minimal resource-aware shortcuts ───────────────
    rp = state.resource_profile
    step_lower = step.description.lower()

    # Datasets present and no web needed → python_auto
    if "python_auto" in available and rp and rp.has_datasets:
        log_stage(logger, "Tool Selected", {
            "tool": "python_auto", "method": "resource_shortcut", "step": step.description[:56],
        })
        return "python_auto"

    # Documents present + doc-related step → rag
    if "rag" in available and rp and rp.has_documents:
        _needs_docs = any(kw in step_lower for kw in ("document", "pdf", "extract", "retrieve", "passage", "study material"))
        if _needs_docs:
            log_stage(logger, "Tool Selected", {
                "tool": "rag", "method": "resource_shortcut", "step": step.description[:56],
            })
            return "rag"

    # ── Priority 3: LLM-based selection ────────────────────────────
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

    try:
        llm = get_llm_structured(temperature=0.0)
        response = await llm.ainvoke(prompt)
        raw = getattr(response, "content", str(response)).strip().lower()

        for tool_name in available:
            if tool_name in raw:
                log_stage(logger, "Tool Selected", {
                    "tool":   tool_name,
                    "method": "LLM",
                    "step":   step.description[:56],
                })
                return tool_name
    except Exception as exc:
        logger.warning("Tool selector LLM failed: %s", exc)

    # Fallback: use first available tool
    fallback = "python_auto" if "python_auto" in available else next(iter(available))
    logger.warning("Tool selector fallback to '%s'", fallback)
    return fallback
