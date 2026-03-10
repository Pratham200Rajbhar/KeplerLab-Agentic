from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .state import AgentState

logger = logging.getLogger(__name__)


class AgentMemory:
    """Collects and manages context available to the agent during execution."""

    def __init__(self, state: AgentState):
        self._state = state
        self._chat_history: List[Dict[str, str]] = []
        self._rag_context: str = ""
        self._web_context: str = ""
        self._code_outputs: List[str] = []

    async def load_chat_history(self):
        try:
            from app.services.chat_v2.message_store import get_history
            self._chat_history = await get_history(
                self._state.notebook_id,
                self._state.user_id,
                self._state.session_id,
            )
        except Exception as exc:
            logger.warning("Failed to load chat history: %s", exc)

    def add_observation(self, tool_name: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        obs = {"tool": tool_name, "content": content}
        if metadata:
            obs["metadata"] = metadata
        self._state.observations.append(obs)

    def add_artifact(self, artifact: Dict[str, Any]):
        self._state.artifacts.append(artifact)

    def add_source(self, source: Dict[str, Any]):
        self._state.sources.append(source)

    def set_rag_context(self, context: str):
        self._rag_context = context

    def set_web_context(self, context: str):
        self._web_context = context

    def add_code_output(self, output: str):
        self._code_outputs.append(output)

    def build_context_for_planner(self) -> str:
        parts = [f"Goal: {self._state.goal}"]

        if self._state.material_ids:
            parts.append(f"User has {len(self._state.material_ids)} material(s) selected.")

        rp = self._state.resource_profile
        if rp:
            parts.append(f"Resource profile: {rp.summary()}")

        if self._chat_history:
            recent = self._chat_history[-5:]
            history_text = "\n".join(
                f"{m.get('role', 'user').capitalize()}: {m.get('content', '')[:200]}"
                for m in recent
            )
            parts.append(f"Recent chat history:\n{history_text}")

        return "\n\n".join(parts)

    def get_resource_info_for_prompt(self) -> str:
        """Resource information block for LLM prompts."""
        rp = self._state.resource_profile
        if not rp:
            if self._state.material_ids:
                return f"{len(self._state.material_ids)} material(s) uploaded (type unknown)."
            return "No uploaded materials."
        lines = [rp.summary()]
        rec = rp.recommended_tools()
        if rec:
            lines.append(f"\nRecommended tool routing:\n{rec}")
        return "\n".join(lines)

    def build_context_for_reflection(self) -> str:
        parts = [f"Goal: {self._state.goal}"]

        completed = self._state.completed_steps_summary()
        if completed:
            parts.append(f"Completed steps:\n{completed}")

        observations = self._state.summary_of_observations(max_chars=4000)
        if observations:
            parts.append(f"Observations:\n{observations}")

        if self._state.artifacts:
            artifact_list = ", ".join(a.get("filename", "unknown") for a in self._state.artifacts)
            parts.append(f"Generated artifacts: {artifact_list}")

        return "\n\n".join(parts)

    def build_context_for_tool(self) -> str:
        parts = [f"Goal: {self._state.goal}"]

        step = self._state.current_step
        if step:
            parts.append(f"Current step: {step.description}")

        observations = self._state.summary_of_observations(max_chars=3000)
        if observations:
            parts.append(f"Previous observations:\n{observations}")

        return "\n\n".join(parts)

    @property
    def chat_history(self) -> List[Dict[str, str]]:
        return self._chat_history
