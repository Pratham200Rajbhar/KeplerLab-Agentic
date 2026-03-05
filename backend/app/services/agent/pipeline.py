"""Agent pipeline — multi-step autonomous task execution.

Orchestrates: Plan → Execute Loop → Reflect → Synthesize → Persist.
All output is streamed as SSE events.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
import time
from typing import Any, AsyncIterator, Dict, List, Optional

from app.core.config import settings
from app.services.agent.schemas import (
    AgentPlan,
    AgentState,
    PlanStep,
    ReflectionDecision,
    ReflectionResult,
    StepResult,
)
from app.services.agent.tools import (
    TOOL_REGISTRY,
    AgentContext,
    ToolOutput,
    classify_artifact,
)

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────

MAX_ITERATIONS = 10
TOKEN_BUDGET = 50000
MAX_PLAN_RETRIES = 2


def _sse(event: str, data: Any) -> str:
    """Format a single SSE event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# ── Main Pipeline ─────────────────────────────────────────────


async def stream_agent(
    *,
    message: str,
    notebook_id: str,
    material_ids: List[str],
    session_id: str,
    user_id: str,
) -> AsyncIterator[str]:
    """Run the full agent pipeline, yielding SSE events.

    Steps:
      1. Plan (LLM generates a JSON plan of tool steps)
      2. Execute loop (run each tool, emitting events)
      3. Reflect after each step (continue or respond?)
      4. Synthesize (LLM produces final answer from all results)
      5. Persist (save to DB)
    """
    start_time = time.time()

    # Create workspace directory
    work_dir = tempfile.mkdtemp(prefix="kepler_agent_")

    ctx = AgentContext(
        user_id=user_id,
        notebook_id=notebook_id,
        session_id=session_id,
        material_ids=material_ids,
        message=message,
        work_dir=work_dir,
    )

    state = AgentState(max_iterations=MAX_ITERATIONS, token_budget=TOKEN_BUDGET)

    try:
        # ── STEP 1: PLAN ─────────────────────────────────────
        plan = await _generate_plan(message, material_ids)
        if not plan or not plan.steps:
            yield _sse("error", {"error": "Agent could not generate a valid plan."})
            return

        state.plan = plan

        yield _sse("agent_start", {
            "plan": [
                {"tool": s.tool, "description": s.description, "step": i}
                for i, s in enumerate(plan.steps)
            ],
            "total_steps": len(plan.steps),
        })

        # ── STEP 2–4: EXECUTE LOOP + REFLECT ─────────────────
        for step_idx, step in enumerate(plan.steps):
            if state.iteration >= state.max_iterations:
                break
            if state.total_tokens >= state.token_budget:
                break

            state.iteration += 1

            # Emit tool_start
            yield _sse("tool_start", {
                "tool": step.tool,
                "label": step.description,
                "step": step_idx,
            })

            # Execute tool
            step_start = time.time()
            result = await _execute_tool(step, ctx, state)
            duration_ms = int((time.time() - step_start) * 1000)

            # Build step result
            step_result = StepResult(
                step_index=step_idx,
                tool=step.tool,
                description=step.description,
                summary=result.summary,
                duration_ms=duration_ms,
                code=result.code,
                artifacts=[a for a in result.artifacts],
                error=result.error,
            )
            state.step_results.append(step_result)

            if step.tool not in state.tools_used:
                state.tools_used.append(step.tool)

            # Emit code_generated if python_tool produced code
            if result.code and step.tool == "python_tool":
                yield _sse("code_generated", {
                    "step_index": step_idx,
                    "code": result.code,
                    "language": "python",
                })

            # Emit artifacts
            for art in result.artifacts:
                artifact_event = await _register_artifact(art, ctx)
                if artifact_event:
                    state.artifacts.append(artifact_event)
                    yield _sse("artifact", artifact_event)

            # Emit tool_result
            yield _sse("tool_result", {
                "summary": result.summary,
                "duration_ms": duration_ms,
                "step": step_idx,
            })

            # ── STEP 3: REFLECT ───────────────────────────────
            reflection = await _reflect(message, state)
            if reflection.decision == ReflectionDecision.RESPOND:
                break

        # ── STEP 5: SYNTHESIZE ────────────────────────────────
        async for token_event in _synthesize(message, state, ctx):
            yield token_event

        # ── STEP 6: EMIT DONE ─────────────────────────────────
        elapsed = time.time() - start_time
        yield _sse("done", {
            "intent": "AGENT",
            "tools_used": state.tools_used,
            "steps": len(state.step_results),
            "tokens_used": state.total_tokens,
            "elapsed": round(elapsed, 2),
        })

    except Exception as e:
        logger.error("[agent] Pipeline error: %s", e, exc_info=True)
        yield _sse("error", {"error": str(e)})
    finally:
        # Cleanup workspace
        try:
            import shutil
            if os.path.isdir(work_dir):
                shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass


