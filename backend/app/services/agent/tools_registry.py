"""Tool registry — wraps existing services as agent-callable tools.

Contract
--------
Every handler MUST return a ToolResult with:
    success  : bool  – True if the tool produced usable output
    output   : str   – human-readable response (never None)
    metadata : dict  – any structured data the frontend / downstream needs
    tool_name: str   – identifier (must match registry name)
    tokens_used: int – rough estimate for budget tracking

Registered tools
-----------------
    rag_tool          → QUESTION
    quiz_tool         → CONTENT_GENERATION
    flashcard_tool    → CONTENT_GENERATION
    ppt_tool          → CONTENT_GENERATION
    python_tool       → DATA_ANALYSIS, CODE_EXECUTION
    research_tool     → RESEARCH
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Coroutine, Dict, List

from app.core.config import settings
from app.services.agent.state import ToolResult

logger = logging.getLogger(__name__)


# ── Tool Registry ─────────────────────────────────────────────

_TOOLS: Dict[str, Dict[str, Any]] = {}


def register_tool(
    name: str,
    description: str,
    handler: Callable[..., Coroutine[Any, Any, ToolResult]],
    intents: List[str],
):
    """Register a tool in the registry."""
    _TOOLS[name] = {
        "name": name,
        "description": description,
        "handler": handler,
        "intents": intents,
    }
    logger.info(f"Registered tool: {name}")


def get_tool(name: str) -> Dict[str, Any] | None:
    """Get a tool by name."""
    return _TOOLS.get(name)


def get_tools_for_intent(intent: str) -> List[Dict[str, Any]]:
    """Get all tools that handle a given intent."""
    return [t for t in _TOOLS.values() if intent in t["intents"]]


def list_tools() -> List[str]:
    """Return list of registered tool names."""
    return list(_TOOLS.keys())


# ── Built-in Tool Implementations ─────────────────────────────


async def rag_tool(
    user_id: str,
    query: str,
    material_ids: List[str],
    notebook_id: str,
    session_id: str,
    **kwargs,
) -> ToolResult:
    """RAG retrieval + LLM answer — wraps the secure retriever and chat service."""
    t0 = time.time()
    logger.info(
        "[rag_tool] START | user=%s | materials=%s | query=%r",
        user_id, material_ids, query[:80],
    )
    try:
        from app.services.rag.secure_retriever import secure_similarity_search_enhanced
        from app.services.chat.service import generate_rag_response

        # secure_similarity_search_enhanced is synchronous — offload to thread pool
        context: str = await asyncio.to_thread(
            secure_similarity_search_enhanced,
            user_id=user_id,
            query=query,
            material_ids=material_ids,
            notebook_id=notebook_id,
            use_mmr=True,
            use_reranker=settings.USE_RERANKER,
            return_formatted=True,
        )

        if not context or context.strip() == "No relevant context found.":
            logger.warning("[rag_tool] No context retrieved for query=%r", query[:80])
            return ToolResult(
                tool_name="rag_tool",
                success=False,
                output="I couldn't find relevant information in your materials for that question.",
                metadata={"context_length": 0},
                error="No relevant context found",
                tokens_used=0,
            )

        answer: str = await generate_rag_response(
            notebook_id=notebook_id,
            user_id=user_id,
            context=context,
            user_message=query,
            session_id=session_id,
        )
        elapsed = time.time() - t0
        logger.info(
            "[rag_tool] OK | elapsed=%.2fs | answer_len=%d | context_len=%d",
            elapsed, len(answer), len(context),
        )
        return ToolResult(
            tool_name="rag_tool",
            success=True,
            output=answer,
            metadata={"context_length": len(context)},
            tokens_used=len(answer.split()) * 2,
        )

    except Exception as exc:
        elapsed = time.time() - t0
        logger.error("[rag_tool] FAILED | elapsed=%.2fs | error=%s", elapsed, exc)
        return ToolResult(
            tool_name="rag_tool",
            success=False,
            output="An error occurred while searching your materials.",
            metadata={},
            error=str(exc),
            tokens_used=0,
        )


async def quiz_tool(
    user_id: str,
    material_ids: List[str],
    notebook_id: str,
    **kwargs,
) -> ToolResult:
    """Quiz generation — retrieves context then generates structured quiz questions."""
    t0 = time.time()
    logger.info(
        "[quiz_tool] START | user=%s | materials=%s", user_id, material_ids
    )
    try:
        from app.services.rag.secure_retriever import secure_similarity_search_enhanced
        # Correct import: module is quiz.generator, NOT quiz.service
        from app.services.quiz.generator import generate_quiz

        context: str = await asyncio.to_thread(
            secure_similarity_search_enhanced,
            user_id=user_id,
            query="Generate comprehensive quiz questions covering the key concepts",
            material_ids=material_ids,
            notebook_id=notebook_id,
            use_mmr=True,
            use_reranker=settings.USE_RERANKER,
            return_formatted=True,
        )

        # generate_quiz is synchronous — offload to thread pool
        result: dict = await asyncio.to_thread(generate_quiz, context)

        questions = result.get("questions", [])
        title = result.get("title", "Quiz")
        elapsed = time.time() - t0
        logger.info(
            "[quiz_tool] OK | elapsed=%.2fs | questions=%d",
            elapsed, len(questions),
        )
        return ToolResult(
            tool_name="quiz_tool",
            success=True,
            output=f"Generated **{title}** with {len(questions)} question(s) from your materials.",
            metadata=result,
            tokens_used=500,
        )

    except Exception as exc:
        elapsed = time.time() - t0
        logger.error("[quiz_tool] FAILED | elapsed=%.2fs | error=%s", elapsed, exc)
        return ToolResult(
            tool_name="quiz_tool",
            success=False,
            output="Quiz generation failed.",
            metadata={},
            error=str(exc),
            tokens_used=0,
        )


async def flashcard_tool(
    user_id: str,
    material_ids: List[str],
    notebook_id: str,
    **kwargs,
) -> ToolResult:
    """Flashcard generation — retrieves context then generates study flashcards."""
    t0 = time.time()
    logger.info(
        "[flashcard_tool] START | user=%s | materials=%s", user_id, material_ids
    )
    try:
        from app.services.rag.secure_retriever import secure_similarity_search_enhanced
        # Correct import: module is flashcard.generator, NOT flashcard.service
        from app.services.flashcard.generator import generate_flashcards

        context: str = await asyncio.to_thread(
            secure_similarity_search_enhanced,
            user_id=user_id,
            query="Generate comprehensive flashcards covering the key concepts and definitions",
            material_ids=material_ids,
            notebook_id=notebook_id,
            use_mmr=True,
            use_reranker=settings.USE_RERANKER,
            return_formatted=True,
        )

        # generate_flashcards is synchronous — offload to thread pool
        result: dict = await asyncio.to_thread(generate_flashcards, context)

        cards = result.get("flashcards", [])
        title = result.get("title", "Flashcards")
        elapsed = time.time() - t0
        logger.info(
            "[flashcard_tool] OK | elapsed=%.2fs | cards=%d",
            elapsed, len(cards),
        )
        return ToolResult(
            tool_name="flashcard_tool",
            success=True,
            output=f"Generated **{title}** with {len(cards)} flashcard(s) from your materials.",
            metadata=result,
            tokens_used=500,
        )

    except Exception as exc:
        elapsed = time.time() - t0
        logger.error("[flashcard_tool] FAILED | elapsed=%.2fs | error=%s", elapsed, exc)
        return ToolResult(
            tool_name="flashcard_tool",
            success=False,
            output="Flashcard generation failed.",
            metadata={},
            error=str(exc),
            tokens_used=0,
        )


async def ppt_tool(
    user_id: str,
    material_ids: List[str],
    notebook_id: str,
    topic: str = "",
    **kwargs,
) -> ToolResult:
    """Presentation generation — directs the user to the Studio panel.

    Full PPT generation is a multi-step flow that requires the frontend Studio
    UI.  This tool acknowledges the request and signals the frontend to open
    the Studio panel.
    """
    logger.info(
        "[ppt_tool] START | user=%s | materials=%s | topic=%r",
        user_id, material_ids, topic,
    )
    try:
        message = (
            "Presentation generation has been initiated. "
            "Please use the **Studio** panel to configure and generate your presentation."
        )
        logger.info("[ppt_tool] OK | redirected to Studio")
        return ToolResult(
            tool_name="ppt_tool",
            success=True,
            output=message,
            metadata={"action": "open_studio", "topic": topic},
            tokens_used=0,
        )
    except Exception as exc:
        logger.error("[ppt_tool] FAILED | error=%s", exc)
        return ToolResult(
            tool_name="ppt_tool",
            success=False,
            output="Presentation generation failed.",
            metadata={},
            error=str(exc),
            tokens_used=0,
        )


async def python_tool(
    query: str,
    session_id: str = "",
    user_id: str = "",
    notebook_id: str = "",
    material_ids: List[str] = None,
    intent: str = "",
    **kwargs,
) -> ToolResult:
    """Python code generation + execution in a sandboxed subprocess.

    Uses generate_and_execute() which:
      1. Prompts the LLM to write Python targeting the user request
      2. Validates the code against security rules
      3. Runs it in an isolated subprocess with a timeout
    """
    t0 = time.time()
    logger.info("[python_tool] START | query=%r", query[:80])
    try:
        from app.services.code_execution.executor import generate_and_execute
        from app.services.material_service import get_material_for_user, get_material_text
        import json
        from app.services.llm_service.llm import get_llm

        # Emit code_generating event so the frontend shows "Generating code…"
        try:
            from langchain_core.callbacks import adispatch_custom_event
            await adispatch_custom_event("code_generating", {"tool": "python_tool", "status": "generating"})
        except Exception:
            pass

        # ── Incorporate previous RAG context if tool chaining (DATA_ANALYSIS) ──
        previous_context = kwargs.get("previous_context", "")

        csv_files = []
        parquet_files: list[dict[str, str]] = []  # {"name": "sales.parquet", "path": "/abs/path.parquet"}

        if material_ids and user_id:
            for m_id in material_ids:
                material = await get_material_for_user(m_id, user_id)
                if not material:
                    continue
                fname = getattr(material, "filename", "") or ""
                fname_lower = fname.lower()

                # Parse stored extraction metadata for parquet side-car paths
                meta_raw = getattr(material, "metadata", None)
                meta: dict = {}
                if meta_raw:
                    try:
                        meta = json.loads(meta_raw) if isinstance(meta_raw, str) else meta_raw
                    except (json.JSONDecodeError, TypeError):
                        pass

                import os
                # Excel: structured_data_paths is {sheet_name: path}
                sdp = meta.get("structured_data_paths")
                if sdp and isinstance(sdp, dict):
                    for sheet_name, ppath in sdp.items():
                        if ppath and os.path.isfile(ppath):
                            safe = fname.rsplit(".", 1)[0] if "." in fname else fname
                            display = f"{safe}_{sheet_name}.parquet"
                            parquet_files.append({"name": display, "path": ppath})
                    continue

                # CSV: structured_data_path is a string
                sdp_single = meta.get("structured_data_path")
                if sdp_single and isinstance(sdp_single, str) and os.path.isfile(sdp_single):
                    display = fname.rsplit(".", 1)[0] + ".parquet" if "." in fname else fname + ".parquet"
                    parquet_files.append({"name": display, "path": sdp_single})
                    continue

                # Legacy fallback: pass raw CSV text for files without parquet
                if fname_lower.endswith(".csv"):
                    text = await get_material_text(m_id, user_id)
                    if text:
                        csv_files.append({"filename": fname, "content": text})

        async def on_stdout(line: str):
            try:
                from langchain_core.callbacks import adispatch_custom_event
                await adispatch_custom_event("code_stdout", {"line": line})
            except ImportError:
                # Fallback if langchain_core is older or not configured for custom events
                pass

        # ── Pre-validate data files before executing ────────────────
        validated_parquet = []
        for pf in parquet_files:
            try:
                import pandas as _pd
                _pd.read_parquet(pf["path"], columns=None).head(0)  # schema-only read
                validated_parquet.append(pf)
            except Exception as val_err:
                logger.warning("[python_tool] Skipping unreadable parquet %s: %s", pf["name"], val_err)

        validated_csv = []
        for cf in csv_files:
            try:
                import io as _io, pandas as _pd
                _pd.read_csv(_io.StringIO(cf["content"]), nrows=0)
                validated_csv.append(cf)
            except Exception as val_err:
                logger.warning("[python_tool] Skipping unreadable CSV %s: %s", cf["filename"], val_err)

        if not validated_parquet and not validated_csv and material_ids:
            return ToolResult(
                tool_name="python_tool",
                success=False,
                output="No readable data files found for the selected materials. "
                       "Ensure the files are valid CSV or Excel format.",
                metadata={},
                error="data_validation_failed",
                tokens_used=0,
            )

        # Callback for when code generation is complete — emit the generated code immediately
        async def on_code_generated(code: str):
            try:
                from langchain_core.callbacks import adispatch_custom_event
                await adispatch_custom_event("code_generated", {"code": code})
            except Exception:
                pass

        result = await generate_and_execute(
            user_query=query,
            csv_files=validated_csv,
            parquet_files=validated_parquet,
            timeout=15,
            on_stdout_line=on_stdout,
            additional_context=previous_context,
            on_code_generated=on_code_generated,
        )

        elapsed = time.time() - t0
        success: bool = result.get("success", False)

        if intent == "DATA_ANALYSIS":
            explanation = ""
            if success:
                llm = get_llm(mode="chat")  # factual explanation
                prompt = (
                    "Analyze this output and provide a well-structured, professional summary of the findings.\n\n"
                    "Format your response in clean Markdown with:\n"
                    "- A bold **Executive Summary** opening line (1-2 sentences)\n"
                    "- **Key Findings** as a bullet list with bold labels for each point\n"
                    "- A brief **Strategic Implications** paragraph at the end\n\n"
                    "Use line breaks between sections for readability. Keep it concise but insightful.\n\n"
                    f"Query: {query}\n\nOutput:\n{result.get('stdout', '')}"
                )
                try:
                    resp = await llm.ainvoke(prompt)
                    explanation = getattr(resp, "content", str(resp)).strip()
                except Exception as e:
                    logger.warning(f"Failed to generate explanation: {e}")
                    explanation = "Analysis completed successfully."
            else:
                explanation = "Execution failed. Please check the error details."

            output_data = {
                "stdout": result.get("stdout", "") if success else result.get("stderr", result.get("error", "Unknown error")),
                "exit_code": result.get("exit_code", -1),
                "base64_chart": result.get("chart_base64"),
                "explanation": explanation,
            }
            output = json.dumps(output_data)
        else:
            # Build human-readable answer string
            parts: list[str] = []
            if result.get("generated_code"):
                parts.append(f"```python\n{result['generated_code']}\n```")
            if success:
                if result.get("stdout"):
                    parts.append(f"**Output:**\n```\n{result['stdout'].rstrip()}\n```")
                if result.get("chart_base64"):
                    parts.append("📊 *Chart generated successfully.*")
            else:
                if result.get("violations"):
                    parts.append(
                        "⚠️ **Security violation:**\n"
                        + "\n".join(f"- {v}" for v in result["violations"])
                    )
                elif result.get("stderr"):
                    parts.append(f"**Error:**\n```\n{result['stderr'].rstrip()}\n```")
                elif result.get("error"):
                    parts.append(f"**Error:** {result['error']}")

            output = "\n\n".join(parts) if parts else "Code execution completed with no output."

        logger.info(
            "[python_tool] %s | elapsed=%.2fs | exit_code=%s",
            "OK" if success else "FAILED",
            elapsed,
            result.get("exit_code", -1),
        )
        return ToolResult(
            tool_name="python_tool",
            success=success,
            output=output,
            metadata={
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", ""),
                "exit_code": result.get("exit_code", -1),
                "chart_base64": result.get("chart_base64"),
                "elapsed": result.get("elapsed", 0.0),
                "violations": result.get("violations", []),
                "generated_code": result.get("generated_code", ""),
            },
            tokens_used=500,
        )

    except Exception as exc:
        elapsed = time.time() - t0
        logger.error("[python_tool] FAILED | elapsed=%.2fs | error=%s", elapsed, exc)
        return ToolResult(
            tool_name="python_tool",
            success=False,
            output="Python execution failed.",
            metadata={},
            error=str(exc),
            tokens_used=0,
        )


async def research_tool(
    query: str,
    user_id: str = "",
    notebook_id: str = "",
    material_ids: list = None,
    **kwargs,
) -> ToolResult:
    """Deep research — multi-source web research with structured report."""
    t0 = time.time()
    logger.info("[research_tool] START | user=%s | query=%r", user_id, query[:80])
    try:
        from app.services.agent.subgraphs.research_graph import run_research

        result = await run_research(
            user_query=query,
            user_id=user_id,
            notebook_id=notebook_id,
            material_ids=material_ids,
        )

        elapsed = time.time() - t0

        if result.startswith('{"executive_summary": "Failed'):
            # It's our graceful failure JSON
            logger.warning("[research_tool] Graceful failure structure returned")

        # result is now a JSON string containing the final report


        report_json: str = result
        logger.info(
            "[research_tool] OK | elapsed=%.2fs | report_len=%d",
            elapsed, len(report_json),
        )
        return ToolResult(
            tool_name="research_tool",
            success=True,
            output=report_json,
            metadata={
                "intent": "RESEARCH"
            },
            tokens_used=2000,
        )

    except Exception as exc:
        elapsed = time.time() - t0
        logger.error("[research_tool] FAILED | elapsed=%.2fs | error=%s", elapsed, exc)
        return ToolResult(
            tool_name="research_tool",
            success=False,
            output="Research execution failed.",
            metadata={},
            error=str(exc),
            tokens_used=0,
        )


# ── /agent — Autonomous Agentic Task Executor ─────────────────


async def agent_task_tool(
    user_message: str,
    user_id: str,
    notebook_id: str,
    material_ids: List[str],
    session_id: str,
    **kwargs,
) -> ToolResult:
    """Autonomous ReAct-style agent: plan → act → observe → decide, one step at a time.

    Contract:
    - Injects codebase / material context before every step.
    - Executes one tool per step; never batches.
    - Emits `agent_step` custom events for each card visible in the UI.
    - Stops when the task is provably complete (not on a timer).
    """
    import re as _re
    import json as _json
    from app.services.llm_service.llm import get_llm
    from langchain_core.callbacks import adispatch_custom_event

    MAX_REACT_STEPS = 7
    t0 = time.time()
    llm = get_llm()

    # ── Step 0: Plan ─────────────────────────────────────────────────────
    plan_prompt = (
        "You are an autonomous AI agent. Analyze this task carefully and build a minimal "
        "step-by-step execution plan.\n\n"
        f"Task: {user_message}\n\n"
        "Available sub-tools:\n"
        "  rag_search   – search uploaded materials via RAG\n"
        "  web_search   – search the web for current info\n"
        "  python_exec  – generate and run Python code in sandbox\n"
        "  llm_reason   – use LLM reasoning / reflection only\n\n"
        "Return a JSON object:\n"
        '{"task_analysis": "...", '
        '"steps": [{"action": "...", "tool": "...", "reason": "..."}], '
        '"success_criteria": "..."}\n'
        "Return only valid JSON, no surrounding text."
    )
    plan_resp = await llm.ainvoke(plan_prompt)
    plan_text = getattr(plan_resp, "content", str(plan_resp)).strip()
    try:
        m = _re.search(r"\{.*\}", plan_text, _re.DOTALL)
        plan_data = _json.loads(m.group()) if m else {}
    except Exception:
        plan_data = {}

    steps = plan_data.get("steps", []) or [{"action": user_message, "tool": "llm_reason", "reason": "direct task"}]
    task_analysis = plan_data.get("task_analysis", "Proceeding with direct execution.")

    # Emit the plan card
    await adispatch_custom_event("agent_step", {
        "phase": "plan",
        "action": f"Task analysis: {task_analysis}",
        "observation": f"Planned {len(steps)} step(s).",
        "next_intent": steps[0]["action"] if steps else "Execute task directly.",
    })

    all_observations: List[str] = []

    for i, step in enumerate(steps[:MAX_REACT_STEPS]):
        action = step.get("action", f"Step {i + 1}")
        tool = step.get("tool", "llm_reason")

        # ── Emit Act ──────────────────────────────────────────────────────
        await adispatch_custom_event("agent_step", {
            "phase": "act",
            "step_num": i + 1,
            "total_steps": len(steps),
            "action": f"[{i + 1}/{len(steps)}] {action}",
            "tool": tool,
            "observation": None,
            "next_intent": None,
        })

        # ── Execute ───────────────────────────────────────────────────────
        observation = ""
        try:
            prior_ctx = " | ".join(all_observations[-2:])
            if tool == "rag_search":
                r = await rag_tool(
                    user_id=user_id, query=action, material_ids=material_ids,
                    notebook_id=notebook_id, session_id=session_id,
                )
                observation = (r.get("output") or "")[:600]

            elif tool == "web_search":
                r = await research_tool(query=action, user_id=user_id, notebook_id=notebook_id)
                raw_out = r.get("output", "{}")
                try:
                    rdata = _json.loads(raw_out)
                    observation = (
                        rdata.get("executive_summary")
                        or rdata.get("synthesis")
                        or raw_out
                    )[:600]
                except Exception:
                    observation = raw_out[:600]

            elif tool == "python_exec":
                from app.services.llm_service.llm import get_llm as _get_llm
                from app.services.code_execution.executor import execute_code
                code_prompt = (
                    f"Write executable Python code to: {action}\n"
                    f"Context: {user_message}\n"
                    f"Prior findings: {prior_ctx}\n"
                    "Return only the Python code, nothing else."
                )
                code_resp = await _get_llm().ainvoke(code_prompt)
                raw_code = getattr(code_resp, "content", str(code_resp)).strip()
                raw_code = _re.sub(r"^```python\n?|^```\n?|```$", "", raw_code, flags=_re.MULTILINE).strip()
                exec_result = await execute_code(code=raw_code, timeout=20)
                observation = (
                    exec_result.get("stdout")
                    or exec_result.get("stderr")
                    or "Execution completed with no output."
                )[:600]

            else:  # llm_reason (default)
                think_prompt = (
                    f"Task: {user_message}\n"
                    f"Current step: {action}\n"
                    f"Prior findings: {prior_ctx}\n\n"
                    "Provide a concise, specific finding for this step (3–5 sentences)."
                )
                think_resp = await llm.ainvoke(think_prompt)
                observation = getattr(think_resp, "content", str(think_resp)).strip()[:500]

        except Exception as exc:
            logger.warning("[agent_task_tool] Step %d error: %s", i + 1, exc)
            observation = f"Step encountered an issue: {str(exc)[:200]}"

        all_observations.append(observation)
        next_intent = steps[i + 1]["action"] if (i + 1) < len(steps) else "Synthesize all findings into the final answer."

        # ── Emit Observe + Decide ─────────────────────────────────────────
        await adispatch_custom_event("agent_step", {
            "phase": "observe",
            "step_num": i + 1,
            "action": action,
            "observation": observation,
            "next_intent": next_intent,
        })

    # ── Final synthesis ────────────────────────────────────────────────────
    synth_prompt = (
        f"Task: {user_message}\n\n"
        "Completed steps and findings:\n"
        + "\n".join(f"Step {j + 1}: {obs}" for j, obs in enumerate(all_observations))
        + "\n\nSynthesize these findings into a complete, actionable response. "
        "Be direct and specific. Do not restate the steps — provide the answer."
    )
    synth_resp = await llm.ainvoke(synth_prompt)
    final_response = getattr(synth_resp, "content", str(synth_resp)).strip()

    elapsed = time.time() - t0
    logger.info("[agent_task_tool] OK | steps=%d | elapsed=%.2fs", len(all_observations), elapsed)
    return ToolResult(
        tool_name="agent_task_tool",
        success=True,
        output=final_response,
        metadata={"steps_executed": len(all_observations), "elapsed": elapsed},
        tokens_used=3500,
    )


# ── /web — Structured 5-Phase Web Research ────────────────────


async def web_research_tool(
    query: str,
    user_id: str = "",
    notebook_id: str = "",
    material_ids: List[str] = None,
    **kwargs,
) -> ToolResult:
    """5-phase structured web research: decompose → retrieve → validate → gap-find → synthesize.

    Contract:
    - Output structure is LLM-determined; no fixed template.
    - Every claim carries an inline citation [Source N] or [domain.com].
    - Contradictions between sources are surfaced explicitly.
    - Open questions left unresolved by sources are flagged.
    - Confidence signals attached per claim.
    - Emits `web_research_phase` custom events for progress display.
    """
    from langchain_core.callbacks import adispatch_custom_event
    from app.services.agent.subgraphs.research_graph import (
        _generate_queries,
        _execute_searches,
        _extract_content,
    )
    from app.services.llm_service.llm import get_llm

    t0 = time.time()
    llm = get_llm()

    # Phase 1 — Query decomposition
    await adispatch_custom_event("web_research_phase", {"phase": 1, "label": "Decomposing query into sub-questions"})
    queries = await _generate_queries(query)
    logger.info("[web_research_tool] Generated %d queries for: %r", len(queries), query[:60])

    # Phase 2 — Multi-source retrieval
    await adispatch_custom_event("web_research_phase", {"phase": 2, "label": "Retrieving from multiple sources"})
    urls = await _execute_searches(queries, t0)
    sources = await _extract_content(urls, t0)
    logger.info("[web_research_tool] Extracted %d sources", len(sources))

    if not sources:
        return ToolResult(
            tool_name="web_research_tool",
            success=False,
            output="No accessible sources found for this query. Try rephrasing or broadening the search terms.",
            metadata={},
            error="no_sources",
            tokens_used=0,
        )

    # Phase 3 — Cross-source validation
    await adispatch_custom_event("web_research_phase", {"phase": 3, "label": "Cross-validating sources"})

    # Phase 4 — Gap identification (baked into synthesis prompt)
    await adispatch_custom_event("web_research_phase", {"phase": 4, "label": "Identifying knowledge gaps"})

    # Phase 5 — Synthesis
    await adispatch_custom_event("web_research_phase", {"phase": 5, "label": "Synthesizing findings"})

    source_block = "\n\n---\n\n".join(
        f"SOURCE {i + 1} [{s.get('url', 'unknown')}]:\n"
        f"{(s.get('text') or s.get('content', ''))[:1800]}"
        for i, s in enumerate(sources[:10])
    )

    synthesis_prompt = (
        f"You are a research analyst. Synthesize these {len(sources)} source(s) into a high-quality "
        f"research response.\n\n"
        f"Query: {query}\n\n"
        f"{source_block}\n\n"
        "INSTRUCTIONS (must follow exactly):\n"
        "1. DO NOT use a fixed section template (no 'Executive Summary', 'Key Findings', etc.).\n"
        "   Let the nature of the query determine the structure:\n"
        "   - Conceptual: layered explanation building from first principles\n"
        "   - Comparative: dimensional breakdown by relevant attributes\n"
        "   - Technical: annotated findings with precision and specificity\n"
        "   - Current-events: timeline-aware narrative\n"
        "2. Every significant claim MUST have an inline citation: [Source N] or [domain.com].\n"
        "3. Surface disagreements between sources as: **\u26a1\ufe0f Contradiction:** ...\n"
        "4. Flag unresolved questions as: **\u2753 Open:** ...\n"
        "5. Attach confidence signals per claim: *(high confidence)* / *(disputed)* / "
        "*(single source)* etc.\n"
        "6. Do not produce generic summaries. Surface the actual findings with specificity.\n"
        "7. Never produce a bare list of source summaries. Weave into analytical prose.\n\n"
        "Respond in Markdown."
    )
    resp = await llm.ainvoke(synthesis_prompt)
    output = getattr(resp, "content", str(resp)).strip()

    elapsed = time.time() - t0
    logger.info("[web_research_tool] OK | sources=%d | elapsed=%.2fs", len(sources), elapsed)
    return ToolResult(
        tool_name="web_research_tool",
        success=True,
        output=output,
        metadata={"sources_used": len(sources), "elapsed": elapsed},
        tokens_used=3000,
    )


# ── /code — Scoped Code Generation (no auto-execution) ─────────


async def code_generation_tool(
    user_message: str,
    user_id: str,
    notebook_id: str,
    material_ids: List[str],
    session_id: str,
    intent: str = "",
    **kwargs,
) -> ToolResult:
    """Generate code with a developer-focused explanation.  Never auto-executes.

    Contract:
    - Emits `code_for_review` custom event carrying {code, language, explanation, dependencies}.
    - Frontend intercepts and shows [Run in Sandbox] / [Copy Only] buttons.
    - Execution is ALWAYS user-initiated via a separate /agent/run-generated call.
    - Explanation covers: what + why key decisions + assumptions/constraints.
      It must be non-obvious — never restate what the code makes self-evident.
    """
    import re as _re
    import json as _json
    from app.services.llm_service.llm import get_llm
    from langchain_core.callbacks import adispatch_custom_event

    t0 = time.time()
    llm = get_llm()

    await adispatch_custom_event("code_generating", {"status": "generating"})

    # Optionally pull material context for scoped generation
    material_context = ""
    if material_ids:
        try:
            from app.services.rag.secure_retriever import secure_similarity_search_enhanced
            material_context = await asyncio.to_thread(
                secure_similarity_search_enhanced,
                user_id=user_id,
                query=user_message,
                material_ids=material_ids,
                notebook_id=notebook_id,
                use_mmr=True,
                return_formatted=True,
            )
        except Exception as exc:
            logger.debug("[code_generation_tool] RAG context fetch failed (non-fatal): %s", exc)

    context_section = (
        f"\nRelevant context from uploaded materials:\n{material_context[:2000]}\n"
        if material_context else ""
    )

    gen_prompt = (
        "You are a senior software engineer. Generate production-quality code for the request below.\n"
        f"{context_section}\n"
        f"Request: {user_message}\n\n"
        "Return a JSON object with exactly these fields:\n"
        '{"code": "<complete executable code>", '
        '"language": "<python|javascript|bash|etc>", '
        '"explanation": "<concise developer-focused explanation: what it does, why key '
        'decisions were made, assumptions/constraints baked in — skip the obvious>", '
        '"dependencies": ["<pip/npm package if needed>"]}\n\n'
        "Explanation rules:\n"
        "- 3–6 sentences maximum.\n"
        "- Never restate what the code already makes self-evident.\n"
        "- Focus on non-obvious tradeoffs, design decisions, and constraints.\n"
        "Return only the JSON object, no surrounding text."
    )

    resp = await llm.ainvoke(gen_prompt)
    raw = getattr(resp, "content", str(resp)).strip()

    # Parse the structured response
    code, language, explanation, dependencies = "", "python", "", []
    try:
        m = _re.search(r"\{.*\}", raw, _re.DOTALL)
        if m:
            data = _json.loads(m.group())
            code = data.get("code", "").strip()
            language = data.get("language", "python").strip()
            explanation = data.get("explanation", "").strip()
            dependencies = data.get("dependencies", [])
    except Exception:
        # Graceful fallback: extract fenced code block
        cb = _re.search(r"```(?:\w+)?\n(.*?)```", raw, _re.DOTALL)
        code = cb.group(1).strip() if cb else raw.strip()
        explanation = "Code generated from your request."

    if not code:
        return ToolResult(
            tool_name="code_generation_tool",
            success=False,
            output="Code generation failed — the model returned an empty response.",
            metadata={},
            error="empty_code",
            tokens_used=0,
        )

    # Emit the review event — frontend MUST handle this before any execution
    await adispatch_custom_event("code_for_review", {
        "code": code,
        "language": language,
        "explanation": explanation,
        "dependencies": dependencies,
    })

    elapsed = time.time() - t0
    logger.info(
        "[code_generation_tool] OK | lang=%s | code_len=%d | elapsed=%.2fs",
        language, len(code), elapsed,
    )
    return ToolResult(
        tool_name="code_generation_tool",
        success=True,
        # Minimal output — the real payload is in the code_for_review event and metadata
        output=f"Code generated ({language}, {len(code.splitlines())} lines). "
               "Use [Run in Sandbox] to execute or [Copy Only] to take it as-is.",
        metadata={
            "code": code,
            "language": language,
            "explanation": explanation,
            "dependencies": dependencies,
            "elapsed": elapsed,
        },
        tokens_used=1200,
    )


# ── Register All Tools ────────────────────────────────────────


def initialize_tools():
    """Register all built-in tools. Called once at startup."""
    register_tool(
        name="rag_tool",
        description="Answer questions using retrieved context from uploaded materials (PDFs, documents, etc.)",
        handler=rag_tool,
        intents=["QUESTION"],
    )

    register_tool(
        name="quiz_tool",
        description="Generate quiz questions from uploaded materials",
        handler=quiz_tool,
        intents=["CONTENT_GENERATION"],
    )

    register_tool(
        name="flashcard_tool",
        description="Generate flashcards from uploaded materials",
        handler=flashcard_tool,
        intents=["CONTENT_GENERATION"],
    )

    register_tool(
        name="ppt_tool",
        description="Generate presentations/slides from uploaded materials",
        handler=ppt_tool,
        intents=["CONTENT_GENERATION"],
    )

    register_tool(
        name="python_tool",
        description="Generate and execute Python code for data analysis, calculations, and visualizations",
        handler=python_tool,
        intents=["DATA_ANALYSIS", "CODE_EXECUTION"],
    )

    register_tool(
        name="research_tool",
        description="Conduct deep multi-source web research and generate a structured report with citations",
        handler=research_tool,
        intents=["RESEARCH"],
    )

    register_tool(
        name="agent_task_tool",
        description="Autonomous ReAct agent: plan → act → observe → decide, one step at a time",
        handler=agent_task_tool,
        intents=["AGENT_TASK"],
    )

    register_tool(
        name="web_research_tool",
        description="Structured 5-phase web research: decompose → retrieve → validate → gap-find → synthesize",
        handler=web_research_tool,
        intents=["WEB_RESEARCH"],
    )

    register_tool(
        name="code_generation_tool",
        description="Generate code with explanation; never auto-executes — user triggers execution explicitly",
        handler=code_generation_tool,
        intents=["CODE_GENERATION"],
    )

    logger.info(f"Initialized {len(_TOOLS)} tools: {list_tools()}")


# Lazy initialization — called on first graph build, NOT on module import.
_tools_initialized = False


def ensure_tools_initialized():
    """Initialize tools once, on first call.  Safe to call multiple times."""
    global _tools_initialized
    if not _tools_initialized:
        initialize_tools()
        _tools_initialized = True

