"""
KeplerLab Agent Orchestrator
============================

Production pipeline with deterministic control flow:
  analyse -> plan -> execute/reflection loop -> synthesize/direct_response

Design goals:
- deterministic execution loop (no hidden graph transitions)
- strict plan/step normalization
- bounded retries and tool calls
- robust SSE streaming and persistence
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import date
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List, Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage

from app.db.prisma_client import prisma
from app.services.chat_v2 import message_store
from app.services.chat_v2.schemas import ToolResult
from app.services.chat_v2.streaming import (
    sse,
    sse_blocks,
    sse_done,
    sse_error,
    sse_meta,
    sse_token,
)
from app.services.llm_service.llm import get_llm, get_llm_structured

from .artifact_executor import detect_file_generation_intent
from .executor import execute_tool, process_tool_result
from .log_utils import log_stage
from .memory import AgentMemory
from .planner import classify_intent, create_plan
from .prompts import AGENT_SYSTEM_PROMPT, DIRECT_RESPONSE_PROMPT, REFLECTION_PROMPT, SYNTHESIS_PROMPT
from .resource_router import classify_materials
from .state import AgentState, PlanStep
from .tool_selector import select_tool

logger = logging.getLogger(__name__)

MAX_STEPS = 12
MAX_TOOL_CALLS = 15
MAX_RETRIES_PER_STEP = 2
AGENT_TIMEOUT = 600

_VAR_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def _today() -> str:
    return date.today().strftime("%B %d, %Y")


def _chunk_text(text: str, size: int = 40) -> List[str]:
    return [text[i:i + size] for i in range(0, len(text), size)]


def _render_prompt(template: str, variables: Dict[str, str]) -> str:
    """Safe prompt rendering: replace known placeholders, blank unknown ones."""

    def _repl(match: re.Match) -> str:
        key = match.group(1)
        return str(variables.get(key, ""))

    return _VAR_RE.sub(_repl, template)


def _normalize_step(step: Any) -> Optional[Dict[str, Any]]:
    if isinstance(step, PlanStep):
        desc = (step.description or "").strip()
        if not desc:
            return None
        return {"description": desc, "tool_hint": step.tool_hint}

    if isinstance(step, dict):
        desc = str(step.get("description", "")).strip()
        if not desc:
            return None
        return {"description": desc, "tool_hint": step.get("tool_hint")}

    if isinstance(step, str):
        desc = step.strip()
        if not desc:
            return None
        return {"description": desc, "tool_hint": None}

    return None


def _normalize_plan(raw_plan: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_plan, list):
        return []

    plan: List[Dict[str, Any]] = []
    for raw in raw_plan:
        normalized = _normalize_step(raw)
        if normalized:
            plan.append(normalized)
    return plan


def _fallback_tool(task_type: str, has_materials: bool, is_file_generation: bool) -> str:
    if task_type == "deep_research":
        return "research"
    if task_type == "web_research":
        return "web_search"
    if task_type == "document_analysis" and has_materials:
        return "rag"
    if is_file_generation:
        return "python_auto"
    if task_type in {"coding_task", "dataset_analysis", "data_processing", "math_computation", "visualization"}:
        return "python_auto"
    return "python_auto"


def _build_agent_state(
    goal: str,
    user_id: str,
    notebook_id: str,
    session_id: str,
    material_ids: List[str],
) -> AgentState:
    return AgentState(
        goal=goal,
        user_id=user_id,
        notebook_id=notebook_id,
        session_id=session_id,
        material_ids=list(material_ids or []),
    )


def _plan_to_state_steps(plan: List[Dict[str, Any]]) -> List[PlanStep]:
    return [PlanStep(description=s["description"], tool_hint=s.get("tool_hint")) for s in plan]


def _extract_after(text: str, marker: str) -> str:
    idx = text.find(marker)
    if idx == -1:
        return ""
    return text[idx + len(marker):].strip()


def _artifact_key(artifact: Dict[str, Any]) -> str:
    filename = str(artifact.get("filename") or "").strip().lower()
    while filename.startswith("./"):
        filename = filename[2:]
    if filename:
        return filename
    return str(artifact.get("id") or "")


def _merge_unique_artifacts(
    existing: List[Dict[str, Any]],
    incoming: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Merge artifacts while keeping only one entry per logical file."""
    ordered: Dict[str, Dict[str, Any]] = {}
    for artifact in existing:
        key = _artifact_key(artifact)
        if key:
            ordered[key] = artifact

    for artifact in incoming:
        key = _artifact_key(artifact)
        if key:
            ordered[key] = artifact

    return list(ordered.values())


