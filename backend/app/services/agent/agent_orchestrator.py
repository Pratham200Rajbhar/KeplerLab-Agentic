"""
KeplerLab Agent Orchestrator — LangGraph pipeline
==================================================

Flow:
  analyse → plan → [direct_response | execute_step ↺ advance_step] → synthesize

Streaming:
  Every node pushes SSE strings through an asyncio.Queue; run_agent() drains
  it and yields to FastAPI's StreamingResponse.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re as _re
import operator
import time
from datetime import date
from typing import (
    Annotated, Any, AsyncIterator, Awaitable, Callable,
    Dict, List, Optional, TypedDict,
)

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END

from app.db.prisma_client import prisma
from app.services.chat_v2 import message_store
from app.services.chat_v2.schemas import ToolResult
from app.services.chat_v2.streaming import (
    sse, sse_done, sse_error, sse_meta, sse_token, sse_blocks,
)
from app.services.llm_service.llm import get_llm, get_llm_structured

from .executor import execute_tool, process_tool_result
from .log_utils import log_stage
from .memory import AgentMemory
from .planner import create_plan, classify_intent
from .prompts import SYNTHESIS_PROMPT, DIRECT_RESPONSE_PROMPT, AGENT_SYSTEM_PROMPT, REFLECTION_PROMPT
from .resource_router import classify_materials
from .artifact_executor import detect_file_generation_intent
from .state import AgentState, PlanStep
from .tool_selector import select_tool

logger = logging.getLogger(__name__)

MAX_STEPS      = 12
MAX_TOOL_CALLS = 15
MAX_RETRIES    = 2
AGENT_TIMEOUT  = 600   # seconds

EmitFn = Callable[[str], Awaitable[None]]


# ═══════════════════════════════════════════════════════════════════════
# 1. LangGraph TypedDict State
# ═══════════════════════════════════════════════════════════════════════

class AgentGraphState(TypedDict):
    # Input
    goal:          str
    user_id:       str
    notebook_id:   str
    session_id:    str
    material_ids:  List[str]

    # Analysis
    task_type:          str
    is_file_generation: bool
    resource_profile:   Any          # ResourceProfile (in-process only)

    # Plan — list of {description, tool_hint}
    plan:               List[Dict[str, Any]]
    current_step_index: int

    # Accumulators: each step appends via operator.add
    observations: Annotated[List[Dict], operator.add]
    artifacts:    Annotated[List[Dict], operator.add]
    sources:      Annotated[List[Dict], operator.add]

    # Counters (replaced, not accumulated)
    total_tool_calls:  int
    step_count:        int
    step_retry_count:  int
    last_step_success: bool

    # Output
    finish_reason:  str
    final_response: str
    start_time:     float

    # Runtime objects (not serialised — in-memory only)
    _memory:      Any   # AgentMemory
    _agent_state: Any   # AgentState (compat shim for existing tools)
    _reflect_decision: str  # Reflection node decision: continue|retry_with_fix|replan|complete


# ═══════════════════════════════════════════════════════════════════════
# 2. Helpers
# ═══════════════════════════════════════════════════════════════════════

_VAR_RE = _re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def _render_prompt(template: str, variables: Dict[str, str]) -> str:
    """Safe prompt renderer — replaces known {vars}, blanks unknown ones.

    Unlike str.format(), this will NEVER raise KeyError for unresolved
    placeholders.  Unknown variables become empty strings.
    """
    def _repl(m: _re.Match) -> str:
        return variables.get(m.group(1), "")
    return _VAR_RE.sub(_repl, template)


def _today() -> str:
    return date.today().strftime("%B %d, %Y")


def _chunk_text(text: str, size: int = 40) -> List[str]:
    return [text[i:i + size] for i in range(0, len(text), size)]


def _build_agent_state(gs: AgentGraphState) -> AgentState:
    """Reconstruct a legacy AgentState from current GraphState for tool executors."""
    st = AgentState(
        goal=gs["goal"], user_id=gs["user_id"],
        notebook_id=gs["notebook_id"], session_id=gs["session_id"],
        material_ids=list(gs.get("material_ids") or []),
    )
    st.task_type          = gs.get("task_type", "general_chat")
    st.is_file_generation = gs.get("is_file_generation", False)
    st.resource_profile   = gs.get("resource_profile")
    st.total_tool_calls   = gs.get("total_tool_calls", 0)
    st.observations       = list(gs.get("observations") or [])
    st.artifacts          = list(gs.get("artifacts") or [])
    st.sources            = list(gs.get("sources") or [])
    plan_data = gs.get("plan") or []
    st.plan = [PlanStep(description=p["description"], tool_hint=p.get("tool_hint"))
               for p in plan_data]
    st.current_step_index = gs.get("current_step_index", 0)
    return st




# ═══════════════════════════════════════════════════════════════════════
# 3. LangGraph Nodes
# ═══════════════════════════════════════════════════════════════════════

async def _node_analyse(state: AgentGraphState, config) -> Dict:
    emit: EmitFn = config["configurable"]["emit"]
    await emit(sse("agent_status", {"phase": "planning", "message": "Analysing request…"}))

    resource_profile = await classify_materials(state["material_ids"])
    is_file_gen      = detect_file_generation_intent(state["goal"])

    # Temporary AgentState so classify_intent can read resource_profile
    tmp = _build_agent_state({
        **state,
        "resource_profile": resource_profile,
        "is_file_generation": is_file_gen,
        "observations": [], "artifacts": [], "sources": [],
    })
    memory = AgentMemory(tmp)
    await memory.load_chat_history()

    task_type = await classify_intent(tmp, memory)
    tmp.task_type = task_type

    log_stage(logger, "Analyse", {
        "task_type": task_type, "is_file_gen": is_file_gen,
        "goal": state["goal"][:60],
    })
    return {
        "task_type": task_type,
        "is_file_generation": is_file_gen,
        "resource_profile": resource_profile,
        "_agent_state": tmp,
        "_memory": memory,
    }


async def _node_plan(state: AgentGraphState, config) -> Dict:
    emit: EmitFn = config["configurable"]["emit"]
    await emit(sse("agent_status", {"phase": "planning", "message": "Creating execution plan…"}))

    agent_state: AgentState  = state["_agent_state"]
    memory:      AgentMemory = state["_memory"]
    agent_state.task_type          = state["task_type"]
    agent_state.is_file_generation = state["is_file_generation"]
    agent_state.resource_profile   = state["resource_profile"]

    plan_steps = await create_plan(agent_state, memory)

    # Safety net: ANY task that isn't pure chat/text creation with empty plan
    # must get at least one execution step — otherwise _route_after_plan sends
    # to direct_response, which is correct.
    # But if file generation is expected, we MUST inject python_auto.
    if not plan_steps and (
        state["is_file_generation"]
        or state["task_type"] not in {"general_chat", "content_creation"}
    ):
        logger.warning("Empty plan for task_type=%s — injecting fallback step.", state["task_type"])
        # Pick tool based on task type
        if state["task_type"] in {"web_research", "deep_research"}:
            tool = "research" if state["task_type"] == "deep_research" else "web_search"
            plan_steps = [PlanStep(description=state["goal"], tool_hint=tool)]
            if state["is_file_generation"]:
                plan_steps.append(PlanStep(
                    description=f"Generate the requested file output using the data found: {state['goal'][:200]}",
                    tool_hint="python_auto",
                ))
        elif state["task_type"] == "document_analysis" and state.get("material_ids"):
            plan_steps = [PlanStep(description=state["goal"], tool_hint="rag")]
        else:
            plan_steps = [PlanStep(description=state["goal"], tool_hint="python_auto")]

    plan_data = [{"description": s.description, "tool_hint": s.tool_hint} for s in plan_steps]

    await emit(sse("agent_plan", {
        "steps": [
            {"step": i + 1, "description": p["description"], "tool_hint": p["tool_hint"]}
            for i, p in enumerate(plan_data)
        ],
    }))
    log_stage(logger, "Plan", {
        "task_type": state["task_type"], "steps": len(plan_data),
        **{f"step[{i+1}]": f"{p['description'][:42]} → {p['tool_hint']}"
           for i, p in enumerate(plan_data)},
    })
    agent_state.plan               = plan_steps
    agent_state.current_step_index = 0
    return {"plan": plan_data, "current_step_index": 0, "_agent_state": agent_state}


async def _node_execute_step(state: AgentGraphState, config) -> Dict:
    emit: EmitFn = config["configurable"]["emit"]
    step_idx = state["current_step_index"]
    plan     = state["plan"]

    # Guard: empty plan or index out of range → skip to synthesize
    if not plan or step_idx >= len(plan):
        logger.warning("execute_step called with empty plan or bad index (%d/%d)", step_idx, len(plan))
        return {
            "observations": [{"tool": "system", "content": "No executable steps in plan."}],
            "artifacts":    [],
            "sources":      [],
            "total_tool_calls":  state.get("total_tool_calls", 0),
            "step_count":        state.get("step_count", 0),
            "last_step_success": False,
            "step_retry_count":  MAX_RETRIES + 1,   # force synthesize on routing
            "_agent_state": state.get("_agent_state"),
            "_memory":      state.get("_memory"),
        }

    step = plan[step_idx]

    agent_state: AgentState  = state["_agent_state"]
    memory:      AgentMemory = state["_memory"]

    # Sync accumulated state into agent_state so executor sees prior context
    agent_state.observations      = list(state.get("observations") or [])
    agent_state.artifacts         = list(state.get("artifacts") or [])
    agent_state.sources           = list(state.get("sources") or [])
    agent_state.total_tool_calls  = state.get("total_tool_calls", 0)
    agent_state.current_step_index = step_idx

    await emit(sse("agent_step", {
        "step_number": step_idx + 1,
        "total_steps": len(plan),
        "description": step["description"],
    }))

    # Tool selection
    try:
        tool_name = await select_tool(agent_state, memory)
    except Exception as exc:
        logger.warning("Tool selection failed (%s) — using hint or python_auto", exc)
        tool_name = step.get("tool_hint") or "python_auto"

    await emit(sse("agent_tool", {"tool": tool_name, "step": step["description"]}))
    log_stage(logger, f"Step {step_idx+1}/{len(plan)}",
              {"desc": step["description"][:60], "tool": tool_name})

    # Tool execution — forward all SSE events, capture ToolResult.
    # Filter out "done" events from tools — those are tool-internal completion
    # signals that would prematurely terminate the SSE stream for the client.
    tool_result: Optional[ToolResult] = None
    try:
        async for item in execute_tool(tool_name, agent_state, memory):
            if isinstance(item, ToolResult):
                tool_result = item
            elif isinstance(item, str) and item.startswith("event: done"):
                pass  # swallow tool-level "done" event
            else:
                await emit(item)   # includes agent_artifact, code_block, tool_start…
    except Exception as exc:
        logger.error("Tool execution raised: %s", exc)
        tool_result = ToolResult(
            tool_name=tool_name, success=False,
            content=f"Tool error: {exc}", metadata={"error": str(exc)},
        )

    # Collect results
    new_obs       = []
    new_artifacts = []
    new_sources   = []
    step_success  = False

    if tool_result:
        # Update agent_state internals (step status, memory context)
        process_tool_result(tool_result, agent_state, memory)
        step_success = tool_result.success

        if tool_result.content:
            new_obs = [{"tool": tool_name, "content": tool_result.content[:4000]}]
        new_artifacts = list(tool_result.artifacts or [])
        new_sources   = list(tool_result.metadata.get("sources", []))

        await emit(sse("agent_result", {
            "tool":    tool_name,
            "success": step_success,
            "summary": (tool_result.content or "")[:300],
        }))
        log_stage(logger, "Result", {
            "tool":      tool_name,
            "success":   step_success,
            "artifacts": len(new_artifacts),
            "preview":   (tool_result.content or "")[:60],
        })

    return {
        # Accumulated via operator.add
        "observations": new_obs,
        "artifacts":    new_artifacts,
        "sources":      new_sources,
        # Counters (replaced)
        "total_tool_calls":  state.get("total_tool_calls", 0) + 1,
        "step_count":        state.get("step_count", 0) + 1,
        "last_step_success": step_success,
        "step_retry_count":  0 if step_success else state.get("step_retry_count", 0) + 1,
        "_agent_state": agent_state,
        "_memory":      memory,
    }


async def _node_advance_step(state: AgentGraphState, config) -> Dict:
    """Increment step index and reset retry counter."""
    agent_state: AgentState = state["_agent_state"]
    new_idx = state["current_step_index"] + 1
    agent_state.current_step_index = new_idx
    return {"current_step_index": new_idx, "step_retry_count": 0, "_agent_state": agent_state}


async def _node_reflect(state: AgentGraphState, config) -> Dict:
    """Self-healing reflection node.

    After each step execution, the LLM evaluates the result and decides:
      - continue:       step OK, move to next planned step
      - retry_with_fix: step failed, retry with corrected instructions
      - replan:         current plan insufficient, add new steps
      - complete:       goal fully achieved, skip remaining steps
    """
    emit: EmitFn = config["configurable"]["emit"]
    success = bool(state.get("last_step_success", False))
    plan = list(state.get("plan") or [])
    step_idx = int(state.get("current_step_index", 0))
    retries = int(state.get("step_retry_count", 0))
    is_last = step_idx >= len(plan) - 1

    # Fast path: success on last step → go straight to synthesize
    if success and is_last:
        return {"_reflect_decision": "complete"}

    # Fast path: success and more steps → continue
    if success and not is_last:
        return {"_reflect_decision": "continue"}

    # Fast path: exceeded retry budget → move on
    if retries >= MAX_RETRIES:
        logger.warning("Reflect: max retries (%d) exceeded, moving on.", MAX_RETRIES)
        return {"_reflect_decision": "continue" if not is_last else "complete"}

    # ── LLM-based reflection on failure ────────────────────────────
    await emit(sse("agent_status", {"phase": "reflecting", "message": "Analyzing error and planning fix…"}))

    latest_obs = list(state.get("observations") or [])[-1:]
    latest_result = str(latest_obs[0].get("content", "No output")) if latest_obs else "No output"
    error_info = ""
    if latest_obs:
        meta = latest_obs[0].get("metadata", {})
        if isinstance(meta, dict):
            error_info = meta.get("error", "")

    current_step = plan[step_idx] if step_idx < len(plan) else {}
    artifacts_str = ", ".join(a.get("filename", "?") for a in (state.get("artifacts") or [])) or "None"
    obs_str = "\n".join(
        f"[{o.get('tool','?')}] {o.get('content','')[:300]}"
        for o in (state.get("observations") or [])
    )[-2000:] or "None"

    prompt = _render_prompt(REFLECTION_PROMPT, {
        "today": _today(),
        "goal": state["goal"],
        "step_number": str(step_idx + 1),
        "total_steps": str(len(plan)),
        "latest_step": current_step.get("description", state["goal"]),
        "success": str(success),
        "latest_result": latest_result[:1500],
        "error": error_info or "None",
        "artifacts": artifacts_str,
        "observations": obs_str,
    })

    try:
        llm = get_llm_structured(temperature=0.0)
        response = await llm.ainvoke(prompt)
        raw = getattr(response, "content", str(response)).strip()
    except Exception as exc:
        logger.warning("Reflection LLM call failed: %s; defaulting to continue", exc)
        return {"_reflect_decision": "continue"}

    raw_lower = raw.lower()
    log_stage(logger, "Reflect", {"raw": raw[:120], "step": step_idx + 1})

    # Parse decision
    if "retry_with_fix" in raw_lower:
        # Extract corrected step description
        new_desc = _extract_after(raw, "NEW_STEPS:")
        if new_desc and not new_desc.startswith("["):
            # Update the current plan step with corrected instructions
            plan[step_idx] = {
                "description": new_desc.strip(),
                "tool_hint": current_step.get("tool_hint"),
            }
            return {
                "_reflect_decision": "retry_with_fix",
                "plan": plan,
                "step_retry_count": retries + 1,
            }
        return {"_reflect_decision": "retry_with_fix", "step_retry_count": retries + 1}

    if "replan" in raw_lower:
        new_steps_raw = _extract_after(raw, "NEW_STEPS:")
        if new_steps_raw:
            try:
                start = new_steps_raw.find("[")
                end = new_steps_raw.rfind("]")
                if start != -1 and end != -1:
                    new_steps_data = json.loads(new_steps_raw[start:end+1])
                    new_plan = list(plan)  # copy
                    for ns in new_steps_data[:3]:  # max 3 new steps
                        if isinstance(ns, dict) and "description" in ns:
                            new_plan.append({
                                "description": ns["description"],
                                "tool_hint": ns.get("tool_hint"),
                            })
                    return {
                        "_reflect_decision": "replan",
                        "plan": new_plan,
                    }
            except Exception as exc:
                logger.warning("Failed to parse replan steps: %s", exc)
        return {"_reflect_decision": "continue"}

    if "complete" in raw_lower:
        return {"_reflect_decision": "complete"}

    # Default: continue
    return {"_reflect_decision": "continue"}


def _extract_after(text: str, marker: str) -> str:
    """Extract text after a marker like 'NEW_STEPS:'."""
    idx = text.find(marker)
    if idx == -1:
        return ""
    return text[idx + len(marker):].strip()


async def _node_direct_response(state: AgentGraphState, config) -> Dict:
    emit: EmitFn = config["configurable"]["emit"]
    await emit(sse("agent_status", {"phase": "synthesizing", "message": "Generating response…"}))

    memory: Optional[AgentMemory] = state.get("_memory")
    system = f"{AGENT_SYSTEM_PROMPT}\n\nToday is {_today()}."
    human  = _render_prompt(DIRECT_RESPONSE_PROMPT, {
        "today": _today(),
        "chat_history": memory.format_chat_history(max_turns=12) if memory else "",
        "artifacts": memory.format_session_artifacts() if memory else "",
        "goal": state["goal"],
    })
    llm      = get_llm(temperature=0.3)
    response = await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=human)])
    text     = getattr(response, "content", str(response)).strip()

    for token in _chunk_text(text):
        await emit(sse_token(token))

    return {"final_response": text, "finish_reason": "direct_response"}


async def _node_synthesize(state: AgentGraphState, config) -> Dict:
    emit: EmitFn = config["configurable"]["emit"]
    await emit(sse("agent_status", {"phase": "synthesizing", "message": "Generating response…"}))

    memory: Optional[AgentMemory] = state.get("_memory")

    obs_str = "\n---\n".join(
        f"[{o.get('tool','?')}] {o.get('content','')}"
        for o in (state.get("observations") or [])
    )[:5000] or "No observations recorded."

    artifacts_list = state.get("artifacts") or []
    if artifacts_list:
        artifacts_str = ", ".join(a.get("filename", "?") for a in artifacts_list)
    else:
        artifacts_str = "None"

    sources_str = "\n".join(
        f"[{i+1}] {s.get('title','')} – {s.get('url','')}"
        for i, s in enumerate(state.get("sources") or [])
    ) or "None"

    # Detect if the goal expected file output but none were produced
    is_file_gen = state.get("is_file_generation", False)
    file_expected_but_missing = is_file_gen and not artifacts_list

    system = f"{AGENT_SYSTEM_PROMPT}\n\nToday is {_today()}."
    human  = _render_prompt(SYNTHESIS_PROMPT, {
        "today": _today(),
        "goal": state["goal"],
        "chat_history": memory.format_chat_history(max_turns=8) if memory else "",
        "observations": obs_str,
        "artifacts": artifacts_str,
        "sources": sources_str,
    })

    llm      = get_llm(temperature=0.3)
    response = await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=human)])
    text     = getattr(response, "content", str(response)).strip()

    for token in _chunk_text(text):
        await emit(sse_token(token))

    reason = state.get("finish_reason")
    if not reason or reason == "unknown":
        if artifacts_list:
            reason = "artifact_produced"
        elif file_expected_but_missing:
            reason = "file_generation_failed"
        else:
            reason = "goal_achieved"
    return {"final_response": text, "finish_reason": reason}


# ═══════════════════════════════════════════════════════════════════════
# 4. Conditional routing
# ═══════════════════════════════════════════════════════════════════════

def _route_after_plan(state: AgentGraphState) -> str:
    plan      = state.get("plan") or []
    if not plan:
        # ALL empty plans go to direct_response — never send to execute_step
        # with an empty plan, which would cause IndexError on plan[step_idx].
        return "direct_response"
    return "execute_step"


def _route_after_execute(state: AgentGraphState) -> str:
    """After executing a step, always go to reflect for intelligent routing."""
    step_count = int(state.get("step_count", 0))
    tool_calls = int(state.get("total_tool_calls", 0))

    # Hard limits — skip reflection, go to synthesize
    if step_count >= MAX_STEPS or tool_calls >= MAX_TOOL_CALLS:
        return "synthesize"

    return "reflect"


def _route_after_reflect(state: AgentGraphState) -> str:
    """Route based on the reflection node's decision."""
    decision = str(state.get("_reflect_decision", "continue"))
    step_idx = int(state.get("current_step_index", 0))
    total = len(list(state.get("plan") or []))
    is_last = step_idx >= total - 1

    if decision == "complete":
        return "synthesize"

    if decision == "retry_with_fix":
        return "execute_step"  # re-run same step with corrected instructions

    if decision == "replan":
        # Plan was extended — advance and execute the new step
        return "advance_step" if not is_last else "execute_step"

    # "continue" — advance to next step or synthesize if last
    if is_last:
        return "synthesize"
    return "advance_step"


