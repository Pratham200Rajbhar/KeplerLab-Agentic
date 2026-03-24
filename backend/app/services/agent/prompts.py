from __future__ import annotations

from app.prompts import compose_prompt, get_prompt_template


# ── Agent system prompt ─────────────────────────────────────────────────
# Uses compose_prompt() for SAFE rendering — all {placeholders} in the
# raw markdown templates are resolved: known ones get values, unknown
# ones become empty strings.  This prevents the KeyError crash that
# occurred when using raw get_prompt_template() + str.format().
#
# NOTE: {today} is NOT baked in here — it is injected at runtime by the
# orchestrator via simple string concatenation (not .format()).
AGENT_SYSTEM_PROMPT = compose_prompt(
    [
        "system/base_system.md",
        "shared/safety.md",
        "shared/style.md",
    ],
    {
        "mode": "Agent",
        "user_intent": "Execute the user's task autonomously using available tools",
        "today": "",  # will be injected at runtime
    },
)

# ── Chat-level prompts (all {vars} are supplied by callers) ─────────────
SYNTHESIS_PROMPT = get_prompt_template("chat/agent_synthesis.md")
DIRECT_RESPONSE_PROMPT = get_prompt_template("chat/direct_response.md")

# ── Structured prompts (all {vars} supplied by callers) ─────────────────
INTENT_CLASSIFIER_PROMPT = get_prompt_template("system/agent_intent_classifier.md")
PLANNER_PROMPT = get_prompt_template("system/agent_planner.md")
TOOL_SELECTOR_PROMPT = get_prompt_template("system/agent_tool_selector.md")
REFLECTION_PROMPT = get_prompt_template("system/agent_reflection.md")