def _build_file_generation_response(artifacts: List[Dict[str, Any]]) -> str:
    names = [str(a.get("filename") or "").strip() for a in artifacts if a.get("filename")]
    if not names:
        return "Task completed."

    if len(names) == 1:
        return f"Generated file: {names[0]}\n\nUse the artifact card to preview or download it."

    lines = "\n".join(f"- {name}" for name in names)
    return f"Generated files:\n{lines}\n\nUse the artifact cards to preview or download them."


async def _analyse_phase(
    *,
    goal: str,
    material_ids: List[str],
    agent_state: AgentState,
) -> Tuple[str, bool, Any, AgentMemory]:
    resource_profile = await classify_materials(material_ids)
    is_file_generation = detect_file_generation_intent(goal)

    agent_state.resource_profile = resource_profile
    agent_state.is_file_generation = is_file_generation

    memory = AgentMemory(agent_state)
    await memory.load_chat_history()

    task_type = await classify_intent(agent_state, memory)
    agent_state.task_type = task_type

    log_stage(
        logger,
        "Analyse",
        {
            "task_type": task_type,
            "is_file_gen": is_file_generation,
            "goal": goal[:60],
        },
    )

    return task_type, is_file_generation, resource_profile, memory


async def _planning_phase(
    *,
    goal: str,
    task_type: str,
    is_file_generation: bool,
    material_ids: List[str],
    agent_state: AgentState,
    memory: AgentMemory,
) -> List[Dict[str, Any]]:
    plan_steps = await create_plan(agent_state, memory)
    plan = _normalize_plan(plan_steps)

    needs_execution = is_file_generation or task_type not in {
        "general_chat",
        "knowledge_query",
        "content_creation",
    }

    if needs_execution and not plan:
        tool = _fallback_tool(task_type, bool(material_ids), is_file_generation)
        plan = [{"description": goal, "tool_hint": tool}]
        if is_file_generation and tool in {"web_search", "research"}:
            plan.append(
                {
                    "description": f"Generate requested file output from gathered findings: {goal[:220]}",
                    "tool_hint": "python_auto",
                }
            )
        logger.warning("Empty planner output for task_type=%s; injected fallback step using %s", task_type, tool)

    plan = _normalize_plan(plan)
    agent_state.plan = _plan_to_state_steps(plan)
    agent_state.current_step_index = 0

    log_stage(
        logger,
        "Plan",
        {
            "task_type": task_type,
            "steps": len(plan),
            **{f"step[{i + 1}]": f"{step['description'][:42]} -> {step.get('tool_hint')}" for i, step in enumerate(plan)},
        },
    )

    return plan


async def _direct_response_phase(goal: str, memory: AgentMemory) -> str:
    system = f"{AGENT_SYSTEM_PROMPT}\n\nToday is {_today()}."
    human = _render_prompt(
        DIRECT_RESPONSE_PROMPT,
        {
            "today": _today(),
            "chat_history": memory.format_chat_history(max_turns=12),
            "artifacts": memory.format_session_artifacts(),
            "goal": goal,
        },
    )

    llm = get_llm(temperature=0.3)
    response = await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=human)])
    return getattr(response, "content", str(response)).strip()


async def _execute_step(
    *,
    step_index: int,
    plan: List[Dict[str, Any]],
    agent_state: AgentState,
    memory: AgentMemory,
    emit: Callable[[str], Awaitable[None]],
) -> Dict[str, Any]:
    step = plan[step_index]
    step_desc = step["description"]
    hinted_tool = step.get("tool_hint")

    agent_state.plan = _plan_to_state_steps(plan)
    agent_state.current_step_index = step_index

    try:
        tool_name = await select_tool(agent_state, memory)
    except Exception as exc:
        logger.warning("Tool selection failed (%s); fallback to hint/python_auto", exc)
        tool_name = hinted_tool or "python_auto"

    tool_result: Optional[ToolResult] = None
    try:
        async for item in execute_tool(tool_name, agent_state, memory):
            if isinstance(item, ToolResult):
                tool_result = item
            elif isinstance(item, str) and item.startswith("event: done"):
                continue
            else:
                await emit(item)
    except Exception as exc:
        logger.error("Tool execution raised (%s): %s", tool_name, exc)
        tool_result = ToolResult(
            tool_name=tool_name,
            success=False,
            content=f"Tool execution failed: {exc}",
            metadata={"error": str(exc)},
        )

    if not tool_result:
        tool_result = ToolResult(
            tool_name=tool_name,
            success=False,
            content="Tool produced no result.",
            metadata={"error": "empty_tool_result"},
        )

    process_tool_result(tool_result, agent_state, memory)

    observation = {
        "tool": tool_name,
        "content": (tool_result.content or "")[:4000],
        "metadata": dict(tool_result.metadata or {}),
    }

    return {
        "tool_name": tool_name,
        "step_desc": step_desc,
        "success": bool(tool_result.success),
        "observation": observation,
        "artifacts": list(tool_result.artifacts or []),
        "sources": list((tool_result.metadata or {}).get("sources", [])),
        "summary": (tool_result.content or "")[:300],
        "error": str((tool_result.metadata or {}).get("error", "")),
    }


