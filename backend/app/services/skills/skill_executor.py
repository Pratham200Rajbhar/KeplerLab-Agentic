"""
Skill Executor — runs a compiled skill plan step-by-step.

Yields SSE events for real-time streaming and collects results + artifacts.
Integrates with the existing agent tool registry.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from app.services.chat_v2.schemas import ToolResult

logger = logging.getLogger(__name__)

# ── Execution Limits ───────────────────────────────────────
MAX_STEPS = 15
MAX_TIMEOUT_SECONDS = 600
MAX_RETRIES_PER_STEP = 2

# ── SSE Event Helpers ──────────────────────────────────────

def _sse(event: str, data: Any) -> str:
    """Format an SSE event string."""
    payload = json.dumps(data) if not isinstance(data, str) else data
    return f"event: {event}\ndata: {payload}\n\n"


_TRUE_VALUES = {"1", "true", "yes", "y", "on", "found", "available", "present"}
_FALSE_VALUES = {"0", "false", "no", "n", "off", "none", "null", "missing", "absent", "not_found"}


def _coerce_bool(value: Any) -> Optional[bool]:
    """Convert common bool-like values to bool, else None."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        token = value.strip().lower()
        if token in _TRUE_VALUES:
            return True
        if token in _FALSE_VALUES:
            return False
    return None


def _context_indicates_dataset_available(context: str, variables: Dict[str, str]) -> Optional[bool]:
    """Infer dataset availability from explicit variables or prior step context."""
    availability_keys = (
        "dataset_found",
        "has_dataset",
        "dataset_available",
        "data_available",
    )
    for key in availability_keys:
        if key in variables:
            coerced = _coerce_bool(variables.get(key))
            if coerced is not None:
                return coerced

    text = (context or "").lower()
    if not text:
        return None

    positive_markers = (
        "dataset found",
        "found dataset",
        "dataset available",
        "data available",
        "csv",
        "dataframe",
        "rows",
        "columns",
    )
    negative_markers = (
        "no dataset",
        "dataset not found",
        "dataset unavailable",
        "no data available",
        "no relevant data",
    )

    pos_idx = max((text.rfind(marker) for marker in positive_markers if marker in text), default=-1)
    neg_idx = max((text.rfind(marker) for marker in negative_markers if marker in text), default=-1)

    if pos_idx == -1 and neg_idx == -1:
        return None
    return pos_idx >= neg_idx


def _evaluate_condition_atom(condition: str, variables: Dict[str, str], context: str) -> bool:
    """Evaluate a single condition expression without AND/OR composition."""
    atom = condition.strip().lower()
    if not atom:
        return True

    # Handle negation prefixes.
    for prefix in ("no ", "not ", "without "):
        if atom.startswith(prefix):
            return not _evaluate_condition_atom(atom[len(prefix):], variables, context)

    # Common dataset branching phrases.
    if "dataset" in atom or "data" in atom:
        inferred = _context_indicates_dataset_available(context, variables)
        if "no dataset" in atom or "dataset not found" in atom or "no data" in atom:
            return inferred is False or inferred is None
        if "dataset found" in atom or "dataset available" in atom or "has dataset" in atom:
            return inferred is True
        if inferred is not None:
            return inferred

    # Variable-style conditions (e.g. "dataset_found", "has_data").
    if atom in variables:
        coerced = _coerce_bool(variables.get(atom))
        if coerced is not None:
            return coerced
        return bool(str(variables.get(atom, "")).strip())

    # Generic "x == y" / "x != y" checks.
    eq_match = re.match(r"^([a-zA-Z_][\w]*)\s*(==|!=)\s*['\"]?(.+?)['\"]?$", atom)
    if eq_match:
        key, op, expected = eq_match.groups()
        actual = str(variables.get(key, "")).strip().lower()
        expected_norm = expected.strip().lower()
        return (actual == expected_norm) if op == "==" else (actual != expected_norm)

    # Last resort: treat condition text as something that should appear in context.
    return atom in (context or "").lower()


def _evaluate_condition(condition: Optional[str], variables: Dict[str, str], context: str) -> bool:
    """Evaluate condition strings with simple AND/OR composition."""
    if not condition:
        return True

    expr = condition.strip()
    if not expr:
        return True

    # Evaluate OR groups first, then AND atoms.
    or_groups = [group.strip() for group in re.split(r"\s+or\s+", expr, flags=re.IGNORECASE)]
    for group in or_groups:
        and_atoms = [atom.strip() for atom in re.split(r"\s+and\s+", group, flags=re.IGNORECASE)]
        if all(_evaluate_condition_atom(atom, variables, context) for atom in and_atoms if atom):
            return True
    return False


# ── Step Executors ─────────────────────────────────────────

async def _execute_rag_step(
    query: str,
    material_ids: List[str],
    user_id: str,
    notebook_id: str,
    step_index: int,
) -> tuple[str, List[dict]]:
    """Execute a RAG retrieval step."""
    from app.services.tools.rag_tool import execute
    content_parts = []
    artifacts = []
    async for item in execute(query, material_ids, user_id, notebook_id, step_index=step_index):
        if isinstance(item, ToolResult):
            content_parts.append(item.content)
            artifacts.extend(item.artifacts)
        elif isinstance(item, str):
            pass  # SSE events from tool — skip
    return "\n".join(content_parts) or "No results found.", artifacts


