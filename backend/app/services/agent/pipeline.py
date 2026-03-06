"""Agent Pipeline — Multi-step autonomous task execution.

Orchestrates the full agent execution lifecycle:
1. Intent Detection
2. Task Planning  
3. Tool Selection
4. Execution Engine
5. Artifact Detection
6. Result Validation
7. Response Generation

All output is streamed as SSE events for real-time UI updates.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import secrets
import tempfile
import time
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

from app.core.config import settings
from app.db.prisma_client import prisma

from app.services.agent.state import (
    AgentExecutionState,
    ExecutionPhase,
    create_agent_state,
)
from app.services.agent.dataset_profiler import (
    DatasetProfiler,
    DatasetProfile,
    build_combined_profile_context,
)
from app.services.agent.tool_selector import (
    TaskType,
    classify_task,
    generate_execution_plan,
)
from app.services.agent.execution_engine import (
    ExecutionEngine,
    ExecutionResult,
)
from app.services.agent.artifact_detector import ArtifactDetector
from app.services.agent.result_validator import (
    ResultValidator,
    SummaryGenerator,
    generate_result_text,
)
from app.services.agent.tools import AgentContext, TOOL_REGISTRY

# Legacy imports for backward compatibility
from app.services.agent.schemas import (
    AgentPlan,
    AgentState as LegacyAgentState,
    PlanStep,
    ReflectionDecision,
    ReflectionResult,
    StepResult,
)
from app.services.agent.tools import classify_artifact, ToolOutput

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────

MAX_ITERATIONS = 10
TOKEN_BUDGET = 50000
MAX_PLAN_RETRIES = 2
MAX_REPAIR_ATTEMPTS = 3


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

    Enhanced execution lifecycle:
      1. Initialize agent state and workspace
      2. Detect intent and classify task
      3. Generate execution plan with tool selection
      4. Execute steps with progress streaming
      5. Detect and register artifacts
      6. Validate results
      7. Synthesize final response
      8. Persist execution metadata

    Args:
        message: User's request/query
        notebook_id: ID of the current notebook
        material_ids: IDs of uploaded materials
        session_id: Current session ID
        user_id: Current user ID

    Yields:
        SSE events for real-time frontend updates
    """
    start_time = time.time()

    # Create workspace directory
    work_dir = tempfile.mkdtemp(prefix="kepler_agent_")

    # Initialize enhanced agent state
    state = create_agent_state(
        session_id=session_id,
        user_id=user_id,
        notebook_id=notebook_id,
        user_query=message,
        work_dir=work_dir,
        max_iterations=MAX_ITERATIONS,
        max_retries=MAX_REPAIR_ATTEMPTS,
    )
    state.mark_started()

    # Create execution context
    ctx = AgentContext(
        user_id=user_id,
        notebook_id=notebook_id,
        session_id=session_id,
        material_ids=material_ids,
        message=message,
        work_dir=work_dir,
    )

    try:
        # ── STEP 1: INTENT DETECTION ─────────────────────────
        yield _sse("step", {
            "status": "Understanding request",
            "phase": "planning",
        })

        has_materials = bool(material_ids)
        classification = classify_task(message, has_materials)
        
        state.detected_intent = classification.task_type.value
        state.intent_confidence = classification.confidence

        yield _sse("intent", {
            "task_type": classification.task_type.value,
            "confidence": classification.confidence,
            "requires_computation": classification.requires_computation,
            "requires_materials": classification.requires_materials,
        })

        # ── STEP 1.5: DATASET PROFILING ──────────────────────
        # For data-related tasks, profile datasets BEFORE planning
        # so the LLM has actual data characteristics for reasoning.
        dataset_profiles: List[DatasetProfile] = []
        if classification.requires_computation and material_ids:
            yield _sse("step", {
                "status": "Profiling datasets",
                "phase": "profiling",
            })

            try:
                profiler = DatasetProfiler(
                    material_ids=material_ids,
                    user_id=user_id,
                    work_dir=work_dir,
                )
                dataset_profiles = await profiler.profile_all()

                if dataset_profiles:
                    # Store profile context in state for all downstream use
                    profile_context = build_combined_profile_context(dataset_profiles)
                    state.dataset_profile_context = profile_context

                    # Also populate datasets list with enriched metadata
                    from app.services.agent.state import DatasetMetadata
                    for dp in dataset_profiles:
                        if dp.profiling_error:
                            continue
                        ds_meta = DatasetMetadata(
                            name=dp.name,
                            rows=dp.rows,
                            columns=dp.columns,
                            column_names=[cp.name for cp in dp.column_profiles],
                            dtypes={cp.name: cp.dtype for cp in dp.column_profiles},
                            missing_values={
                                cp.name: cp.missing_count
                                for cp in dp.column_profiles
                                if cp.missing_count > 0
                            },
                            numeric_columns=dp.numeric_columns,
                            categorical_columns=dp.categorical_columns,
                            datetime_columns=dp.datetime_columns,
                            correlations=dp.correlations,
                            top_correlations=[
                                {"col1": c1, "col2": c2, "value": v}
                                for c1, c2, v in dp.top_correlations
                            ],
                            sample_rows=dp.sample_rows,
                            profile_context=dp.to_context_string(),
                        )
                        state.add_dataset(ds_meta)

                    yield _sse("dataset_profile", {
                        "datasets_profiled": len(dataset_profiles),
                        "profiles": [
                            {
                                "name": dp.name,
                                "rows": dp.rows,
                                "columns": dp.columns,
                                "numeric_columns": dp.numeric_columns,
                                "categorical_columns": dp.categorical_columns,
                                "missing_summary": {
                                    cp.name: f"{cp.missing_pct:.1f}%"
                                    for cp in dp.column_profiles
                                    if cp.missing_count > 0
                                },
                            }
                            for dp in dataset_profiles
                            if not dp.profiling_error
                        ],
                    })
                    logger.info(
                        "[agent] Profiled %d dataset(s) for session %s",
                        len(dataset_profiles), session_id,
                    )
            except Exception as exc:
                logger.warning("[agent] Dataset profiling failed: %s", exc)
                yield _sse("step", {
                    "status": "Dataset profiling skipped",
                    "phase": "profiling",
                    "warning": str(exc),
                })

        # ── STEP 2: TASK PLANNING ────────────────────────────
        yield _sse("step", {
            "status": "Planning execution",
            "phase": "planning",
        })

        plan_steps = await generate_execution_plan(
            query=message,
            material_ids=material_ids,
            context=state.get_context_summary(),
        )

        if not plan_steps:
            yield _sse("error", {"error": "Failed to generate execution plan"})
            return

        state.execution_plan = plan_steps
        state.phase = ExecutionPhase.EXECUTING

        yield _sse("agent_start", {
            "plan": [
                {
                    "tool": step.get("tool"),
                    "description": step.get("description"),
                    "step": i,
                }
                for i, step in enumerate(plan_steps)
            ],
            "total_steps": len(plan_steps),
            "intent": state.detected_intent,
        })

        # ── STEP 3: EXECUTE STEPS ────────────────────────────
        execution_engine = ExecutionEngine(state, ctx)
        
        # Set up event callback for streaming
        async def emit_event(event: str, data: Dict[str, Any]) -> None:
            # This is called by the engine but we can't yield from here
            # Events are emitted in the main loop instead
            pass
        
        execution_engine.set_event_callback(emit_event)

        for step_idx, step in enumerate(plan_steps):
            # Check iteration limits
            if state.iteration >= state.max_iterations:
                yield _sse("step", {
                    "status": "Max iterations reached",
                    "step": step_idx,
                })
                break

            state.iteration += 1
            tool = step.get("tool", "python_tool")
            description = step.get("description", "Executing step")
            inputs = step.get("inputs", {})

            # Emit step start
            yield _sse("step", {
                "status": description,
                "step": step_idx,
                "tool": tool,
                "phase": "executing",
            })

            # Execute step
            result = await execution_engine.execute_step(
                step_index=step_idx,
                tool=tool,
                description=description,
                inputs=inputs,
            )

            # Emit code if generated
            if result.code:
                yield _sse("code_generated", {
                    "step_index": step_idx,
                    "code": result.code,
                    "language": "python",
                })

            # Emit artifacts
            for artifact in result.artifacts:
                registered = await _register_artifact(artifact, ctx, state)
                if registered:
                    yield _sse("artifact", registered)

            # Emit step result
            yield _sse("tool_result", {
                "step": step_idx,
                "tool": tool,
                "summary": result.summary,
                "success": result.success,
                "duration_ms": result.duration_ms,
            })

            # Check for reflection/early termination
            if result.success and _should_stop_early(state, result):
                break

        # ── STEP 4: VALIDATE RESULTS ─────────────────────────
        state.phase = ExecutionPhase.REFLECTING
        
        yield _sse("step", {
            "status": "Validating results",
            "phase": "validating",
        })

        validator = ResultValidator(state)
        validation = validator.validate()

        if validation.warnings:
            yield _sse("validation", {
                "warnings": validation.warnings,
                "suggestions": validation.suggestions,
            })

        # ── STEP 5: GENERATE SUMMARY ─────────────────────────
        summary_gen = SummaryGenerator(state)
        summary = summary_gen.generate_summary()

        yield _sse("summary", {
            "title": summary.title,
            "description": summary.description,
            "key_results": summary.key_results,
            "metrics": summary.metrics,
            "artifacts": summary.artifacts_summary,
        })

        # ── STEP 6: SYNTHESIZE RESPONSE ──────────────────────
        state.phase = ExecutionPhase.SYNTHESIZING
        
        yield _sse("step", {
            "status": "Preparing response",
            "phase": "synthesizing",
        })

        async for token_event in _synthesize_response(message, state, ctx):
            yield token_event

        # ── STEP 7: COMPLETION ───────────────────────────────
        state.mark_completed(success=True)

        yield _sse("done", {
            "intent": state.detected_intent,
            "tools_used": state.tools_used,
            "steps": len(state.step_progress),
            "artifacts_count": len(state.artifacts),
            "elapsed": state.elapsed_seconds,
            "success": True,
        })

        # Persist execution log
        await _persist_execution(state)

    except Exception as e:
        logger.error("[agent] Pipeline error: %s", e, exc_info=True)
        state.mark_completed(success=False)
        yield _sse("error", {"error": str(e)})

    finally:
        # Workspace cleanup is handled by the caller or scheduled cleanup
        # Don't delete immediately as artifacts may still be needed
        pass