async def _reflect_on_failure(
    *,
    goal: str,
    step_number: int,
    total_steps: int,
    step_desc: str,
    latest_result: str,
    latest_error: str,
    observations: List[Dict[str, Any]],
    artifacts: List[Dict[str, Any]],
) -> Dict[str, Any]:
    artifacts_str = ", ".join(a.get("filename", "?") for a in artifacts) or "None"
    observations_str = "\n".join(
        f"[{o.get('tool', '?')}] {o.get('content', '')[:300]}"
        for o in observations
    )[-2000:] or "None"

    prompt = _render_prompt(
        REFLECTION_PROMPT,
        {
            "today": _today(),
            "goal": goal,
            "step_number": str(step_number),
            "total_steps": str(total_steps),
            "latest_step": step_desc,
            "success": "False",
            "latest_result": latest_result[:1500] or "No output",
            "error": latest_error or "None",
            "artifacts": artifacts_str,
            "observations": observations_str,
        },
    )

    try:
        llm = get_llm_structured(temperature=0.0)
        response = await llm.ainvoke(prompt)
        raw = getattr(response, "content", str(response)).strip()
    except Exception as exc:
        logger.warning("Reflection failed: %s", exc)
        return {"decision": "continue"}

    lower = raw.lower()
    log_stage(logger, "Reflect", {"raw": raw[:140], "step": step_number})

    if "retry_with_fix" in lower:
        new_value = _extract_after(raw, "NEW_STEPS:")
        new_desc = ""
        if new_value and not new_value.strip().startswith("["):
            new_desc = new_value.strip()
        return {"decision": "retry_with_fix", "new_description": new_desc}

    if "replan" in lower:
        raw_steps = _extract_after(raw, "NEW_STEPS:")
        if raw_steps:
            try:
                start = raw_steps.find("[")
                end = raw_steps.rfind("]")
                if start != -1 and end != -1:
                    parsed = json.loads(raw_steps[start : end + 1])
                    additions = _normalize_plan(parsed)[:3]
                    if additions:
                        return {"decision": "replan", "new_steps": additions}
            except Exception as exc:
                logger.warning("Reflection replan parse failed: %s", exc)
        return {"decision": "continue"}

    if "complete" in lower:
        return {"decision": "complete"}

    return {"decision": "continue"}


async def _synthesis_phase(
    *,
    goal: str,
    observations: List[Dict[str, Any]],
    artifacts: List[Dict[str, Any]],
    sources: List[Dict[str, Any]],
    memory: AgentMemory,
) -> str:
    observations_text = "\n---\n".join(
        f"[{o.get('tool', '?')}] {o.get('content', '')}"
        for o in observations
    )[:5000] or "No observations recorded."

    artifacts_text = ", ".join(a.get("filename", "?") for a in artifacts) if artifacts else "None"
    sources_text = "\n".join(
        f"[{i + 1}] {s.get('title', '')} - {s.get('url', '')}"
        for i, s in enumerate(sources)
    ) or "None"

    system = f"{AGENT_SYSTEM_PROMPT}\n\nToday is {_today()}."
    human = _render_prompt(
        SYNTHESIS_PROMPT,
        {
            "today": _today(),
            "goal": goal,
            "chat_history": memory.format_chat_history(max_turns=8),
            "observations": observations_text,
            "artifacts": artifacts_text,
            "sources": sources_text,
        },
    )

    llm = get_llm(temperature=0.3)
    response = await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=human)])
    return getattr(response, "content", str(response)).strip()


