from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Optional

from app.services.llm_service.llm import get_llm_structured

from .memory import AgentMemory
from .prompts import REFLECTION_PROMPT
from .state import AgentState, StepStatus

logger = logging.getLogger(__name__)


class ReflectionAction(str, Enum):
    CONTINUE = "continue"
    RETRY = "retry"
    COMPLETE = "complete"
    ABORT = "abort"


class ReflectionResult:
    def __init__(
        self,
        step_succeeded: bool,
        goal_achieved: bool,
        action: ReflectionAction,
        reason: str,
    ):
        self.step_succeeded = step_succeeded
        self.goal_achieved = goal_achieved
        self.action = action
        self.reason = reason


async def reflect(state: AgentState, memory: AgentMemory) -> ReflectionResult:
    """Evaluate progress and decide the next action."""
    # Short-circuit: if we're on the last step and it already completed
    # successfully there is no need to hit the LLM — just declare done.
    if state.plan and state.current_step_index >= len(state.plan) - 1:
        cs = state.plan[state.current_step_index]
        if cs.status == StepStatus.COMPLETED:
            return ReflectionResult(
                step_succeeded=True,
                goal_achieved=True,
                action=ReflectionAction.COMPLETE,
                reason="All plan steps completed successfully.",
            )

    plan_summary = "\n".join(
        f"{i+1}. [{s.status.value}] {s.description}"
        for i, s in enumerate(state.plan)
    )

    step = state.current_step
    latest_step = step.description if step else "N/A"
    latest_result = step.result or step.error or "No result" if step else "N/A"

    observations = state.summary_of_observations(max_chars=3000)
    artifacts = ", ".join(a.get("filename", "?") for a in state.artifacts) or "None"

    prompt = REFLECTION_PROMPT.format(
        goal=state.goal,
        plan_summary=plan_summary,
        latest_step=latest_step,
        latest_result=latest_result[:1000],
        observations=observations or "None",
        artifacts=artifacts,
    )

    llm = get_llm_structured(temperature=0.0)
    response = await llm.ainvoke(prompt)
    raw = getattr(response, "content", str(response)).strip()

    return _parse_reflection(raw, state)


def _parse_reflection(raw: str, state: AgentState) -> ReflectionResult:
    """Parse LLM reflection output with robust fallback."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                logger.warning("Failed to parse reflection JSON; defaulting to continue.")
                return _default_reflection(state)
        else:
            logger.warning("No JSON in reflection output; defaulting to continue.")
            return _default_reflection(state)

    step_succeeded = data.get("step_succeeded", True)
    goal_achieved = data.get("goal_achieved", False)
    action_str = data.get("action", "continue").lower()
    reason = data.get("reason", "")

    try:
        action = ReflectionAction(action_str)
    except ValueError:
        action = ReflectionAction.CONTINUE

    return ReflectionResult(
        step_succeeded=step_succeeded,
        goal_achieved=goal_achieved,
        action=action,
        reason=reason,
    )


def _default_reflection(state: AgentState) -> ReflectionResult:
    """If we're on the last step, complete. Otherwise continue."""
    is_last = state.current_step_index >= len(state.plan) - 1
    if is_last:
        return ReflectionResult(
            step_succeeded=True,
            goal_achieved=True,
            action=ReflectionAction.COMPLETE,
            reason="Last step reached; marking as complete.",
        )
    return ReflectionResult(
        step_succeeded=True,
        goal_achieved=False,
        action=ReflectionAction.CONTINUE,
        reason="Continuing to next step.",
    )