# ═══════════════════════════════════════════════════════════════════════
# 5. Compile the graph (built once at import time)
# ═══════════════════════════════════════════════════════════════════════

def _build_graph() -> Any:
    g = StateGraph(AgentGraphState)
    g.add_node("analyse",         _node_analyse)
    g.add_node("planner",         _node_plan)
    g.add_node("execute_step",    _node_execute_step)
    g.add_node("reflect",         _node_reflect)
    g.add_node("advance_step",    _node_advance_step)
    g.add_node("direct_response", _node_direct_response)
    g.add_node("synthesize",      _node_synthesize)

    g.set_entry_point("analyse")
    g.add_edge("analyse", "planner")
    g.add_conditional_edges("planner", _route_after_plan,
                             {"execute_step": "execute_step",
                              "direct_response": "direct_response"})
    g.add_conditional_edges("execute_step", _route_after_execute,
                             {"synthesize": "synthesize",
                              "reflect":    "reflect"})
    g.add_conditional_edges("reflect", _route_after_reflect,
                             {"synthesize":   "synthesize",
                              "advance_step": "advance_step",
                              "execute_step": "execute_step"})
    g.add_edge("advance_step",    "execute_step")
    g.add_edge("direct_response", END)
    g.add_edge("synthesize",      END)
    return g.compile()