# ── Plan generation ───────────────────────────────────────────


async def _generate_plan(message: str, material_ids: List[str]) -> Optional[AgentPlan]:
    """Call LLM with structured output to generate a tool execution plan."""
    from app.services.llm_service.llm import get_llm
    from app.services.llm_service.structured_invoker import async_invoke_structured_safe

    has_materials = bool(material_ids)

    tools_description = """Available tools:
- rag_tool: Search user's uploaded materials for relevant information. Input: {"query": "search query"}
- python_tool: Generate and run Python code to analyze data, create charts, or compute results. Input: {"task": "description of what to code"}
- web_search_tool: Search the web for current information. Input: {"query": "search query"}  
- research_tool: Do deep multi-step web research. Input: {"query": "research question"}"""

    system_prompt = f"""You are a task planner for an AI assistant. Given a user request, 
produce a JSON plan of tool steps to fulfill it.

{tools_description}

Rules:
- Use rag_tool FIRST if the user likely needs info from their uploaded documents{" (materials are available)" if has_materials else " (no materials uploaded — skip rag_tool)"}.
- Use python_tool when computation, data analysis, or file generation is needed.
- Use web_search_tool for quick factual lookups from the internet.
- Use research_tool only for deep, multi-source research questions.
- Keep plans concise: 1-5 steps typically. Don't over-plan.
- Return ONLY valid JSON matching this schema:
  {{"steps": [{{"tool": "tool_name", "description": "what this step does", "inputs": {{...}}}}]}}
"""

    prompt = f"{system_prompt}\n\nUser request: {message}\n\nProduce the JSON plan:"

    result = await async_invoke_structured_safe(prompt, AgentPlan)

    if result.get("success") and result.get("data"):
        data = result["data"]
        # async_invoke_structured_safe returns model_dump() dict, not the model
        if isinstance(data, dict):
            return AgentPlan(**data)
        return data

    # Fallback: simple single-step plan
    logger.warning("[agent] Plan generation failed, using fallback. Error: %s", result.get("error"))
    if has_materials:
        return AgentPlan(steps=[
            PlanStep(tool="rag_tool", description="Search materials for relevant information", inputs={"query": message}),
        ])
    else:
        return AgentPlan(steps=[
            PlanStep(tool="web_search_tool", description="Search the web for information", inputs={"query": message}),
        ])


# ── Tool execution ────────────────────────────────────────────


async def _execute_tool(step: PlanStep, ctx: AgentContext, state: AgentState) -> ToolOutput:
    """Execute a single tool step."""
    tool_fn = TOOL_REGISTRY.get(step.tool)
    if not tool_fn:
        return ToolOutput(summary=f"Unknown tool: {step.tool}", error="Tool not found")

    # Enrich inputs with context from previous steps
    inputs = dict(step.inputs)

    # If there's RAG context from a previous step, inject it
    for prev in state.step_results:
        if prev.tool == "rag_tool" and not prev.error:
            # Find the data in the result
            if "context" not in inputs:
                # Add context from previous RAG step for python/research tools
                if step.tool in ("python_tool", "research_tool"):
                    for sr in state.step_results:
                        if sr.tool == "rag_tool":
                            inputs.setdefault("context", sr.summary)
                            break

    try:
        if step.tool == "python_tool":
            # python_tool needs special handling for events
            return await tool_fn(inputs, ctx)
        else:
            return await tool_fn(inputs, ctx)
    except Exception as e:
        logger.error("[agent] Tool %s failed: %s", step.tool, e)
        return ToolOutput(summary=f"Tool {step.tool} failed: {e}", error=str(e))


# ── Reflection ────────────────────────────────────────────────


