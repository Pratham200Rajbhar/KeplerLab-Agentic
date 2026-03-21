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


async def classify_intent(state: AgentState, memory: AgentMemory) -> str:
    """Classify the user's request into a task type.

    Priority order:
    1. Explicit web/live-data keywords → web_research  (even if file output requested)
    2. Uploaded datasets → dataset_analysis
    3. Uploaded documents → document_analysis
    4. File-generation intent (no web needed) → file_generation
    5. LLM fallback
    """
    goal_lower = state.goal.lower()
    rp = state.resource_profile

    # ── 0. Deep research detection (before general web check) ──────
    _DEEP_RESEARCH_PATTERN = re.compile(
        r"\b(deep\s+research|comprehensive\s+research|in.?depth\s+research|"
        r"thorough\s+research|detailed\s+research|conduct\s+research|"
        r"do\s+(?:some\s+)?research\s+on|research\s+on\b)",
        re.IGNORECASE,
    )
    if _DEEP_RESEARCH_PATTERN.search(goal_lower):
        return "deep_research"

    # ── 1. Web / live-data detection (highest priority) ───────────
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

    # ── 2. Resource-based classification ──────────────────────────
    if rp and rp.has_datasets:
        if needs_web:
            return "web_research"
        return "dataset_analysis"

    if rp and rp.has_documents and not rp.has_datasets:
        if needs_web:
            return "web_research"
        return "document_analysis"

    # ── 3. Web takes precedence over pure file-gen ────────────────
    if needs_web:
        return "web_research"

    # ── 4. Pure file-generation (no web needed) ───────────────────
    if state.is_file_generation:
        return "file_generation"

    # ── 5. Keyword-based pre-classification (catches tasks the LLM
    #        might mis-route to knowledge_query) ───────────────────

    # Code writing / debugging / review
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

    # Pure computation / math (no file format, no live data)
    _COMPUTE_PATTERN = re.compile(
        r"\b(?:calculate|compute|solve|evaluate|integrate|differentiate|"
        r"simulate|optimize|minimize|maximize)\s+\w",
        re.IGNORECASE,
    )
    if _COMPUTE_PATTERN.search(goal_lower):
        return "math_computation"

    # Chart / visualization request (without explicit file format — those hit file_generation)
    _VIZ_PATTERN = re.compile(
        r"\b(?:plot|draw|render|visualize|visualise|"
        r"generate\s+(?:a\s+)?(?:chart|graph|diagram|fractal|visual|image|figure))\b",
        re.IGNORECASE,
    )
    if _VIZ_PATTERN.search(goal_lower):
        return "visualization"

    # ── 6. Follow-up modification detection ──────────────────────
    # If the user has prior conversation history that included code execution / file generation
    # and their current message looks like a modification/refinement request,
    # route directly to coding_task so the agent RE-RUNS code rather than giving a text answer.
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
            # Confirm prior assistant turn had execution evidence
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
    prompt = INTENT_CLASSIFIER_PROMPT.format(
        goal=state.goal,
        resource_info=resource_info,
        chat_history=history,
        today=_today(),
        n=n_turns,
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

    # Final safety: anything unclassified that is not a follow-up → use python_auto
    # This ensures the agent always attempts execution rather than giving a text-only answer.
    return "coding_task"


async def create_plan(state: AgentState, memory: AgentMemory) -> List[PlanStep]:
    """Use intent classification + LLM to generate a minimal execution plan.

    If state.task_type is already set (not 'general_chat'), reuse it to avoid
    a redundant classify_intent call — _node_analyse already classified.
    """
    # Step 1: Use pre-classified task_type if available, otherwise classify
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

    # Step 2: Fast-path for general_chat (no tools needed)
    if task_type == "general_chat":
        state.plan = []
        state.current_step_index = 0
        logger.info("General chat — no tools needed, skipping plan.")
        return []

    # Step 3: Deterministic single-step plans for common cases
    deterministic = _deterministic_plan(task_type, state)
    if deterministic:
        state.plan = deterministic
        state.current_step_index = 0
        det_fields: dict = {"task_type": task_type, "steps": len(deterministic)}
        for i, s in enumerate(deterministic):
            det_fields[f"step[{i + 1}]"] = f"{s.description[:42]} → {s.tool_hint or 'auto'}"
        log_stage(logger, "Plan · Deterministic", det_fields)
        return deterministic

    # Step 4: LLM-based planning for complex/ambiguous cases
    has_materials = bool(state.material_ids)
    tools_desc = get_tools_description(has_materials)
    context = memory.build_context_for_planner()
    resource_info = memory.get_resource_info_for_prompt()
    chat_history = memory.format_chat_history()

    prompt = PLANNER_PROMPT.format(
        goal=state.goal,
        task_type=task_type,
        context=context,
        resource_info=resource_info,
        tools_description=tools_desc,
        chat_history=chat_history,
        today=_today(),
    )

    llm = get_llm_structured(temperature=0.1)
    response = await llm.ainvoke(prompt)
    raw = getattr(response, "content", str(response)).strip()

    steps = _parse_plan(raw)
    if not steps:
        steps = [PlanStep(description=state.goal, tool_hint=None)]
        logger.warning("Planner returned empty plan; using fallback single-step plan.")

    # Enforce maximum 4 steps
    if len(steps) > 4:
        steps = steps[:4]

    state.plan = steps
    state.current_step_index = 0
    plan_fields: dict = {"task_type": task_type, "steps": len(steps), "source": "LLM"}
    for i, s in enumerate(steps):
        plan_fields[f"step[{i + 1}]"] = f"{s.description[:46]} → {s.tool_hint or 'auto'}"
    log_stage(logger, "Plan · LLM", plan_fields)
    return steps


def _deterministic_plan(task_type: str, state: AgentState) -> List[PlanStep] | None:
    """Return a pre-built plan for straightforward task types, or None for LLM planning."""
    goal = state.goal

    # ── File format keywords — used to detect compound research+generate tasks ──
    _FILE_FORMAT_RE = re.compile(
        r"\b(pdf|docx|doc|xlsx|xls|pptx|ppt|csv|report|document|spreadsheet|chart|graph|plot)\b",
        re.I,
    )

    # ── Web research (may be compound: search + generate file) ────
    if task_type == "web_research":
        search_desc = f"Search the web for up-to-date information about: {goal[:200]}"

        # Explicit "web search" in the user's goal → ALWAYS use web_search tool.
        # Only use the heavier "research" tool when the user explicitly asks for
        # deep/comprehensive research (and did NOT also say "web search").
        _EXPLICIT_WEB = re.compile(r"\bweb\s*search\b|\bsearch\s+the\s+web\b", re.I)
        _EXPLICIT_RESEARCH = re.compile(
            r"\bdo\s+research\b|\bdeep\s+research\b|\bcomprehensive\s+research\b|"
            r"\bin.?depth\s+research\b|\bconduct\s+research\b",
            re.I,
        )

        if _EXPLICIT_WEB.search(goal):
            # User said "web search" → always web_search
            tool = "web_search"
        elif _EXPLICIT_RESEARCH.search(goal):
            # User explicitly asked for deep research
            tool = "research"
        else:
            # Autonomous decision: use research for complex queries
            _DEEP = re.compile(
                r"\b(comprehensive|in.?depth|thorough|detailed\s+analysis)\b", re.I
            )
            tool = "research" if _DEEP.search(goal) else "web_search"

        steps: list[PlanStep] = [PlanStep(description=search_desc, tool_hint=tool)]

        # Add python_auto step whenever the user asked for a file output, regardless
        # of whether the heuristic flag is set — check the goal text directly too.
        needs_file_output = state.is_file_generation or bool(_FILE_FORMAT_RE.search(goal))
        if needs_file_output:
            gen_desc = (
                f"Using ALL findings from the previous search step, generate the "
                f"requested file output. Use whatever data was found — even if partial "
                f"or approximate — to produce the file: {goal[:200]}"
            )
            steps.append(PlanStep(description=gen_desc, tool_hint="python_auto"))
        return steps

    # ── Data / document / file / code tasks (single-step) ─────────
    if task_type == "dataset_analysis":
        return [PlanStep(description=goal, tool_hint="python_auto")]

    if task_type == "document_analysis":
        steps = [PlanStep(description=goal, tool_hint="rag")]
        if state.is_file_generation or bool(_FILE_FORMAT_RE.search(goal)):
            gen_desc = (
                f"Using the information retrieved from the documents, generate the "
                f"requested file output: {goal[:200]}"
            )
            steps.append(PlanStep(description=gen_desc, tool_hint="python_auto"))
        return steps

    if task_type == "file_generation":
        return [PlanStep(description=goal, tool_hint="python_auto")]

    if task_type == "coding_task":
        return [PlanStep(description=goal, tool_hint="python_auto")]

    if task_type == "visualization":
        return [PlanStep(description=goal, tool_hint="python_auto")]

    if task_type in ("data_processing", "math_computation"):
        return [PlanStep(description=goal, tool_hint="python_auto")]

    if task_type == "deep_research":
        deep_steps: list[PlanStep] = [
            PlanStep(
                description=f"Research comprehensively: {goal[:200]}",
                tool_hint="research",
            )
        ]
        # Same as web_research: check goal text directly, not just the heuristic flag
        needs_file_output = state.is_file_generation or bool(_FILE_FORMAT_RE.search(goal))
        if needs_file_output:
            deep_steps.append(PlanStep(
                description=(
                    f"Using ALL research findings from the previous step, generate the "
                    f"requested file output. Use whatever data was collected — even if "
                    f"partial — to produce the file: {goal[:200]}"
                ),
                tool_hint="python_auto",
            ))
        return deep_steps

    if task_type == "content_creation":
        # File requested → generate via python_auto; pure text → direct LLM response
        if state.is_file_generation:
            return [PlanStep(description=goal, tool_hint="python_auto")]
        return []  # handled as direct LLM response (empty plan)

    if task_type == "knowledge_query":
        # File output explicitly requested → python_auto must run
        if state.is_file_generation:
            return [PlanStep(description=goal, tool_hint="python_auto")]
        # Any generative / computational phrasing → python_auto
        _EXEC_PATTERN = re.compile(
            r"\b(calculate|compute|generate|create|make|build|write|implement|"
            r"solve|simulate|optimize|predict|plot|chart|graph|visualize|"
            r"code|script|function|algorithm|render|draw|convert|transform|"
            r"analyze|analyse|summarize|summarise|extract|classify|cluster)\b",
            re.IGNORECASE,
        )
        if _EXEC_PATTERN.search(goal):
            return [PlanStep(description=goal, tool_hint="python_auto")]
        # Truly factual question → direct LLM (no tools)
        return []

    # ambiguous → LLM planning
    return None


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