_AGENT_GRAPH = _build_graph()


# ═══════════════════════════════════════════════════════════════════════
# 6. Public entry point
# ═══════════════════════════════════════════════════════════════════════

async def run_agent(
    goal:         str,
    notebook_id:  str,
    user_id:      str,
    session_id:   str,
    material_ids: List[str],
) -> AsyncIterator[str]:
    """
    LangGraph agent pipeline.

    Runs the graph in a background asyncio Task and streams SSE events
    through a Queue so FastAPI's StreamingResponse sees them in real time.
    """
    start_time = time.time()
    queue: asyncio.Queue = asyncio.Queue()

    async def emit(event: str) -> None:
        await queue.put(event)

    initial_state: AgentGraphState = {
        "goal":               goal,
        "user_id":            user_id,
        "notebook_id":        notebook_id,
        "session_id":         session_id,
        "material_ids":       list(material_ids or []),
        "task_type":          "general_chat",
        "is_file_generation": False,
        "resource_profile":   None,
        "plan":               [],
        "current_step_index": 0,
        "observations":       [],
        "artifacts":          [],
        "sources":            [],
        "total_tool_calls":   0,
        "step_count":         0,
        "step_retry_count":   0,
        "last_step_success":  False,
        "finish_reason":      "unknown",
        "final_response":     "",
        "start_time":         start_time,
        "_memory":            None,
        "_agent_state":       None,
        "_reflect_decision": "continue",
    }

    final_state: Dict = {}
    graph_error: Optional[str] = None

    async def _run_graph() -> None:
        nonlocal final_state, graph_error
        try:
            log_stage(logger, "START", {
                "goal":      goal[:72] + ("…" if len(goal) > 72 else ""),
                "user":      user_id,
                "notebook":  notebook_id,
                "materials": f"{len(material_ids or [])} file(s)",
            })
            result = await _AGENT_GRAPH.ainvoke(
                initial_state,
                config={"configurable": {"emit": emit}},
            )
            final_state = dict(result) if result else {}
        except Exception as exc:
            logger.error("Agent graph error: %s", exc, exc_info=True)
            graph_error = str(exc)
            await emit(sse_error(str(exc)))
        finally:
            await queue.put(None)   # sentinel → stop draining

    task = asyncio.create_task(_run_graph())

    # ── Drain queue → yield SSE to HTTP response ──────────────────
    # Send SSE keepalive comments every _KEEPALIVE seconds to prevent
    # idle-connection timeouts (h11 / proxies / TCP) during long research ops.
    _KEEPALIVE = 15  # seconds
    try:
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=_KEEPALIVE)
            except asyncio.TimeoutError:
                if task.done():
                    # Graph finished but sentinel not received yet — break
                    break
                elapsed_so_far = time.time() - start_time
                if elapsed_so_far > AGENT_TIMEOUT:
                    logger.error("Agent stream timed out after %ds", AGENT_TIMEOUT)
                    yield sse_error("Agent timed out")
                    task.cancel()
                    break
                # Still running — send keepalive comment to prevent connection drop
                yield ": keepalive\n\n"
                continue
            if item is None:
                break
            yield item
    except GeneratorExit:
        task.cancel()
        return

    # Ensure graph task is fully done (don't re-raise caught exceptions)
    try:
        await task
    except Exception as exc:
        logger.error("Awaiting agent task raised: %s", exc)
        if not graph_error:
            graph_error = str(exc)

    # ── Derive finish_reason robustly ──────────────────────────────
    elapsed = round(time.time() - start_time, 2)
    finish_reason = final_state.get("finish_reason", "unknown")
    if finish_reason == "unknown":
        # Infer from available state even if graph crashed partway
        if graph_error:
            finish_reason = "error"
        elif final_state.get("artifacts"):
            finish_reason = "artifact_produced"
        elif final_state.get("final_response"):
            finish_reason = "goal_achieved"
        else:
            finish_reason = "completed"

    meta = {
        "intent":          "AGENT",
        "task_type":       final_state.get("task_type", "unknown"),
        "steps_executed":  final_state.get("step_count", 0),
        "tool_calls":      final_state.get("total_tool_calls", 0),
        "finish_reason":   finish_reason,
        "elapsed":         elapsed,
    }
    yield sse_meta(meta)

    final_response = final_state.get("final_response", "")

    # ── Persist to DB ──────────────────────────────────────────────
    try:
        await message_store.save_user_message(notebook_id, user_id, session_id, goal)
        msg_id = await message_store.save_assistant_message(
            notebook_id, user_id, session_id, final_response, meta,
        )
        for art in (final_state.get("artifacts") or []):
            art_id = art.get("id")
            if art_id:
                try:
                    await prisma.artifact.update(
                        where={"id": art_id}, data={"messageId": msg_id},
                    )
                except Exception as link_exc:
                    logger.warning("Artifact link failed %s: %s", art_id, link_exc)
        blocks = await message_store.save_response_blocks(msg_id, final_response)
        if blocks:
            yield sse_blocks(blocks)
    except Exception as exc:
        logger.error("Agent persistence failed: %s", exc)

    yield sse("agent_done", {
        "finish_reason":  finish_reason,
        "steps_executed": final_state.get("step_count", 0),
        "tool_calls":     final_state.get("total_tool_calls", 0),
    })
    log_stage(logger, "COMPLETE", {
        "task_type":     final_state.get("task_type"),
        "finish_reason": final_state.get("finish_reason"),
        "steps":         final_state.get("step_count", 0),
        "tool_calls":    final_state.get("total_tool_calls", 0),
        "artifacts":     len(final_state.get("artifacts") or []),
        "elapsed":       f"{elapsed:.2f}s",
    })
    yield sse_done({"elapsed": elapsed, **meta})