async def _reflect(message: str, state: AgentState) -> ReflectionResult:
    """Decide whether to continue executing steps or synthesize a response."""
    # Hard limits
    if state.iteration >= state.max_iterations:
        return ReflectionResult(
            decision=ReflectionDecision.RESPOND,
            reason="Max iterations reached",
        )
    if state.total_tokens >= state.token_budget:
        return ReflectionResult(
            decision=ReflectionDecision.RESPOND,
            reason="Token budget exceeded",
        )

    # If we've completed all planned steps, respond
    if state.plan and state.iteration >= len(state.plan.steps):
        return ReflectionResult(
            decision=ReflectionDecision.RESPOND,
            reason="All planned steps completed",
        )

    # If last step had an error, try to continue with remaining steps
    if state.step_results and state.step_results[-1].error:
        # Don't stop on error — try remaining steps
        return ReflectionResult(
            decision=ReflectionDecision.CONTINUE,
            reason="Previous step had error, continuing with plan",
        )

    # Otherwise continue with planned steps
    return ReflectionResult(
        decision=ReflectionDecision.CONTINUE,
        reason="More planned steps remain",
    )


# ── Synthesis ─────────────────────────────────────────────────


async def _synthesize(
    message: str,
    state: AgentState,
    ctx: AgentContext,
) -> AsyncIterator[str]:
    """Call LLM to produce the final answer from all tool results. Stream tokens."""
    from app.services.llm_service.llm import get_llm

    # Build context from all tool results
    tool_context_parts = []
    for sr in state.step_results:
        part = f"[{sr.tool}] {sr.description}\nResult: {sr.summary}"
        if sr.code:
            part += f"\nCode used:\n```python\n{sr.code[:500]}\n```"
        tool_context_parts.append(part)

    tool_context = "\n\n".join(tool_context_parts)

    system_prompt = """You are a helpful AI assistant. The agent has executed several tools 
to gather information. Using the tool results below, provide a clear, comprehensive answer 
to the user's question.

Rules:
- Synthesize information from ALL tool results
- Be specific and cite what was found
- If code was executed, summarize the OUTPUT (do not show the code)
- If research was done, include key findings
- Use markdown formatting for clarity
- Do NOT mention tool names or internal processes to the user"""

    prompt = f"""{system_prompt}

Tool Results:
{tool_context}

User Question: {message}

Provide your answer:"""

    llm = get_llm(temperature=settings.LLM_TEMPERATURE_CHAT)

    try:
        async for chunk in llm.astream(prompt):
            content = getattr(chunk, "content", str(chunk))
            if content:
                yield _sse("token", {"content": content})
    except Exception as e:
        logger.error("[agent] Synthesis failed: %s", e)
        yield _sse("token", {"content": f"\n\nI encountered an error synthesizing the results: {e}"})


# ── Artifact registration ─────────────────────────────────────


async def _register_artifact(
    art: Dict[str, Any],
    ctx: AgentContext,
) -> Optional[Dict[str, Any]]:
    """Register an artifact in the database and return the SSE payload."""
    from app.db.prisma_client import prisma
    import secrets
    from datetime import datetime, timedelta, timezone

    fpath = art.get("path", "")
    if not fpath or not os.path.isfile(fpath):
        return None

    filename = art.get("filename", os.path.basename(fpath))
    mime = art.get("mime", "application/octet-stream")
    display_type = art.get("display_type", classify_artifact(filename, mime))
    size = art.get("size", os.path.getsize(fpath))

    # Generate download token
    token = secrets.token_urlsafe(48)
    expiry = datetime.now(timezone.utc) + timedelta(hours=settings.ARTIFACT_TOKEN_EXPIRY_HOURS)

    try:
        record = await prisma.artifact.create(
            data={
                "userId": ctx.user_id,
                "notebookId": ctx.notebook_id,
                "sessionId": ctx.session_id,
                "filename": filename,
                "mimeType": mime,
                "displayType": display_type,
                "sizeBytes": size,
                "downloadToken": token,
                "tokenExpiry": expiry,
                "workspacePath": fpath,
            }
        )

        return {
            "filename": filename,
            "mime": mime,
            "display_type": display_type,
            "url": f"/workspace/file/{record.id}?token={token}",
            "size": size,
        }
    except Exception as e:
        logger.error("[agent] Failed to register artifact: %s", e)
        return {
            "filename": filename,
            "mime": mime,
            "display_type": display_type,
            "url": "",
            "size": size,
        }