# ── Helper Functions ──────────────────────────────────────────


def _should_stop_early(state: AgentExecutionState, result: ExecutionResult) -> bool:
    """Decide if we should stop execution early.
    
    Conditions for early stop:
    - All planned steps completed
    - Sufficient results gathered
    - Repeated errors detected
    """
    # If all planned steps are done
    if state.current_step_index >= len(state.execution_plan) - 1:
        return True
    
    # If we have good results and artifacts
    if result.success and state.artifacts and state.models:
        return True
    
    # If errors are repeating
    if state.is_error_repeated():
        return True
    
    return False


async def _synthesize_response(
    message: str,
    state: AgentExecutionState,
    ctx: AgentContext,
) -> AsyncIterator[str]:
    """Synthesize final response using LLM. Streams tokens."""
    from app.services.llm_service.llm import get_llm
    from app.services.agent.result_validator import generate_result_text

    # Build context from execution
    result_context = generate_result_text(state)

    system_prompt = """You are a helpful AI assistant that has just completed a data analysis/ML task.
Based on the execution results below, provide a clear, friendly response to the user.

Guidelines:
- Summarize what was accomplished in plain language
- Highlight key findings and metrics
- Mention generated files/charts
- Be specific about accuracy, counts, etc.
- Do NOT show code unless asked
- Do NOT mention internal tool names
- Use markdown formatting for clarity
- Keep the response focused and concise"""

    prompt = f"""{system_prompt}

{result_context}

User's original request: {message}

Provide a helpful response:"""

    llm = get_llm(temperature=settings.LLM_TEMPERATURE_CHAT)

    try:
        async for chunk in llm.astream(prompt):
            content = getattr(chunk, "content", str(chunk))
            if content:
                yield _sse("token", {"content": content})
    except Exception as e:
        logger.error("[agent] Synthesis failed: %s", e)
        yield _sse("token", {"content": f"\n\nI completed the analysis but encountered an issue generating the summary: {e}"})


