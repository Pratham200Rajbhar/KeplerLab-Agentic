"""Fully agentic open-loop system — LangGraph state machine.

Triggered ONLY when ``intent_override = "AGENT"`` (frontend /agent command).

Philosophy: no fixed pipeline, no predetermined steps.  The agent receives a
user query + material_ids + notebook_id and autonomously decides what tools
to call, in what order, how many times.  The loop continues until the goal is
met or 10 iterations are reached.

Nodes
-----
planner_node       – LLM picks the next single tool + args
tool_executor_node – executes chosen tool, appends result
reflection_node    – LLM evaluates: done → respond | not done → replan
response_node      – synthesises everything into streamed markdown
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, AsyncIterator, Dict, List, Optional, TypedDict

from app.core.config import settings
from app.services.llm_service.llm import get_llm

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────

MAX_ITERATIONS = 10
_TOOL_DESCRIPTIONS: str = ""  # set lazily

# ── State ─────────────────────────────────────────────────────


class ToolCall(TypedDict, total=False):
    tool: str
    args: Dict[str, Any]
    reasoning: str
    result_summary: str
    duration_ms: float
    success: bool
    error: Optional[str]


class Artifact(TypedDict, total=False):
    type: str           # chart | table | file
    index: int
    data: Any           # base64 for chart, rows/cols for table, path for file
    filename: str
    url: Optional[str]
    mime: Optional[str]


class AgentLoopState(TypedDict, total=False):
    query: str
    material_ids: List[str]
    notebook_id: str
    user_id: str
    session_id: str
    plan: str
    tool_history: List[ToolCall]
    artifacts: List[Artifact]
    iteration: int
    final_response: str


# ── Tool Dispatch ─────────────────────────────────────────────

def _get_tool_descriptions() -> str:
    """Build human-readable tool list for the planner prompt."""
    global _TOOL_DESCRIPTIONS
    if _TOOL_DESCRIPTIONS:
        return _TOOL_DESCRIPTIONS
    _TOOL_DESCRIPTIONS = (
        "rag_search(query, material_ids, k=10) – semantic search over user's materials\n"
        "python_executor(code, context={}) – sandboxed Python execution (pandas, matplotlib, etc.)\n"
        "file_generator(type, content, filename) – create PDF/DOCX/PPTX/CSV/JSON/TXT/MD files\n"
        "web_search(query, n_results=5) – quick web search (title+snippet+URL)\n"
        "code_repair(code, error) – rewrite broken Python code\n"
        "flashcard_generator(material_ids, count, language) – generate flashcards\n"
        "quiz_generator(material_ids, count, difficulty, language) – generate quiz\n"
        "mindmap_generator(material_ids) – generate mindmap\n"
        "ppt_generator(material_ids, options) – generate presentation"
    )
    return _TOOL_DESCRIPTIONS


async def _dispatch_tool(
    tool_name: str,
    tool_args: Dict[str, Any],
    state: AgentLoopState,
) -> Dict[str, Any]:
    """Execute a tool and return a result dict.

    Bridges to existing tools_registry handlers where possible.
    """
    from app.services.agent.tools_registry import (
        rag_tool,
        python_tool,
        research_tool,
        quiz_tool,
        flashcard_tool,
        ensure_tools_initialized,
    )
    from app.services.agent.tools.file_generator import generate_file
    from app.services.agent.tools.code_repair import repair_code

    ensure_tools_initialized()

    user_id = state.get("user_id", "")
    notebook_id = state.get("notebook_id", "")
    material_ids = state.get("material_ids", [])
    session_id = state.get("session_id", "")

    try:
        if tool_name == "rag_search":
            r = await rag_tool(
                user_id=user_id,
                query=tool_args.get("query", state.get("query", "")),
                material_ids=tool_args.get("material_ids", material_ids),
                notebook_id=notebook_id,
                session_id=session_id,
            )
            return {
                "success": r.get("success", False),
                "output": r.get("output", ""),
                "metadata": r.get("metadata", {}),
            }

        elif tool_name == "python_executor":
            r = await python_tool(
                query=state.get("query", ""),
                session_id=session_id,
                user_id=user_id,
                notebook_id=notebook_id,
                material_ids=material_ids,
                intent="DATA_ANALYSIS",
                previous_context=tool_args.get("context", ""),
            )
            result = {
                "success": r.get("success", False),
                "output": r.get("output", ""),
                "metadata": r.get("metadata", {}),
            }
            # Collect artifacts
            meta = r.get("metadata", {})
            if meta.get("chart_base64"):
                result["chart"] = meta["chart_base64"]
            return result

        elif tool_name == "web_search":
            r = await research_tool(
                query=tool_args.get("query", state.get("query", "")),
                user_id=user_id,
                notebook_id=notebook_id,
            )
            return {
                "success": r.get("success", False),
                "output": r.get("output", ""),
                "metadata": r.get("metadata", {}),
            }

        elif tool_name == "code_repair":
            llm = get_llm(temperature=0.0, max_tokens=4000)
            fixed = await repair_code(
                tool_args.get("code", ""),
                tool_args.get("error", ""),
                llm,
            )
            return {"success": True, "output": fixed, "metadata": {"fixed_code": fixed}}

        elif tool_name == "flashcard_generator":
            r = await flashcard_tool(
                user_id=user_id,
                material_ids=tool_args.get("material_ids", material_ids),
                notebook_id=notebook_id,
            )
            return {
                "success": r.get("success", False),
                "output": r.get("output", ""),
                "metadata": r.get("metadata", {}),
            }

        elif tool_name == "quiz_generator":
            r = await quiz_tool(
                user_id=user_id,
                material_ids=tool_args.get("material_ids", material_ids),
                notebook_id=notebook_id,
            )
            return {
                "success": r.get("success", False),
                "output": r.get("output", ""),
                "metadata": r.get("metadata", {}),
            }

        elif tool_name == "file_generator":
            # Simplified file generation — create a temp file with content
            ftype = tool_args.get("type", "txt")
            content = tool_args.get("content", "")
            filename = tool_args.get("filename", f"output.{ftype}")
            import tempfile, os
            out_dir = os.path.join(settings.GENERATED_OUTPUT_DIR, state.get("user_id", "anon"))
            os.makedirs(out_dir, exist_ok=True)
            fpath = os.path.join(out_dir, filename)
            with open(fpath, "w") as f:
                f.write(content if isinstance(content, str) else json.dumps(content, indent=2))
            return {
                "success": True,
                "output": f"File saved: {filename}",
                "metadata": {"path": fpath, "filename": filename, "type": ftype},
            }

        else:
            return {"success": False, "output": f"Unknown tool: {tool_name}", "metadata": {}}

    except Exception as exc:
        logger.exception("[dispatch_tool] %s failed: %s", tool_name, exc)
        return {"success": False, "output": str(exc), "metadata": {}, "error": str(exc)}


# ── Planner Node ──────────────────────────────────────────────

async def _planner_node(state: AgentLoopState) -> AgentLoopState:
    """LLM picks the next single tool call + args.

    RULE: planner only picks the NEXT tool — no multi-step pre-planning.
    """
    llm = get_llm(temperature=0.2)
    history_text = ""
    for i, tc in enumerate(state.get("tool_history", [])):
        summary = tc.get("result_summary", "")[:300]
        history_text += f"  Step {i + 1}: {tc.get('tool')}({json.dumps(tc.get('args', {}))[:200]}) → {summary}\n"

    artifacts_text = ""
    for a in state.get("artifacts", []):
        artifacts_text += f"  [{a.get('type')}] {a.get('filename', '?')}\n"

    prompt = (
        "You are an autonomous AI agent. Decide the NEXT single tool call.\n\n"
        f"User query: {state.get('query', '')}\n\n"
        f"Available tools:\n{_get_tool_descriptions()}\n\n"
        f"Tool history (what you've already done):\n{history_text or '  (none yet)'}\n\n"
        f"Artifacts produced so far:\n{artifacts_text or '  (none)'}\n\n"
        "Return ONLY a JSON object:\n"
        '{"tool": "<tool_name>", "args": {<tool_args>}, "reasoning": "<one line>"}\n\n'
        "If the task is already complete based on tool history, return:\n"
        '{"tool": "DONE", "args": {}, "reasoning": "Task complete"}'
    )

    resp = await llm.ainvoke(prompt)
    raw = getattr(resp, "content", str(resp)).strip()

    import re
    try:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(m.group()) if m else {"tool": "DONE", "args": {}, "reasoning": "Parse failed"}
    except Exception:
        data = {"tool": "DONE", "args": {}, "reasoning": "Parse failed"}

    state = {**state, "plan": data.get("reasoning", "")}

    if data.get("tool") == "DONE":
        state["final_response"] = "__PLAN_DONE__"

    state["_next_tool"] = data.get("tool", "DONE")
    state["_next_args"] = data.get("args", {})
    return state


# ── Tool Executor Node ────────────────────────────────────────

async def _tool_executor_node(state: AgentLoopState) -> AgentLoopState:
    """Execute the tool chosen by planner and append result to history."""
    tool_name = state.pop("_next_tool", "DONE")
    tool_args = state.pop("_next_args", {})

    if tool_name == "DONE":
        return state

    t0 = time.perf_counter()
    result = await _dispatch_tool(tool_name, tool_args, state)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    tc: ToolCall = {
        "tool": tool_name,
        "args": tool_args,
        "reasoning": state.get("plan", ""),
        "result_summary": (result.get("output", "") or "")[:500],
        "duration_ms": round(elapsed_ms, 1),
        "success": result.get("success", False),
        "error": result.get("error"),
    }

    tool_history = list(state.get("tool_history", []))
    tool_history.append(tc)

    artifacts = list(state.get("artifacts", []))
    # Auto-collect artifacts
    if result.get("chart"):
        artifacts.append(Artifact(
            type="chart",
            index=len(artifacts),
            data=result["chart"],
            filename=f"chart_{len(artifacts)}.png",
        ))
    meta = result.get("metadata", {})
    if meta.get("path") and meta.get("filename"):
        artifacts.append(Artifact(
            type="file",
            index=len(artifacts),
            filename=meta["filename"],
            url=f"/files/agent/{meta['filename']}",
        ))

    # Auto code repair on python_executor failure
    if tool_name == "python_executor" and not result.get("success"):
        stderr = meta.get("stderr", "")
        code = meta.get("generated_code", "")
        if stderr and code:
            logger.info("[tool_executor] Python failed — attempting auto-repair")
            repair_result = await _dispatch_tool("code_repair", {"code": code, "error": stderr}, state)
            if repair_result.get("success"):
                fixed_code = repair_result.get("metadata", {}).get("fixed_code", "")
                if fixed_code:
                    retry_result = await _dispatch_tool("python_executor", {"code": fixed_code}, state)
                    retry_tc: ToolCall = {
                        "tool": "python_executor (repair retry)",
                        "args": {"code": fixed_code[:200]},
                        "reasoning": "Auto-repair retry",
                        "result_summary": (retry_result.get("output", "") or "")[:500],
                        "duration_ms": 0,
                        "success": retry_result.get("success", False),
                    }
                    tool_history.append(retry_tc)
                    if retry_result.get("chart"):
                        artifacts.append(Artifact(
                            type="chart", index=len(artifacts),
                            data=retry_result["chart"],
                            filename=f"chart_{len(artifacts)}.png",
                        ))

    return {
        **state,
        "tool_history": tool_history,
        "artifacts": artifacts,
        "iteration": state.get("iteration", 0) + 1,
    }


# ── Reflection Node ──────────────────────────────────────────

async def _reflection_node(state: AgentLoopState) -> AgentLoopState:
    """LLM evaluates whether the query has been fully answered."""
    iteration = state.get("iteration", 0)
    if iteration >= MAX_ITERATIONS:
        return {**state, "final_response": "__FORCE_RESPOND__"}

    if state.get("final_response") == "__PLAN_DONE__":
        return state

    llm = get_llm(temperature=0.1)
    history_summary = "\n".join(
        f"  {tc.get('tool')}: {'OK' if tc.get('success') else 'FAILED'} — {tc.get('result_summary', '')[:200]}"
        for tc in state.get("tool_history", [])
    )
    prompt = (
        "You are evaluating whether an AI agent has fully answered the user's query.\n\n"
        f"User query: {state.get('query', '')}\n\n"
        f"Tool execution history:\n{history_summary}\n\n"
        f"Iteration: {iteration}/{MAX_ITERATIONS}\n\n"
        "Has the user's question been fully answered? Reply ONLY with JSON:\n"
        '{"done": true/false, "reasoning": "..."}'
    )
    resp = await llm.ainvoke(prompt)
    raw = getattr(resp, "content", str(resp)).strip()
    import re
    try:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(m.group()) if m else {"done": False}
    except Exception:
        data = {"done": False}

    if data.get("done"):
        state = {**state, "final_response": "__REFLECT_DONE__"}

    return state


def _should_continue(state: AgentLoopState) -> str:
    """Conditional edge for LangGraph."""
    if state.get("final_response") in ("__PLAN_DONE__", "__REFLECT_DONE__", "__FORCE_RESPOND__"):
        return "respond"
    if state.get("iteration", 0) >= MAX_ITERATIONS:
        return "respond"
    return "replan"


# ── Response Node ─────────────────────────────────────────────

async def _response_node(state: AgentLoopState) -> AgentLoopState:
    """Synthesise all tool outputs + artifacts into final markdown."""
    llm = get_llm(temperature=0.3)

    history_text = ""
    for i, tc in enumerate(state.get("tool_history", [])):
        history_text += (
            f"### Step {i + 1}: {tc.get('tool')}\n"
            f"Result: {tc.get('result_summary', '')}\n\n"
        )

    artifact_refs = ""
    for a in state.get("artifacts", []):
        if a.get("type") == "chart":
            artifact_refs += f"![Chart](artifact:{a.get('index', 0)})\n"
        elif a.get("type") == "file":
            artifact_refs += f"- [{a.get('filename', 'file')}]({a.get('url', '')})\n"
        elif a.get("type") == "table":
            artifact_refs += f"- Table: {a.get('filename', 'data')}\n"

    prompt = (
        "Synthesise the following tool results into a clear, well-structured markdown response.\n\n"
        f"User query: {state.get('query', '')}\n\n"
        f"Tool results:\n{history_text}\n\n"
        f"Available artifact references:\n{artifact_refs or '(none)'}\n\n"
        "Instructions:\n"
        "- Embed chart references inline using ![Chart](artifact:N) syntax\n"
        "- List downloadable files at the bottom\n"
        "- Be specific and reference actual results\n"
        "- Use markdown formatting"
    )
    resp = await llm.ainvoke(prompt)
    final = getattr(resp, "content", str(resp)).strip()

    return {**state, "final_response": final}


# ── Graph Builder ─────────────────────────────────────────────

_compiled_graph = None


def _build_graph():
    """Build the LangGraph state machine for the agentic loop."""
    global _compiled_graph
    if _compiled_graph is not None:
        return _compiled_graph

    from langgraph.graph import StateGraph, END

    g = StateGraph(AgentLoopState)
    g.add_node("planner", _planner_node)
    g.add_node("executor", _tool_executor_node)
    g.add_node("reflection", _reflection_node)
    g.add_node("response", _response_node)

    g.set_entry_point("planner")
    g.add_edge("planner", "executor")
    g.add_edge("executor", "reflection")
    g.add_conditional_edges("reflection", _should_continue, {
        "replan": "planner",
        "respond": "response",
    })
    g.add_edge("response", END)

    _compiled_graph = g.compile()
    logger.info("Agentic loop graph compiled")
    return _compiled_graph


# ── Public Entry Points ───────────────────────────────────────


async def run_agentic_loop(
    query: str,
    material_ids: List[str],
    notebook_id: str,
    user_id: str,
    session_id: str,
) -> Dict[str, Any]:
    """Run the full agentic loop synchronously (non-streaming)."""
    graph = _build_graph()
    initial: AgentLoopState = {
        "query": query,
        "material_ids": material_ids,
        "notebook_id": notebook_id,
        "user_id": user_id,
        "session_id": session_id,
        "plan": "",
        "tool_history": [],
        "artifacts": [],
        "iteration": 0,
        "final_response": "",
    }
    result = await graph.ainvoke(initial)
    return {
        "response": result.get("final_response", ""),
        "artifacts": result.get("artifacts", []),
        "tool_history": result.get("tool_history", []),
    }


async def stream_agentic_loop(
    query: str,
    material_ids: List[str],
    notebook_id: str,
    user_id: str,
    session_id: str,
) -> AsyncIterator[str]:
    """Stream the agentic loop as SSE events.

    Yields events conforming to Section 5 specification:
    agent_start, agent_step (running/done), artifact, agent_reflection, token, done
    """
    graph = _build_graph()
    initial: AgentLoopState = {
        "query": query,
        "material_ids": material_ids,
        "notebook_id": notebook_id,
        "user_id": user_id,
        "session_id": session_id,
        "plan": "",
        "tool_history": [],
        "artifacts": [],
        "iteration": 0,
        "final_response": "",
    }

    start_time = time.time()
    step_id = 0
    prev_history_len = 0
    prev_artifact_len = 0

    def _sse(event_type: str, data: Any) -> str:
        return f"data: {json.dumps({'type': event_type, **data})}\n\n"

    try:
        async for event in graph.astream_events(initial, version="v2"):
            kind = event.get("event", "")

            # Planner completed → emit agent_start / plan update
            if kind == "on_chain_end" and event.get("name") == "planner":
                output = event.get("data", {}).get("output", {})
                plan_text = output.get("plan", "")
                if step_id == 0:
                    yield _sse("agent_start", {"plan": plan_text})
                step_id += 1

            # Executor completed → emit agent_step + artifacts
            elif kind == "on_chain_end" and event.get("name") == "executor":
                output = event.get("data", {}).get("output", {})
                history = output.get("tool_history", [])
                artifacts = output.get("artifacts", [])

                # Emit new tool steps
                for tc in history[prev_history_len:]:
                    yield _sse("agent_step", {
                        "step": {
                            "id": len(history),
                            "tool": tc.get("tool", "unknown"),
                            "status": "done" if tc.get("success") else "failed",
                            "result_summary": tc.get("result_summary", ""),
                            "duration_ms": tc.get("duration_ms", 0),
                        },
                    })
                prev_history_len = len(history)

                # Emit new artifacts
                for art in artifacts[prev_artifact_len:]:
                    yield _sse("artifact", {"artifact": art})
                prev_artifact_len = len(artifacts)

            # Reflection completed → emit reasoning
            elif kind == "on_chain_end" and event.get("name") == "reflection":
                output = event.get("data", {}).get("output", {})
                fr = output.get("final_response", "")
                if fr in ("__PLAN_DONE__", "__REFLECT_DONE__", "__FORCE_RESPOND__"):
                    yield _sse("agent_reflection", {
                        "reflection": "Goal achieved. Composing final response.",
                    })
                else:
                    yield _sse("agent_reflection", {
                        "reflection": "More work needed. Re-planning next step.",
                    })

            # Response node completed → stream tokens
            elif kind == "on_chain_end" and event.get("name") == "response":
                output = event.get("data", {}).get("output", {})
                final = output.get("final_response", "")
                # Stream in chunks
                CHUNK = 80
                for i in range(0, len(final), CHUNK):
                    yield _sse("token", {"content": final[i:i + CHUNK]})

        elapsed = round(time.time() - start_time, 2)
        yield _sse("done", {"elapsed": elapsed, "artifacts": []})

    except Exception as exc:
        logger.exception("[stream_agentic_loop] Error: %s", exc)
        yield _sse("error", {"error": str(exc)})
        elapsed = round(time.time() - start_time, 2)
        yield _sse("done", {"elapsed": elapsed, "artifacts": []})
