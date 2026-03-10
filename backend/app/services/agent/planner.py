from __future__ import annotations

import json
import logging
from typing import List

from app.services.llm_service.llm import get_llm_structured

from .memory import AgentMemory
from .prompts import PLANNER_PROMPT
from .state import AgentState, PlanStep
from .tools_registry import get_tools_description

logger = logging.getLogger(__name__)


async def create_plan(state: AgentState, memory: AgentMemory) -> List[PlanStep]:
    """Use LLM to generate a structured execution plan from the user goal."""
    has_materials = bool(state.material_ids)
    tools_desc = get_tools_description(has_materials)
    context = memory.build_context_for_planner()
    resource_info = memory.get_resource_info_for_prompt()

    prompt = PLANNER_PROMPT.format(
        goal=state.goal,
        context=context,
        resource_info=resource_info,
        tools_description=tools_desc,
    )

    llm = get_llm_structured(temperature=0.1)
    response = await llm.ainvoke(prompt)
    raw = getattr(response, "content", str(response)).strip()

    steps = _parse_plan(raw)
    if not steps:
        steps = [PlanStep(description=state.goal, tool_hint=None)]
        logger.warning("Planner returned empty plan; using fallback single-step plan.")

    state.plan = steps
    state.current_step_index = 0
    logger.info("Agent plan created with %d step(s)", len(steps))
    return steps


def _parse_plan(raw: str) -> List[PlanStep]:
    """Robustly parse the LLM's JSON plan output."""
    text = raw.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # drop opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON array from surrounding text
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                logger.error("Failed to parse plan JSON: %s", text[:200])
                return []
        else:
            logger.error("No JSON array found in planner output: %s", text[:200])
            return []

    if not isinstance(data, list):
        logger.error("Planner output is not a list: %s", type(data))
        return []

    steps: List[PlanStep] = []
    for item in data:
        if isinstance(item, dict) and "description" in item:
            steps.append(
                PlanStep(
                    description=item["description"],
                    tool_hint=item.get("tool_hint"),
                )
            )
    return steps
