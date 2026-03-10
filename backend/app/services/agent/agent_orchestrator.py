from __future__ import annotations

import asyncio
import logging
import time
from typing import AsyncIterator, List

from app.db.prisma_client import prisma
from app.services.chat_v2 import message_store
from app.services.chat_v2.schemas import ToolResult
from app.services.chat_v2.streaming import (
    sse,
    sse_done,
    sse_error,
    sse_meta,
    sse_token,
    sse_blocks,
)
from app.services.llm_service.llm import get_llm, extract_chunk_content

from .executor import execute_tool, process_tool_result
from .memory import AgentMemory
from .planner import create_plan
from .prompts import SYNTHESIS_PROMPT
from .reflection import ReflectionAction, reflect
from .resource_router import classify_materials
from .artifact_executor import detect_file_generation_intent
from .state import AgentState, StepStatus
from .tool_selector import select_tool

logger = logging.getLogger(__name__)

MAX_AGENT_STEPS = 10
MAX_TOOL_CALLS = 20
MAX_EXECUTION_TIME = 180  # seconds
MAX_RETRIES_PER_STEP = 2


def _sse_agent(event_type: str, data) -> str:
    return sse(f"agent_{event_type}", data)


async def run_agent(
    goal: str,
    notebook_id: str,
    user_id: str,
    session_id: str,
    material_ids: List[str],
) -> AsyncIterator[str]:
    """Main agent execution loop. Yields SSE events."""
    start_time = time.time()

    state = AgentState(
        goal=goal,
        user_id=user_id,
        notebook_id=notebook_id,
        session_id=session_id,
        material_ids=material_ids or [],
    )

    memory = AgentMemory(state)
    await memory.load_chat_history()

    # ── Phase 0: Resource Classification ──────────────────────────────
    yield _sse_agent("status", {"phase": "routing", "message": "Classifying resources…"})

    resource_profile = await classify_materials(state.material_ids)
    state.resource_profile = resource_profile
    state.is_file_generation = detect_file_generation_intent(goal)

    logger.info(
        "Resource profile: %s | file_generation=%s",
        resource_profile.summary(),
        state.is_file_generation,
    )

    # ── Phase 1: Planning ─────────────────────────────────────────────
    yield _sse_agent("status", {"phase": "planning", "message": "Creating execution plan…"})

    try:
        plan = await create_plan(state, memory)
    except Exception as exc:
        logger.error("Agent planner failed: %s", exc)
        yield sse_error(f"Agent planning failed: {exc}")
        yield sse_done({"elapsed": _elapsed(start_time)})
        return

    plan_data = [
        {"step": i + 1, "description": s.description, "tool_hint": s.tool_hint}
        for i, s in enumerate(plan)
    ]
    yield _sse_agent("plan", {"steps": plan_data})

    # ── Phase 2: Execution Loop ───────────────────────────────────────
    step_count = 0
    retry_count = 0
    failed_tools_for_step: set[str] = set()

    while not state.finished:
        # Safety limits
        if step_count >= MAX_AGENT_STEPS:
            state.finished = True
            state.finish_reason = "max_steps_reached"
            yield _sse_agent("status", {"phase": "limit", "message": "Maximum steps reached."})
            break

        if state.total_tool_calls >= MAX_TOOL_CALLS:
            state.finished = True
            state.finish_reason = "max_tool_calls_reached"
            yield _sse_agent("status", {"phase": "limit", "message": "Maximum tool calls reached."})
            break

        if _elapsed(start_time) > MAX_EXECUTION_TIME:
            state.finished = True
            state.finish_reason = "timeout"
            yield _sse_agent("status", {"phase": "timeout", "message": "Execution time limit reached."})
            break

        step = state.current_step
        if not step:
            state.finished = True
            state.finish_reason = "plan_complete"
            break

        step_count += 1
        step.status = StepStatus.RUNNING

        yield _sse_agent("step", {
            "step_number": state.current_step_index + 1,
            "total_steps": len(state.plan),
            "description": step.description,
        })

        # ── Tool Selection ────────────────────────────────────────
        try:
            tool_name = await select_tool(state, memory)
        except Exception as exc:
            logger.error("Tool selection failed: %s", exc)
            state.mark_current(StepStatus.FAILED, error=str(exc))
            state.advance()
            retry_count = 0
            failed_tools_for_step = set()
            continue

        yield _sse_agent("tool", {"tool": tool_name, "step": step.description})

        # ── Tool Execution ────────────────────────────────────────
        tool_result = None
        try:
            async for item in execute_tool(tool_name, state, memory):
                if isinstance(item, ToolResult):
                    tool_result = item
                else:
                    yield item
        except Exception as exc:
            logger.error("Tool execution failed: %s", exc)
            tool_result = ToolResult(
                tool_name=tool_name,
                success=False,
                content=f"Tool execution error: {exc}",
                metadata={"error": str(exc)},
            )

        if tool_result:
            process_tool_result(tool_result, state, memory)
            yield _sse_agent("result", {
                "tool": tool_name,
                "success": tool_result.success,
                "summary": tool_result.content[:300] if tool_result.content else "",
            })

            # Early termination: only for explicit file-generation goals on the last step.
            # For analysis tasks, let all steps run so synthesis gets real observations.
            is_last_step = (state.current_step_index >= len(state.plan) - 1)
            if (tool_result.artifacts and tool_result.success
                    and state.is_file_generation and is_last_step):
                logger.info(
                    "File-gen artifacts produced (%d file(s)); terminating agent early.",
                    len(tool_result.artifacts),
                )
                state.mark_current(StepStatus.COMPLETED, result="File(s) generated successfully.")
                state.finished = True
                state.finish_reason = "artifact_produced"
                break

        # ── Reflection ────────────────────────────────────────────
        try:
            ref = await reflect(state, memory)
        except Exception as exc:
            logger.error("Reflection failed: %s", exc)
            state.advance()
            retry_count = 0
            failed_tools_for_step = set()
            continue

        yield _sse_agent("reflection", {
            "step_succeeded": ref.step_succeeded,
            "goal_achieved": ref.goal_achieved,
            "action": ref.action.value,
            "reason": ref.reason,
        })

        if ref.action == ReflectionAction.COMPLETE:
            state.finished = True
            state.finish_reason = "goal_achieved"
            break
        elif ref.action == ReflectionAction.ABORT:
            state.finished = True
            state.finish_reason = "aborted"
            break
        elif ref.action == ReflectionAction.RETRY:
            retry_count += 1
            failed_tools_for_step.add(tool_name)

            if retry_count > MAX_RETRIES_PER_STEP:
                logger.info(
                    "Max retries (%d) for step '%s'; advancing to next step.",
                    MAX_RETRIES_PER_STEP,
                    step.description[:60],
                )
                state.mark_current(StepStatus.FAILED, error="Max retries exceeded")
                state.advance()
                retry_count = 0
                failed_tools_for_step = set()
            else:
                # On retry, clear the tool_hint so tool_selector can pick
                # an alternative tool instead of blindly retrying the same one
                if step.tool_hint in failed_tools_for_step:
                    step.tool_hint = None
                    logger.info(
                        "Cleared tool_hint after failure of '%s'; will re-select tool.",
                        tool_name,
                    )
        else:
            # CONTINUE
            retry_count = 0
            failed_tools_for_step = set()
            state.advance()

    # ── Phase 3: Synthesis ────────────────────────────────────────────
    yield _sse_agent("status", {"phase": "synthesizing", "message": "Generating final response…"})

    # If file artifacts were produced, use a brief message instead of full LLM synthesis
    if state.finish_reason == "artifact_produced" and state.artifacts:
        filenames = ", ".join(a.get("filename", "file") for a in state.artifacts)
        final_response = f"Here are your generated files: **{filenames}**\n\nYou can download them using the buttons above."
    else:
        final_response = await _synthesize(state, memory)

    for token in _chunk_text(final_response, chunk_size=40):
        yield sse_token(token)

    elapsed = _elapsed(start_time)

    # ── Phase 4: Persistence ──────────────────────────────────────────
    meta = {
        "intent": "AGENT",
        "steps_executed": step_count,
        "tool_calls": state.total_tool_calls,
        "finish_reason": state.finish_reason,
        "elapsed": elapsed,
    }
    yield sse_meta(meta)

    try:
        await message_store.save_user_message(notebook_id, user_id, session_id, goal)

        msg_id = await message_store.save_assistant_message(
            notebook_id, user_id, session_id, final_response, meta,
        )

        # Link generated artifacts to this message for history reload
        for art in state.artifacts:
            art_id = art.get("id")
            if art_id:
                try:
                    await prisma.artifact.update(
                        where={"id": art_id},
                        data={"messageId": msg_id},
                    )
                except Exception as link_exc:
                    logger.warning("Failed to link artifact %s to message: %s", art_id, link_exc)

        blocks = await message_store.save_response_blocks(msg_id, final_response)
        if blocks:
            yield sse_blocks(blocks)
    except Exception as exc:
        logger.error("Agent persistence failed: %s", exc)

    yield _sse_agent("done", {
        "finish_reason": state.finish_reason,
        "steps_executed": step_count,
        "tool_calls": state.total_tool_calls,
    })
    yield sse_done({"elapsed": elapsed, **meta})


async def _synthesize(state: AgentState, memory: AgentMemory) -> str:
    """Generate a final synthesis response from all observations."""
    execution_summary = state.completed_steps_summary()
    observations = state.summary_of_observations(max_chars=5000)
    artifacts = ", ".join(a.get("filename", "?") for a in state.artifacts) or "None"
    sources = "\n".join(
        f"[{i+1}] {s.get('title', '')} - {s.get('url', '')}"
        for i, s in enumerate(state.sources)
    ) or "None"

    prompt = SYNTHESIS_PROMPT.format(
        goal=state.goal,
        execution_summary=execution_summary or "All steps completed.",
        observations=observations or "No observations recorded.",
        artifacts=artifacts,
        sources=sources,
    )

    llm = get_llm(temperature=0.3)
    response = await llm.ainvoke(prompt)
    return getattr(response, "content", str(response)).strip()


def _elapsed(start: float) -> float:
    return round(time.time() - start, 2)


def _chunk_text(text: str, chunk_size: int = 40) -> List[str]:
    """Break text into small chunks for token-like streaming."""
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i + chunk_size])
    return chunks
