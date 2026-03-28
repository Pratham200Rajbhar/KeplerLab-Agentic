from __future__ import annotations

import json
import logging
import re
from datetime import date
from typing import List

from app.services.llm_service.llm import get_llm_structured

from .log_utils import log_stage
from .memory import AgentMemory
from .prompts import PLANNER_PROMPT, INTENT_CLASSIFIER_PROMPT
from .state import AgentState, PlanStep
from .tools_registry import get_tools_description


def _today() -> str:
    return date.today().strftime("%B %d, %Y")

logger = logging.getLogger(__name__)
_VAR_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")

# Valid task types the classifier can return
VALID_TASK_TYPES = {
    "knowledge_query",
    "document_analysis",
    "dataset_analysis",
    "web_research",
    "deep_research",
    "file_generation",
    "coding_task",
    "data_processing",
    "visualization",
    "math_computation",
    "content_creation",
    "general_chat",
}

_FILE_OUTPUT_STEP_PATTERN = re.compile(
    r"\b(generate|create|export|save|produce|write|build|deliver)\b.*"
    r"\b(pdf|csv|xlsx|excel|docx|pptx|html|report|document|file|chart|image|graph)\b"
    r"|\b(pdf|csv|xlsx|docx|pptx|report|document|file)\b",
    re.IGNORECASE,
)


def _render_prompt(template: str, variables: dict) -> str:
    """Render only known placeholders and leave all other braces intact.

    This prevents str.format KeyError when prompt templates include JSON
    examples such as {"description": "..."}.
    """

    def _repl(match: re.Match) -> str:
        key = match.group(1)
        return str(variables.get(key, ""))

    return _VAR_RE.sub(_repl, template)


