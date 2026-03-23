from __future__ import annotations

from app.prompts import get_prompt_template


# These constants keep the existing .format(...) call pattern used by the agent runtime.
# They are now sourced from modular markdown templates in app/prompts.
AGENT_SYSTEM_PROMPT = "\n\n".join(
    [
        get_prompt_template("system/base_system.md").strip(),
        get_prompt_template("system/agent_system.md").strip(),
        get_prompt_template("system/tool_system.md").strip(),
        get_prompt_template("shared/safety.md").strip(),
        get_prompt_template("shared/style.md").strip(),
    ]
)

INTENT_CLASSIFIER_PROMPT = get_prompt_template("system/agent_intent_classifier.md")
PLANNER_PROMPT = get_prompt_template("system/agent_planner.md")
TOOL_SELECTOR_PROMPT = get_prompt_template("system/agent_tool_selector.md")
REFLECTION_PROMPT = get_prompt_template("system/agent_reflection.md")
SYNTHESIS_PROMPT = get_prompt_template("chat/agent_synthesis.md")
DIRECT_RESPONSE_PROMPT = get_prompt_template("chat/direct_response.md")