_DISPLAY_TYPE_TO_CATEGORY: Dict[str, str] = {
    "image":        "charts",
    "csv_table":    "datasets",
    "json_tree":    "datasets",
    "text_preview": "reports",
    "html_preview": "reports",
    "pdf_embed":    "reports",
}

_MODEL_EXTENSIONS = {
    ".pkl", ".pickle", ".joblib",
    ".h5", ".pt", ".pth", ".onnx", ".pb", ".keras",
}


def _derive_category(display_type: str, filename: str) -> str:
    """Compute a meaningful artifact category from display_type and filename."""
    ext = os.path.splitext(filename)[1].lower()
    if ext in _MODEL_EXTENSIONS:
        return "models"
    return _DISPLAY_TYPE_TO_CATEGORY.get(display_type, "files")


async def _register_artifact(
    art: Dict[str, Any],
    ctx: AgentContext,
    state: AgentExecutionState,
) -> Optional[Dict[str, Any]]:
    """Register an artifact in the database and return SSE payload."""
    fpath = art.get("path", "")
    if not fpath or not os.path.isfile(fpath):
        return None

    filename = art.get("filename", os.path.basename(fpath))
    mime = art.get("mime", "application/octet-stream")
    display_type = art.get("display_type", classify_artifact(filename, mime))
    # Derive category from display_type/extension; fall back to any explicit value
    # already set on the artifact (e.g. by a future tool that knows its category).
    category = art.get("category") or _derive_category(display_type, filename)
    size = art.get("size", os.path.getsize(fpath))

    # Generate secure download token
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

        artifact_data = {
            "id": record.id,
            "filename": filename,
            "mime": mime,
            "category": category,
            "display_type": display_type,
            "url": f"/agent/file/{record.id}?token={token}",
            "size": size,
            "workspace_path": fpath,
        }

        # Add to state
        state.add_artifact(artifact_data)

        return artifact_data

    except Exception as e:
        logger.error("[agent] Failed to register artifact: %s", e)
        return {
            "filename": filename,
            "mime": mime,
            "category": category,
            "display_type": display_type,
            "url": "",
            "size": size,
            "workspace_path": fpath,
        }