async def classify_intent(state: AgentState, memory: AgentMemory) -> str:
    """Classify the user's request into a task type.

    Priority order:
    1. File-generation intent → file_generation (deterministic artifact path)
    2. Explicit deep-research request → deep_research
    3. Uploaded datasets/documents classification
    4. Explicit web/live-data keywords → web_research
    5. LLM fallback
    """
    goal_lower = state.goal.lower()
    rp = state.resource_profile

    # ── 0. File generation must stay on artifact-capable pipeline ──
    if state.is_file_generation:
        return "file_generation"

    # ── 1. Deep research detection (before general web check) ──────
    _DEEP_RESEARCH_PATTERN = re.compile(
        r"\b(deep\s+research|comprehensive\s+research|in.?depth\s+research|"
        r"thorough\s+research|detailed\s+research|conduct\s+research|"
        r"do\s+(?:some\s+)?research\s+on|research\s+on\b)",
        re.IGNORECASE,
    )
    if _DEEP_RESEARCH_PATTERN.search(goal_lower):
        return "deep_research"

    # ── 2. Web / live-data detection ───────────────────────────────
    _WEB_PATTERN = re.compile(
        r"\b(current|latest|today|live|real.?time|news|recent|updated?|"
        r"search\s+the\s+web|search\s+online|web\s+search|look\s*up|"
        r"find\s+out|what.s\s+happening|this\s+week|this\s+month|"
        r"search\s+for|gather\s+data\s+from|"
        r"find\s+(?:how|what|why|when|where|who|information|info|details|out)|"
        r"internet|20\d{2}\s+(stats?|result|score|report|data|event|match|update))\b",
        re.IGNORECASE,
    )
    needs_web = bool(_WEB_PATTERN.search(goal_lower))

    # ── 3. Resource-based classification ──────────────────────────
    if rp and rp.has_datasets:
        if needs_web:
            return "web_research"
        return "dataset_analysis"

    if rp and rp.has_documents and not rp.has_datasets:
        if needs_web:
            return "web_research"
        return "document_analysis"

    # ── 4. Web classification ──────────────────────────────────────
    if needs_web:
        return "web_research"

    # ── 5. Keyword-based pre-classification ───────────────────────

    _CODE_PATTERN = re.compile(
        r"\bwrite\s+(?:a\s+)?(?:python\s+)?(?:function|class|script|module|program|code)\b|"
        r"\bimplement\s+(?:a\s+|an\s+)?(?:function|class|algorithm|method|api)\b|"
        r"\bdebug\s+(?:this\s+)?(?:code|error|bug)\b|"
        r"\bfix\s+(?:this\s+)?(?:code|bug|error|issue)\b|"
        r"\breview\s+(?:this\s+)?code\b|"
        r"\brefactor\b",
        re.IGNORECASE,
    )
    if _CODE_PATTERN.search(goal_lower):
        return "coding_task"

    _COMPUTE_PATTERN = re.compile(
        r"\b(?:calculate|compute|solve|evaluate|integrate|differentiate|"
        r"simulate|optimize|minimize|maximize)\s+\w",
        re.IGNORECASE,
    )
    if _COMPUTE_PATTERN.search(goal_lower):
        return "math_computation"

    _VIZ_PATTERN = re.compile(
        r"\b(?:plot|draw|render|visualize|visualise|"
        r"generate\s+(?:a\s+)?(?:chart|graph|diagram|fractal|visual|image|figure))\b",
        re.IGNORECASE,
    )
    if _VIZ_PATTERN.search(goal_lower):
        return "visualization"

    # ── 6. Follow-up modification detection ───────────────────────
    if memory.chat_history:
        _MODIFY_PATTERN = re.compile(
            r"\b(change|modify|update|make it|now (make|add|show|render|create|generate|give)|"
            r"also (add|include|show|make)|add (a |the )?(legend|title|label|axis|grid|"
            r"color|colour|annotation|marker|bar|line|column)|"
            r"use (blue|red|green|yellow|orange|purple|black|white|log|linear|"
            r"dark|light|different)|set (the )?(title|label|color|colour|scale|font|size)|"
            r"remove (the )?(legend|title|label|grid|axis)|"
            r"make (the )?(chart|plot|graph|figure|output|file|report)|"
            r"try (again|a different|with|using)|redo|regenerate|rerun|re-run)\b",
            re.IGNORECASE,
        )
        if _MODIFY_PATTERN.search(goal_lower):
            recent_assistant = [
                m for m in memory.chat_history[-6:]
                if m.get("role") == "assistant"
            ]
            _EXEC_EVIDENCE = {"generated", "created", "saved", "chart", "plot", "graph",
                              "scatter", "figure", "file", "png", "pdf", "xlsx", "pptx",
                              "docx", "csv", "output", "executed", "ran"}
            prior_had_execution = any(
                any(kw in (m.get("content") or "").lower() for kw in _EXEC_EVIDENCE)
                for m in recent_assistant
            )
            if prior_had_execution:
                logger.info(
                    "Follow-up modification detected with prior execution context → coding_task"
                )
                return "coding_task"

    # ── 7. LLM fallback for ambiguous cases ───────────────────────
    resource_info = memory.get_resource_info_for_prompt()
    history = memory.format_chat_history()
    n_turns = min(len(memory.chat_history), 10)
    prompt = _render_prompt(
        INTENT_CLASSIFIER_PROMPT,
        {
            "goal": state.goal,
            "resource_info": resource_info,
            "chat_history": history,
            "today": _today(),
            "n": n_turns,
        },
    )

    try:
        llm = get_llm_structured(temperature=0.0)
        response = await llm.ainvoke(prompt)
        raw = getattr(response, "content", str(response)).strip().lower()
        for tt in VALID_TASK_TYPES:
            if tt in raw:
                return tt
    except Exception as exc:
        logger.warning("Intent classification failed: %s; defaulting to coding_task", exc)

    return "coding_task"


def _enforce_file_generation_steps(steps: List[PlanStep]) -> List[PlanStep]:
    """Guarantee that output-producing steps run via python_auto."""
    if not steps:
        return steps

    enforced: List[PlanStep] = []
    for idx, step in enumerate(steps):
        description = (step.description or "").strip() or f"Step {idx + 1}"
        tool_hint = step.tool_hint
        is_last = idx == (len(steps) - 1)
        looks_like_output = bool(_FILE_OUTPUT_STEP_PATTERN.search(description))

        if is_last or looks_like_output:
            tool_hint = "python_auto"

        enforced.append(PlanStep(description=description, tool_hint=tool_hint))

    if all((s.tool_hint or "") != "python_auto" for s in enforced):
        enforced[-1].tool_hint = "python_auto"

    return enforced


