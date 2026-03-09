"""Agent tools — registry of executable tools for the agent loop.

Each tool is an async function:
    async def tool(inputs: dict, context: AgentContext) -> ToolOutput

Tools available:
  - rag_tool: vector search over user's uploaded materials
  - python_tool: code generation + sandboxed execution
  - web_search_tool: DuckDuckGo search + page scraping
  - research_tool: deep iterative research
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
import time
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ToolOutput:
    """Standard output from any tool."""
    summary: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    code: Optional[str] = None
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class AgentContext:
    """Context passed to every tool invocation."""
    user_id: str
    notebook_id: str
    session_id: str
    material_ids: List[str]
    message: str
    work_dir: str  # Sandbox working directory


# ── Tool: rag_tool ───────────────────────────────────────────


async def rag_tool(inputs: Dict[str, Any], ctx: AgentContext) -> ToolOutput:
    """Vector search over user's uploaded materials.
    
    Input: { query: str }
    Output: { context: str, chunks_used: int, sources: [...] }
    """
    from app.services.rag.secure_retriever import secure_similarity_search_enhanced
    from app.services.rag.context_builder import build_context

    query = inputs.get("query", ctx.message)

    try:
        # Vector search + MMR + reranking
        chunks = await secure_similarity_search_enhanced(
            query=query,
            material_ids=ctx.material_ids,
            user_id=ctx.user_id,
            k=settings.INITIAL_VECTOR_K,
        )

        if not chunks:
            return ToolOutput(
                summary="No relevant content found in materials.",
                data={"context": "", "chunks_used": 0, "sources": []},
            )

        # Build context string within token limit
        context_str = build_context(chunks, max_tokens=settings.MAX_CONTEXT_TOKENS)
        sources = [
            {"content_preview": c.page_content[:200] if hasattr(c, 'page_content') else str(c)[:200]}
            for c in chunks[:5]
        ]

        return ToolOutput(
            summary=f"Retrieved {len(chunks)} relevant chunks from materials.",
            data={"context": context_str, "chunks_used": len(chunks), "sources": sources},
        )
    except Exception as e:
        logger.error("[rag_tool] Failed: %s", e)
        return ToolOutput(
            summary="RAG search failed.",
            error=str(e),
            data={"context": "", "chunks_used": 0, "sources": []},
        )


# ── Tool: python_tool ────────────────────────────────────────


async def python_tool(
    inputs: Dict[str, Any],
    ctx: AgentContext,
    on_event: Optional[Callable] = None,
) -> ToolOutput:
    """Generate Python code from a task, scan it, execute in sandbox.
    
    Input: { task: str, context: str (optional) }
    Output: { exit_code: int, files_produced: [...] }
    """
    from app.services.llm_service.llm import get_llm
    from app.services.code_execution.security import validate_code, sanitize_code
    from app.services.code_execution.sandbox import run_in_sandbox
    from app.prompts import get_code_generation_prompt

    task = inputs.get("task", "")
    context = inputs.get("context", "")

    # Step 1: Generate code
    llm = get_llm(temperature=settings.LLM_TEMPERATURE_CODE)
    prompt_text = get_code_generation_prompt(task)
    if context:
        prompt_text = f"{prompt_text}\n\nAvailable context:\n{context}"

    code_response = await llm.ainvoke(prompt_text)
    code = getattr(code_response, "content", str(code_response)).strip()

    # Strip markdown fences
    if code.startswith("```python"):
        code = code[len("```python"):].strip()
    if code.startswith("```"):
        code = code[3:].strip()
    if code.endswith("```"):
        code = code[:-3].strip()

    # Emit code_generated event
    if on_event:
        await on_event("code_generated", {"code": code, "language": "python"})

    # Step 2: Security scan
    validation = validate_code(code)
    if not validation.is_safe:
        return ToolOutput(
            summary=f"Code blocked by security scan: {'; '.join(validation.violations)}",
            code=code,
            error="Security violation",
            data={"exit_code": -1, "files_produced": []},
        )

    code = sanitize_code(code)

    # Step 3: Execute with repair loop
    max_repairs = settings.MAX_CODE_REPAIR_ATTEMPTS
    attempt = 0

    while attempt <= max_repairs:
        result = await run_in_sandbox(
            code,
            work_dir=ctx.work_dir,
            timeout=settings.CODE_EXECUTION_TIMEOUT,
        )

        if result.exit_code == 0:
            # Success — detect produced files
            artifacts = _detect_output_files(ctx.work_dir, code)

            if on_event and artifacts:
                for art in artifacts:
                    await on_event("artifact", art)

            return ToolOutput(
                summary=f"Code executed successfully. {len(artifacts)} file(s) produced.",
                code=code,
                data={"exit_code": 0, "files_produced": artifacts},
                artifacts=artifacts,
            )

        # Check if it's an ImportError we can handle
        if result.stderr and "ModuleNotFoundError" in result.stderr:
            module_match = _extract_missing_module(result.stderr)
            if module_match and module_match in settings.APPROVED_ON_DEMAND:
                try:
                    from app.services.code_execution.sandbox_env import install_package_if_missing_async
                    await install_package_if_missing_async(module_match)
                    # Retry without incrementing attempt
                    result = await run_in_sandbox(code, work_dir=ctx.work_dir, timeout=settings.CODE_EXECUTION_TIMEOUT)
                    if result.exit_code == 0:
                        artifacts = _detect_output_files(ctx.work_dir, code)
                        if on_event and artifacts:
                            for art in artifacts:
                                await on_event("artifact", art)
                        return ToolOutput(
                            summary=f"Code executed after installing {module_match}. {len(artifacts)} file(s) produced.",
                            code=code,
                            data={"exit_code": 0, "files_produced": artifacts},
                            artifacts=artifacts,
                        )
                except Exception:
                    pass

        # Repair attempt
        attempt += 1
        if attempt > max_repairs:
            break

        if on_event:
            await on_event("repair_attempt", {"attempt": attempt})

        # LLM generates repair
        from app.prompts import get_code_repair_prompt
        repair_prompt = get_code_repair_prompt(code, result.stderr or result.error or "Unknown error")
        repair_response = await llm.ainvoke(repair_prompt)
        repaired = getattr(repair_response, "content", str(repair_response)).strip()

        # Strip fences
        if repaired.startswith("```python"):
            repaired = repaired[len("```python"):].strip()
        if repaired.startswith("```"):
            repaired = repaired[3:].strip()
        if repaired.endswith("```"):
            repaired = repaired[:-3].strip()

        # Validate repaired code
        repair_validation = validate_code(repaired)
        if not repair_validation.is_safe:
            continue

        code = sanitize_code(repaired)

    # All attempts failed
    return ToolOutput(
        summary=f"Code execution failed after {max_repairs} repair attempts.",
        code=code,
        error=result.error or result.stderr or "Execution failed",
        data={"exit_code": result.exit_code, "files_produced": []},
    )


# ── Tool: web_search_tool ────────────────────────────────────


async def web_search_tool(inputs: Dict[str, Any], ctx: AgentContext) -> ToolOutput:
    """Web search via DuckDuckGo + page scraping.
    
    Input: { query: str }
    Output: { results: [{ title, url, content }] }
    """
    from app.core.web_search import ddg_search, fetch_url_content

    query = inputs.get("query", ctx.message)

    try:
        # Search via DuckDuckGo
        raw_results = await ddg_search(query, max_results=5)

        if not raw_results:
            return ToolOutput(
                summary="No web results found.",
                data={"results": []},
            )

        # Scrape top 3 via trafilatura
        scraped = []
        for r in raw_results[:3]:
            url = r["url"]
            try:
                fetched = await fetch_url_content(url)
                if fetched and fetched.get("text"):
                    scraped.append({"title": r["title"], "url": url, "content": fetched["text"][:4000]})
                else:
                    scraped.append({"title": r["title"], "url": url, "content": r["snippet"]})
            except Exception:
                scraped.append({"title": r["title"], "url": url, "content": r["snippet"]})

        return ToolOutput(
            summary=f"Found {len(scraped)} web results for: {query[:60]}",
            data={"results": scraped},
        )
    except Exception as e:
        logger.error("[web_search_tool] Failed: %s", e)
        return ToolOutput(
            summary="Web search failed.",
            error=str(e),
            data={"results": []},
        )


# ── Tool: research_tool ──────────────────────────────────────


async def research_tool(inputs: Dict[str, Any], ctx: AgentContext) -> ToolOutput:
    """Deep iterative research — same as /research mode.
    
    Input: { query: str }
    Output: { report: str, sources: [...] }
    """
    from app.services.research.pipeline import stream_research

    query = inputs.get("query", ctx.message)

    try:
        report_parts = []
        sources = []

        async for event_str in stream_research(
            query=query,
            user_id=ctx.user_id,
            notebook_id=ctx.notebook_id,
            session_id=ctx.session_id,
        ):
            # Parse the SSE event to extract content
            for line in event_str.split("\n"):
                if line.startswith("data: "):
                    try:
                        payload = json.loads(line[len("data: "):])
                        if "content" in payload:
                            report_parts.append(payload["content"])
                        if "citations" in payload:
                            sources = payload["citations"]
                    except json.JSONDecodeError:
                        pass

        report = "".join(report_parts)
        return ToolOutput(
            summary=f"Research complete: {len(report)} chars, {len(sources)} sources.",
            data={"report": report, "sources": sources},
        )
    except Exception as e:
        logger.error("[research_tool] Failed: %s", e)
        return ToolOutput(
            summary="Research failed.",
            error=str(e),
            data={"report": "", "sources": []},
        )


# ── Tool Registry ────────────────────────────────────────────

TOOL_REGISTRY: Dict[str, Callable] = {
    "rag_tool": rag_tool,
    "python_tool": python_tool,
    "web_search_tool": web_search_tool,
    "research_tool": research_tool,
}


# ── Internal helpers ─────────────────────────────────────────


def _detect_output_files(work_dir: str, original_code: str) -> List[Dict[str, Any]]:
    """Scan the workspace directory for files produced by code execution."""
    if not work_dir or not os.path.isdir(work_dir):
        return []

    artifacts = []
    skip_files = {"_kepler_exec.py", "__pycache__"}

    for fname in os.listdir(work_dir):
        if fname in skip_files or fname.startswith("__"):
            continue

        fpath = os.path.join(work_dir, fname)
        if not os.path.isfile(fpath):
            continue

        stat = os.stat(fpath)
        if stat.st_size == 0:
            continue

        mime = _guess_mime(fname)
        display_type = classify_artifact(fname, mime)

        artifacts.append({
            "filename": fname,
            "mime": mime,
            "display_type": display_type,
            "path": fpath,
            "size": stat.st_size,
        })

    return artifacts


def _extract_missing_module(stderr: str) -> Optional[str]:
    """Extract module name from ModuleNotFoundError traceback."""
    import re
    match = re.search(r"No module named '(\w+)'", stderr)
    return match.group(1) if match else None


def _guess_mime(filename: str) -> str:
    """Guess MIME type from filename extension."""
    ext = os.path.splitext(filename)[1].lower()
    mime_map = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml",
        ".csv": "text/csv", ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
        ".json": "application/json",
        ".txt": "text/plain", ".log": "text/plain", ".md": "text/markdown",
        ".html": "text/html", ".htm": "text/html",
        ".pdf": "application/pdf",
        ".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg",
        ".mp4": "video/mp4", ".webm": "video/webm",
        ".py": "text/x-python",
    }
    return mime_map.get(ext, "application/octet-stream")


def classify_artifact(filename: str, mime: str) -> str:
    """Classify an artifact by filename/mime into a display_type.
    
    Returns one of: image, csv_table, json_tree, text_preview,
    html_preview, pdf_embed, audio_player, video_player, file_card
    """
    ext = os.path.splitext(filename)[1].lower()

    if mime.startswith("image/"):
        return "image"
    if mime in ("text/csv", "application/csv") or ext in (".csv",):
        return "csv_table"
    if ext in (".xlsx", ".xls"):
        return "csv_table"
    if mime == "application/json" or ext == ".json":
        return "json_tree"
    if mime in ("text/plain", "text/markdown") or ext in (".txt", ".log", ".md"):
        return "text_preview"
    if mime == "text/html" or ext in (".html", ".htm"):
        return "html_preview"
    if mime == "application/pdf" or ext == ".pdf":
        return "pdf_embed"
    if mime.startswith("audio/"):
        return "audio_player"
    if mime.startswith("video/"):
        return "video_player"

    return "file_card"