async def _persist_execution(state: AgentExecutionState) -> None:
    """Persist execution metadata to database."""
    try:
        await prisma.agentexecutionlog.create(
            data={
                "userId": state.user_id,
                "notebookId": state.notebook_id,
                "intent": state.detected_intent,
                "confidence": state.intent_confidence,
                "toolsUsed": state.tools_used,
                "stepsCount": len(state.step_progress),
                "tokensUsed": state.total_tokens,
                "elapsedTime": state.elapsed_seconds,
            }
        )
    except Exception as e:
        logger.warning("Failed to persist agent execution: %s", e)


# ── Legacy Plan Generation (for backward compatibility) ───────


async def _generate_plan(message: str, material_ids: List[str]) -> Optional[AgentPlan]:
    """Call LLM with structured output to generate a tool execution plan.
    
    This is kept for backward compatibility with existing code.
    """
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


# ── Legacy Tool Execution (for backward compatibility) ────────


async def _execute_tool(step: PlanStep, ctx: AgentContext, state: LegacyAgentState) -> ToolOutput:
    """Execute a single tool step (legacy interface)."""
    tool_fn = TOOL_REGISTRY.get(step.tool)
    if not tool_fn:
        return ToolOutput(summary=f"Unknown tool: {step.tool}", error="Tool not found")

    inputs = dict(step.inputs)

    # Inject context from previous RAG steps
    for prev in state.step_results:
        if prev.tool == "rag_tool" and not prev.error:
            if step.tool in ("python_tool", "research_tool"):
                inputs.setdefault("context", prev.summary)
                break

    try:
        return await tool_fn(inputs, ctx)
    except Exception as e:
        logger.error("[agent] Tool %s failed: %s", step.tool, e)
        return ToolOutput(summary=f"Tool {step.tool} failed: {e}", error=str(e))


# ── Legacy Reflection (for backward compatibility) ────────────


async def _reflect(message: str, state: LegacyAgentState) -> ReflectionResult:
    """Decide whether to continue or respond (legacy interface)."""
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

    if state.plan and state.iteration >= len(state.plan.steps):
        return ReflectionResult(
            decision=ReflectionDecision.RESPOND,
            reason="All planned steps completed",
        )

    if state.step_results and state.step_results[-1].error:
        return ReflectionResult(
            decision=ReflectionDecision.CONTINUE,
            reason="Previous step had error, continuing with plan",
        )

    return ReflectionResult(
        decision=ReflectionDecision.CONTINUE,
        reason="More planned steps remain",
    )


# ── Legacy Synthesis (for backward compatibility) ─────────────


async def _synthesize(
    message: str,
    state: LegacyAgentState,
    ctx: AgentContext,
) -> AsyncIterator[str]:
    """Call LLM to produce final answer (legacy interface)."""
    from app.services.llm_service.llm import get_llm

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