async def create_plan(state: AgentState, memory: AgentMemory) -> List[PlanStep]:
    """LLM-first planning for ALL task types.

    Only general_chat gets a fast-path (empty plan → direct response).
    Everything else goes through the LLM planner for dynamic, open-ended
    planning that can handle any query.
    """
    # Step 1: Use pre-classified task_type if available
    if state.task_type and state.task_type != "general_chat":
        task_type = state.task_type
    else:
        task_type = await classify_intent(state, memory)
        state.task_type = task_type

    log_stage(logger, "Intent Classified", {
        "task_type":  task_type,
        "goal":       state.goal[:60],
        "materials":  f"{len(state.material_ids)} file(s)",
        "file_gen":   state.is_file_generation,
    })

    # Step 2: Fast-path for general_chat only (no tools needed)
    if task_type == "general_chat":
        state.plan = []
        state.current_step_index = 0
        logger.info("General chat — no tools needed, skipping plan.")
        return []

    # Step 3: Pure knowledge queries without file output → direct LLM response
    if task_type == "knowledge_query" and not state.is_file_generation:
        # Check if user is asking something that truly needs code execution
        _EXEC_PATTERN = re.compile(
            r"\b(calculate|compute|generate|create|make|build|write|implement|"
            r"solve|simulate|optimize|predict|plot|chart|graph|visualize|"
            r"code|script|function|algorithm|render|draw|convert|transform|"
            r"analyze|analyse|summarize|summarise|extract|classify|cluster)\b",
            re.IGNORECASE,
        )
        if not _EXEC_PATTERN.search(state.goal):
            state.plan = []
            state.current_step_index = 0
            logger.info("Knowledge query — direct LLM response, no tools.")
            return []

    # Step 4: LLM-driven planning for ALL other cases
    has_materials = bool(state.material_ids)
    tools_desc = get_tools_description(has_materials)
    context = memory.build_context_for_planner()
    resource_info = memory.get_resource_info_for_prompt()
    chat_history = memory.format_chat_history()

    prompt = _render_prompt(
        PLANNER_PROMPT,
        {
            "goal": state.goal,
            "task_type": task_type,
            "context": context,
            "resource_info": resource_info,
            "tools_description": tools_desc,
            "chat_history": chat_history,
            "today": _today(),
        },
    )

    try:
        llm = get_llm_structured(temperature=0.1)
        response = await llm.ainvoke(prompt)
        raw = getattr(response, "content", str(response)).strip()
        steps = _parse_plan(raw)
    except Exception as exc:
        logger.warning("LLM planner failed: %s; using single-step fallback.", exc)
        steps = []

    # Fallback: if LLM returned nothing, create a sensible single step
    if not steps:
        default_tool = _fallback_tool(task_type, state)
        steps = [PlanStep(description=state.goal, tool_hint=default_tool)]
        logger.warning("Planner returned empty plan; using fallback: %s", default_tool)

    # Enforce maximum 8 steps
    if len(steps) > 8:
        steps = steps[:8]

    # File-generation tasks must end with artifact-capable execution.
    if state.is_file_generation:
        steps = _enforce_file_generation_steps(steps)

    state.plan = steps
    state.current_step_index = 0

    plan_fields: dict = {"task_type": task_type, "steps": len(steps), "source": "LLM"}
    for i, s in enumerate(steps):
        plan_fields[f"step[{i + 1}]"] = f"{s.description[:46]} → {s.tool_hint or 'auto'}"
    log_stage(logger, "Plan · LLM", plan_fields)
    return steps


def _fallback_tool(task_type: str, state: AgentState) -> str:
    """Pick a sensible default tool when the LLM planner fails."""
    if task_type in ("dataset_analysis", "file_generation", "coding_task",
                     "visualization", "data_processing", "math_computation"):
        return "python_auto"
    if task_type == "document_analysis" and state.resource_profile and state.resource_profile.has_documents:
        return "rag"
    if task_type in ("web_research", "deep_research"):
        return "web_search"
    return "python_auto"


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