async def _persist_result(
    *,
    notebook_id: str,
    user_id: str,
    session_id: str,
    user_goal: str,
    final_response: str,
    meta: Dict[str, Any],
    artifacts: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    await message_store.save_user_message(
        notebook_id,
        user_id,
        session_id,
        user_goal,
        agent_meta={"intent": "AGENT"},
    )

    message_id = await message_store.save_assistant_message(
        notebook_id,
        user_id,
        session_id,
        final_response,
        meta,
    )

    for artifact in artifacts:
        artifact_id = artifact.get("id")
        if not artifact_id:
            continue
        try:
            await prisma.artifact.update(
                where={"id": artifact_id},
                data={"messageId": message_id},
            )
        except Exception as exc:
            logger.warning("Artifact link failed for %s: %s", artifact_id, exc)

    return await message_store.save_response_blocks(message_id, final_response)


async def run_agent(
    goal: str,
    notebook_id: str,
    user_id: str,
    session_id: str,
    material_ids: List[str],
    original_goal: Optional[str] = None,
) -> AsyncIterator[str]:
    """Run the production /agent pipeline and stream SSE events."""
    start_time = time.time()

    step_count = 0
    tool_calls = 0
    retry_count = 0
    finish_reason = "unknown"

    observations: List[Dict[str, Any]] = []
    artifacts: List[Dict[str, Any]] = []
    sources: List[Dict[str, Any]] = []

    task_type = "general_chat"
    final_response = ""

    try:
        log_stage(
            logger,
            "START",
            {
                "goal": goal[:72] + ("..." if len(goal) > 72 else ""),
                "user": user_id,
                "notebook": notebook_id,
                "materials": f"{len(material_ids or [])} file(s)",
            },
        )

        yield sse("agent_status", {"phase": "planning", "message": "Analysing request..."})

        agent_state = _build_agent_state(goal, user_id, notebook_id, session_id, material_ids)
        task_type, is_file_generation, _resource_profile, memory = await _analyse_phase(
            goal=goal,
            material_ids=material_ids,
            agent_state=agent_state,
        )

        yield sse("agent_status", {"phase": "planning", "message": "Creating execution plan..."})

        plan = await _planning_phase(
            goal=goal,
            task_type=task_type,
            is_file_generation=is_file_generation,
            material_ids=material_ids,
            agent_state=agent_state,
            memory=memory,
        )

        yield sse(
            "agent_plan",
            {
                "steps": [
                    {
                        "step": i + 1,
                        "description": step["description"],
                        "tool_hint": step.get("tool_hint"),
                    }
                    for i, step in enumerate(plan)
                ]
            },
        )

        if not plan:
            yield sse("agent_status", {"phase": "synthesizing", "message": "Generating response..."})
            final_response = await _direct_response_phase(goal, memory)
            for token in _chunk_text(final_response):
                yield sse_token(token)
            finish_reason = "direct_response"
        else:
            current_step = 0

            while current_step < len(plan):
                elapsed = time.time() - start_time
                if elapsed > AGENT_TIMEOUT:
                    raise TimeoutError(f"Agent timed out after {AGENT_TIMEOUT}s")
                if step_count >= MAX_STEPS or tool_calls >= MAX_TOOL_CALLS:
                    finish_reason = "execution_limits_reached"
                    break

                step = plan[current_step]
                yield sse(
                    "agent_step",
                    {
                        "step_number": current_step + 1,
                        "total_steps": len(plan),
                        "description": step["description"],
                    },
                )

                step_events: asyncio.Queue[str] = asyncio.Queue()

                async def emit_step_event(event: str) -> None:
                    await step_events.put(event)

                step_task = asyncio.create_task(
                    _execute_step(
                        step_index=current_step,
                        plan=plan,
                        agent_state=agent_state,
                        memory=memory,
                        emit=emit_step_event,
                    )
                )

                while True:
                    try:
                        item = await asyncio.wait_for(step_events.get(), timeout=15)
                        yield item
                    except asyncio.TimeoutError:
                        if step_task.done() and step_events.empty():
                            break
                        yield ": keepalive\n\n"
                        continue

                    if step_task.done() and step_events.empty():
                        break

                result = await step_task

                yield sse("agent_tool", {"tool": result["tool_name"], "step": result["step_desc"]})
                log_stage(
                    logger,
                    f"Step {current_step + 1}/{len(plan)}",
                    {"desc": result["step_desc"][:60], "tool": result["tool_name"]},
                )

                observations.append(result["observation"])
                artifacts = _merge_unique_artifacts(artifacts, result["artifacts"])
                sources.extend(result["sources"])

                step_count += 1
                tool_calls += 1

                yield sse(
                    "agent_result",
                    {
                        "tool": result["tool_name"],
                        "success": result["success"],
                        "summary": result["summary"],
                    },
                )

                log_stage(
                    logger,
                    "Result",
                    {
                        "tool": result["tool_name"],
                        "success": result["success"],
                        "artifacts": len(result["artifacts"]),
                        "preview": result["summary"][:60],
                    },
                )

                if result["success"]:
                    retry_count = 0
                    current_step += 1
                    continue

                if retry_count >= MAX_RETRIES_PER_STEP:
                    logger.warning(
                        "Max retries reached for step %d (%d). Moving to next step.",
                        current_step + 1,
                        MAX_RETRIES_PER_STEP,
                    )
                    retry_count = 0
                    current_step += 1
                    continue

                yield sse("agent_status", {"phase": "reflecting", "message": "Analyzing error and planning fix..."})
                reflection = await _reflect_on_failure(
                    goal=goal,
                    step_number=current_step + 1,
                    total_steps=len(plan),
                    step_desc=result["step_desc"],
                    latest_result=result["summary"],
                    latest_error=result["error"],
                    observations=observations,
                    artifacts=artifacts,
                )

                decision = reflection.get("decision", "continue")

                if decision == "complete":
                    finish_reason = "completed_by_reflection"
                    break

                if decision == "retry_with_fix":
                    new_desc = str(reflection.get("new_description", "")).strip()
                    if new_desc:
                        plan[current_step]["description"] = new_desc
                    retry_count += 1
                    continue

                if decision == "replan":
                    additions = _normalize_plan(reflection.get("new_steps") or [])
                    if additions:
                        plan.extend(additions)
                    retry_count = 0
                    current_step += 1
                    continue

                retry_count = 0
                current_step += 1

            if not finish_reason or finish_reason == "unknown":
                if artifacts:
                    finish_reason = "artifact_produced"
                elif is_file_generation:
                    finish_reason = "file_generation_failed"
                else:
                    finish_reason = "goal_achieved"

            if is_file_generation and artifacts:
                yield sse("agent_status", {"phase": "synthesizing", "message": "Finalizing artifact response..."})
                final_response = _build_file_generation_response(artifacts)
            else:
                yield sse("agent_status", {"phase": "synthesizing", "message": "Generating response..."})
                final_response = await _synthesis_phase(
                    goal=goal,
                    observations=observations,
                    artifacts=artifacts,
                    sources=sources,
                    memory=memory,
                )
            for token in _chunk_text(final_response):
                yield sse_token(token)

    except asyncio.CancelledError:
        logger.warning("Agent pipeline cancelled")
        return
    except Exception as exc:
        logger.error("Agent pipeline failed: %s", exc, exc_info=True)
        finish_reason = "error"
        yield sse_error(str(exc))

    elapsed = round(time.time() - start_time, 2)

    meta = {
        "intent": "AGENT",
        "task_type": task_type,
        "steps_executed": step_count,
        "tool_calls": tool_calls,
        "finish_reason": finish_reason,
        "elapsed": elapsed,
    }
    yield sse_meta(meta)

    try:
        persist_goal = original_goal if original_goal is not None else goal
        blocks = await _persist_result(
            notebook_id=notebook_id,
            user_id=user_id,
            session_id=session_id,
            user_goal=persist_goal,
            final_response=final_response,
            meta=meta,
            artifacts=artifacts,
        )
        if blocks:
            yield sse_blocks(blocks)
    except Exception as exc:
        logger.error("Agent persistence failed: %s", exc)

    yield sse(
        "agent_done",
        {
            "finish_reason": finish_reason,
            "steps_executed": step_count,
            "tool_calls": tool_calls,
        },
    )

    log_stage(
        logger,
        "COMPLETE",
        {
            "task_type": task_type,
            "finish_reason": finish_reason,
            "steps": step_count,
            "tool_calls": tool_calls,
            "artifacts": len(artifacts),
            "elapsed": f"{elapsed:.2f}s",
        },
    )

    yield sse_done({"elapsed": elapsed, **meta})
