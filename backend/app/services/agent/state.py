from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .resource_router import ResourceProfile


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    description: str
    tool_hint: Optional[str] = None
    status: StepStatus = StepStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None


@dataclass
class AgentState:
    goal: str
    user_id: str
    notebook_id: str
    session_id: str
    material_ids: List[str] = field(default_factory=list)

    task_type: str = "general_chat"
    plan: List[PlanStep] = field(default_factory=list)
    current_step_index: int = 0
    observations: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    messages: List[Dict[str, str]] = field(default_factory=list)

    resource_profile: Optional[ResourceProfile] = None
    is_file_generation: bool = False

    total_tool_calls: int = 0
    finished: bool = False
    finish_reason: Optional[str] = None

    @property
    def current_step(self) -> Optional[PlanStep]:
        if 0 <= self.current_step_index < len(self.plan):
            return self.plan[self.current_step_index]
        return None

    def advance(self) -> bool:
        self.current_step_index += 1
        return self.current_step_index < len(self.plan)

    def mark_current(self, status: StepStatus, result: str = "", error: str = ""):
        step = self.current_step
        if step:
            step.status = status
            step.result = result
            step.error = error

    def summary_of_observations(self, max_chars: int = 6000) -> str:
        parts = []
        for obs in self.observations:
            tool = obs.get("tool", "unknown")
            content = obs.get("content", "")
            parts.append(f"[{tool}] {content}")
        text = "\n---\n".join(parts)
        return text[:max_chars] if len(text) > max_chars else text

    def completed_steps_summary(self) -> str:
        lines = []
        for i, step in enumerate(self.plan):
            if step.status == StepStatus.COMPLETED:
                lines.append(f"Step {i+1}: {step.description} -> {step.result or 'done'}")
        return "\n".join(lines)