async def _execute_web_search_step(
    query: str,
    user_id: str,
    step_index: int,
) -> tuple[str, List[dict]]:
    """Execute a web search step."""
    from app.services.tools.web_search_tool import execute
    content_parts = []
    artifacts = []
    async for item in execute(query, user_id, step_index=step_index):
        if isinstance(item, ToolResult):
            content_parts.append(item.content)
            artifacts.extend(item.artifacts)
    return "\n".join(content_parts) or "No results found.", artifacts


async def _execute_research_step(
    query: str,
    user_id: str,
    notebook_id: str,
    session_id: str,
    material_ids: List[str],
    step_index: int,
) -> tuple[str, List[dict]]:
    """Execute a deep research step."""
    from app.services.tools.research_tool import execute
    content_parts = []
    artifacts = []
    async for item in execute(query, user_id, notebook_id, session_id, material_ids, step_index=step_index):
        if isinstance(item, ToolResult):
            content_parts.append(item.content)
            artifacts.extend(item.artifacts)
    return "\n".join(content_parts) or "Research complete.", artifacts


async def _execute_python_auto_step(
    query: str,
    material_ids: List[str],
    user_id: str,
    notebook_id: str,
    session_id: str,
    step_index: int,
) -> tuple[str, List[dict]]:
    """Execute a python_auto (code generation + execution) step."""
    from app.services.agent.tools_registry import TOOL_REGISTRY
    tool = TOOL_REGISTRY.get("python_auto")
    if not tool:
        return "python_auto tool not available.", []
    content_parts = []
    artifacts = []
    async for item in tool.execute_fn(
        query=query,
        material_ids=material_ids,
        user_id=user_id,
        notebook_id=notebook_id,
        session_id=session_id,
        step_index=step_index,
    ):
        if isinstance(item, ToolResult):
            content_parts.append(item.content)
            artifacts.extend(item.artifacts)
    return "\n".join(content_parts) or "Code executed.", artifacts


async def _execute_llm_step(
    query: str,
    context: str = "",
    rules: List[str] = None,
    material_ids: List[str] = None,
) -> tuple[str, List[dict]]:
    """Execute a pure LLM reasoning/synthesis step."""
    from app.services.llm_service.llm import get_llm, extract_chunk_content
    from app.services.notebooks.materials import get_material_metadata

    system = "You are a helpful assistant completing a step in a skill workflow."
    if rules:
        system += "\n\nRules to follow:\n" + "\n".join(f"- {r}" for r in rules)

    # Add context about available materials if applicable
    material_context = ""
    if material_ids:
        try:
            metas = [get_material_metadata(mid) for mid in material_ids]
            filenames = [m.get("filename") for m in metas if m.get("filename")]
            if filenames:
                material_context = f"\nNOTE: The user has uploaded the following materials to this notebook: {', '.join(filenames)}. "
                material_context += "If you need specific data from them, you can ask for it or assume it was processed in previous steps."
        except Exception:
            pass

    prompt = query
    if context:
        prompt = f"Context from previous steps:\n{context}\n\nTask:\n{query}"

    full_prompt = f"{system}{material_context}\n\n{prompt}"
    llm = get_llm(temperature=0.3, max_tokens=3000)
    result = await llm.ainvoke(full_prompt)
    response = extract_chunk_content(result)

    return response or "No output generated.", []


# ── Main Executor ──────────────────────────────────────────

async def execute_skill(
    plan: List[Dict[str, Any]],
    user_id: str,
    notebook_id: str,
    session_id: str,
    material_ids: List[str],
    variables: Dict[str, str],
    rules: List[str] = None,
) -> AsyncIterator[str]:
    """
    Execute a compiled skill plan step-by-step, yielding SSE events.

    Events:
    - skill_status: overall status updates
    - skill_step_start: step beginning
    - skill_step_skipped: step skipped due to condition
    - skill_step_result: step completed with result
    - skill_step_error: step failed
    - skill_artifact: artifact produced
    - skill_done: execution complete
    """
    start_time = time.time()
    step_logs: List[Dict[str, Any]] = []
    all_artifacts: List[dict] = []
    accumulated_context = ""
    total_steps = min(len(plan), MAX_STEPS)
    timed_out = False

    yield _sse("skill_status", {
        "status": "running",
        "total_steps": total_steps,
        "message": f"Starting skill execution ({total_steps} steps)",
    })

    for i, step in enumerate(plan[:MAX_STEPS]):
        step_index = step.get("index", i + 1)
        instruction = step.get("instruction", "")
        tool = step.get("tool", "llm")
        query = step.get("query", instruction)
        condition = step.get("condition")
        elapsed = time.time() - start_time

        # Timeout check
        if elapsed > MAX_TIMEOUT_SECONDS:
            timed_out = True
            timeout_error = "Execution timeout exceeded"
            step_logs.append({
                "step_index": step_index,
                "instruction": instruction,
                "tool": tool,
                "success": False,
                "skipped": False,
                "condition": condition,
                "content": "",
                "artifacts_count": 0,
                "elapsed_seconds": 0.0,
                "retries": 0,
                "error": timeout_error,
            })
            yield _sse("skill_step_error", {
                "step_index": step_index,
                "tool": tool,
                "error": timeout_error,
                "success": False,
            })
            yield _sse("skill_status", {"status": "failed", "error": "Timeout"})
            break

        if condition and not _evaluate_condition(condition, variables, accumulated_context):
            skip_reason = f"Condition '{condition}' evaluated to false"
            step_log = {
                "step_index": step_index,
                "instruction": instruction,
                "tool": tool,
                "success": True,
                "skipped": True,
                "condition": condition,
                "skip_reason": skip_reason,
                "content": "",
                "artifacts_count": 0,
                "elapsed_seconds": 0.0,
                "retries": 0,
                "error": None,
            }
            step_logs.append(step_log)
            yield _sse("skill_step_skipped", {
                "step_index": step_index,
                "instruction": instruction,
                "tool": tool,
                "condition": condition,
                "reason": skip_reason,
                "success": True,
                "progress": round(((i + 1) / total_steps) * 100),
            })
            continue

        yield _sse("skill_step_start", {
            "step_index": step_index,
            "total_steps": total_steps,
            "instruction": instruction,
            "tool": tool,
            "progress": round((i / total_steps) * 100),
        })

        step_start = time.time()
        content = ""
        artifacts: List[dict] = []
        success = True
        error_msg = None
        retries = 0

        while retries <= MAX_RETRIES_PER_STEP:
            try:
                if tool == "rag":
                    content, artifacts = await _execute_rag_step(
                        query, material_ids, user_id, notebook_id, step_index,
                    )
                elif tool == "web_search":
                    content, artifacts = await _execute_web_search_step(
                        query, user_id, step_index,
                    )
                elif tool == "research":
                    content, artifacts = await _execute_research_step(
                        query, user_id, notebook_id, session_id,
                        material_ids, step_index,
                    )
                elif tool == "python_auto":
                    content, artifacts = await _execute_python_auto_step(
                        query, material_ids, user_id, notebook_id,
                        session_id, step_index,
                    )
                elif tool == "llm":
                    content, artifacts = await _execute_llm_step(
                        query, accumulated_context, rules, material_ids,
                    )
                else:
                    # Unknown tool, fall back to LLM
                    logger.warning("Unknown tool '%s' for step %d, falling back to llm", tool, step_index)
                    content, artifacts = await _execute_llm_step(
                        query, accumulated_context, rules, material_ids,
                    )
                break  # success
            except Exception as e:
                retries += 1
                error_msg = str(e)
                logger.warning(
                    "Step %d (tool=%s) failed (attempt %d/%d): %s",
                    step_index, tool, retries, MAX_RETRIES_PER_STEP + 1, e,
                )
                if retries > MAX_RETRIES_PER_STEP:
                    success = False
                    content = f"Step failed after {retries} attempts: {error_msg}"
                else:
                    await asyncio.sleep(1)  # Brief backoff before retry

        step_elapsed = time.time() - step_start

        # Accumulate context for subsequent LLM steps
        if content:
            accumulated_context += f"\n\n--- Step {step_index} ({tool}) ---\n{content[:2000]}"

        # Emit artifacts
        for artifact in artifacts:
            all_artifacts.append(artifact)
            yield _sse("skill_artifact", artifact)

        # Log step
        step_log = {
            "step_index": step_index,
            "instruction": instruction,
            "tool": tool,
            "success": success,
            "skipped": False,
            "condition": condition,
            "content": content[:2000] if content else "",
            "artifacts_count": len(artifacts),
            "elapsed_seconds": round(step_elapsed, 2),
            "retries": retries,
            "error": error_msg if not success else None,
        }
        step_logs.append(step_log)

        if success:
            yield _sse("skill_step_result", {
                "step_index": step_index,
                "tool": tool,
                "content": content[:3000] if content else "",
                "artifacts_count": len(artifacts),
                "elapsed": round(step_elapsed, 2),
                "success": True,
                "progress": round(((i + 1) / total_steps) * 100),
            })
        else:
            yield _sse("skill_step_error", {
                "step_index": step_index,
                "tool": tool,
                "error": error_msg or "Unknown error",
                "success": False,
                "progress": round(((i + 1) / total_steps) * 100),
            })

    total_elapsed = time.time() - start_time
    has_failures = timed_out or any(not log.get("success", True) for log in step_logs)

    yield _sse("skill_done", {
        "status": "completed" if not has_failures else "completed_with_errors",
        "total_steps": len(step_logs),
        "successful_steps": sum(1 for log in step_logs if log["success"]),
        "failed_steps": sum(1 for log in step_logs if not log["success"]),
        "artifacts_count": len(all_artifacts),
        "elapsed_seconds": round(total_elapsed, 2),
        "final_output": accumulated_context[-3000:] if accumulated_context else "",
        # Include step logs and artifacts in the final event for persistence
        "step_logs": step_logs,
        "artifacts": all_artifacts,
    })
