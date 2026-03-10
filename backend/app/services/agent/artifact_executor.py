"""
Artifact executor — generates code, executes it in the sandbox,
registers output files as Artifact records, and returns them.

Used by the agent when file-generation intent is detected so
the user gets an artifact card directly instead of a code block
that requires manual "Run".
"""
from __future__ import annotations

import logging
import mimetypes
import os
import secrets
import shutil
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncIterator, Dict, List, Optional

from app.core.config import settings
from app.services.chat_v2.schemas import ToolResult
from app.services.chat_v2.streaming import sse

logger = logging.getLogger(__name__)

# ── File-generation intent detection ──────────────────────────────────

_FILE_EXTENSIONS = {
    "pdf", "csv", "docx", "doc", "xlsx", "xls", "pptx", "html", "htm",
    "txt", "json", "xml", "md", "png", "jpg", "jpeg", "svg", "gif",
}

_FILE_KEYWORDS = {
    "generate", "create", "make", "build", "export", "produce", "save",
    "write", "download", "output", "give", "show", "plot", "visualize",
    "draw", "display",
}

_FORMAT_KEYWORDS = {
    "pdf", "csv", "excel", "spreadsheet", "document", "docx", "word",
    "powerpoint", "pptx", "html", "report", "file", "image", "chart",
    "png", "jpg", "svg", "scatter", "plot", "histogram", "graph", "figure",
    "heatmap", "boxplot", "visualization", "bar chart", "line chart",
}


def detect_file_generation_intent(goal: str) -> bool:
    """Return *True* if the user's goal implies producing a downloadable file or visual output."""
    lower = goal.lower()
    has_action = any(kw in lower for kw in _FILE_KEYWORDS)
    has_format = any(kw in lower for kw in _FORMAT_KEYWORDS)
    has_as     = " as " in lower  # "… as pdf", "… as csv"
    return (has_action and has_format) or has_as


# ── Artifact helpers (mirrors code_execution.py logic) ────────────────

def _guess_mime(filename: str) -> str:
    mime, _ = mimetypes.guess_type(filename)
    return mime or "application/octet-stream"


def _classify_display_type(filename: str, mime: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    if mime.startswith("image/"):
        return "image"
    if ext in (".csv",) or mime in ("text/csv", "application/csv"):
        return "csv_table"
    if ext in (".xlsx", ".xls"):
        return "csv_table"
    if ext == ".json" or mime == "application/json":
        return "json_tree"
    if ext in (".txt", ".log", ".md") or mime in ("text/plain", "text/markdown"):
        return "text_preview"
    if ext in (".html", ".htm") or mime == "text/html":
        return "html_preview"
    if ext == ".pdf" or mime == "application/pdf":
        return "pdf_embed"
    if mime.startswith("audio/"):
        return "audio_player"
    if mime.startswith("video/"):
        return "video_player"
    return "file_card"


def _detect_output_files(
    work_dir: str,
    skip_filenames: Optional[set] = None,
) -> List[Dict[str, Any]]:
    """Scan the sandbox work directory for produced files.

    ``skip_filenames`` should contain the basenames of any *input* files
    (e.g. uploaded datasets) that were copied in before execution.  Those
    must not be reported as generated outputs.
    """
    if not work_dir or not os.path.isdir(work_dir):
        return []
    skip = {"_kepler_exec.py", "__pycache__"}
    if skip_filenames:
        skip.update(skip_filenames)
    results: List[Dict[str, Any]] = []
    for fname in os.listdir(work_dir):
        if fname in skip or fname.startswith("__"):
            continue
        fpath = os.path.join(work_dir, fname)
        if not os.path.isfile(fpath):
            continue
        size = os.path.getsize(fpath)
        if size == 0:
            continue
        mime = _guess_mime(fname)
        results.append({
            "filename": fname,
            "mime": mime,
            "display_type": _classify_display_type(fname, mime),
            "path": fpath,
            "size": size,
        })
    return results


async def _register_artifact(
    art: Dict[str, Any],
    user_id: str,
    notebook_id: str,
    session_id: str,
) -> Optional[Dict[str, Any]]:
    """Copy file to permanent storage & create DB record."""
    from app.db.prisma_client import prisma

    fpath = art.get("path", "")
    if not fpath or not os.path.isfile(fpath):
        return None

    filename = art["filename"]
    mime = art.get("mime", "application/octet-stream")
    display_type = art.get("display_type", "file_card")
    size = art.get("size", os.path.getsize(fpath))
    ext = os.path.splitext(filename)[1].lower()

    artifact_id = str(uuid.uuid4())
    artifacts_dir = os.path.abspath(settings.ARTIFACTS_DIR)
    os.makedirs(artifacts_dir, exist_ok=True)
    permanent_path = os.path.join(artifacts_dir, f"{artifact_id}{ext}")

    try:
        shutil.copy2(fpath, permanent_path)
    except Exception as exc:
        logger.error("Failed to copy artifact to storage: %s", exc)
        return None

    token = secrets.token_urlsafe(48)
    expiry = datetime.now(timezone.utc) + timedelta(days=36500)

    try:
        record = await prisma.artifact.create(
            data={
                "id": artifact_id,
                "userId": user_id,
                "notebookId": notebook_id,
                "sessionId": session_id,
                "filename": filename,
                "mimeType": mime,
                "displayType": display_type,
                "sizeBytes": size,
                "downloadToken": token,
                "tokenExpiry": expiry,
                "workspacePath": permanent_path,
            }
        )
        return {
            "id": record.id,
            "filename": filename,
            "mime": mime,
            "display_type": display_type,
            "url": f"/api/artifacts/{record.id}",
            "size": size,
        }
    except Exception as exc:
        logger.error("Failed to register artifact: %s", exc)
        try:
            os.remove(permanent_path)
        except OSError:
            pass
        return None


# ── Main execution function ───────────────────────────────────────────

MAX_CODE_REPAIR_ATTEMPTS = 2

_CODE_REPAIR_PROMPT = """\
The following {language} code failed with this error:

ERROR:
{error}

ORIGINAL CODE:
```{language}
{code}
```

Fix the code so it runs without errors. Common fixes:
- Missing imports (add them at the top)
- Wrong file paths (use files in the current directory)
- Library API changes
- Syntax errors

Return ONLY the corrected code — no markdown fences, no explanation.
"""


async def _attempt_code_repair(
    code: str,
    error: str,
    language: str,
) -> str | None:
    """Use LLM to attempt fixing failed code. Returns fixed code or None."""
    try:
        from app.services.llm_service.llm import get_llm

        prompt = _CODE_REPAIR_PROMPT.format(language=language, error=error[:1500], code=code)
        llm = get_llm(temperature=0.1)
        response = await llm.ainvoke(prompt)
        fixed = getattr(response, "content", str(response)).strip()

        # Strip markdown fences
        for fence in (f"```{language}", "```python", "```"):
            if fixed.startswith(fence):
                fixed = fixed[len(fence):].strip()
                break
        if fixed.endswith("```"):
            fixed = fixed[:-3].strip()

        return fixed if fixed and fixed != code else None
    except Exception as exc:
        logger.warning("Code repair failed: %s", exc)
        return None


async def execute_code_and_collect_artifacts(
    code: str,
    user_id: str,
    notebook_id: str,
    session_id: str,
    language: str = "python",
    timeout: int = 60,
    material_ids: Optional[List[str]] = None,
) -> AsyncIterator[str | ToolResult]:
    """
    Execute code in the sandbox, register any output files as artifacts,
    and yield SSE events + ToolResult.

    On failure, attempts automatic code repair up to MAX_CODE_REPAIR_ATTEMPTS times.
    Uploaded material files are copied into the work directory so generated code
    can reference them by their original names.
    """
    from app.services.code_execution.security import validate_code, sanitize_code
    from app.services.code_execution.sandbox import run_in_sandbox

    validation = validate_code(code)
    if not validation.is_safe:
        yield ToolResult(
            tool_name="python",
            success=False,
            content=f"Code validation failed: {'; '.join(validation.violations)}",
            metadata={"error": "validation_failed"},
        )
        return

    code = sanitize_code(code)
    work_dir = tempfile.mkdtemp(prefix="kepler_agent_")

    try:
        # Copy uploaded material files into the sandbox work directory
        input_filenames: set = set()
        if material_ids:
            try:
                from app.services.agent.material_files import (
                    get_material_file_map,
                    copy_materials_to_workdir,
                )
                file_map = await get_material_file_map(material_ids, user_id)
                if file_map:
                    copied = copy_materials_to_workdir(file_map, work_dir)
                    input_filenames = {os.path.basename(p) for p in copied}
                    logger.info("Copied %d material file(s) to sandbox: %s", len(copied), copied)
            except Exception as exc:
                logger.warning("Failed to copy material files to sandbox: %s", exc)

        # Execute with auto-repair loop
        current_code = code
        result = None
        for attempt in range(1 + MAX_CODE_REPAIR_ATTEMPTS):
            result = await run_in_sandbox(
                current_code, work_dir=work_dir, timeout=timeout, language=language,
            )

            if result.exit_code == 0:
                break

            # Attempt repair if we have retries left
            if attempt < MAX_CODE_REPAIR_ATTEMPTS:
                error_msg = result.stderr or result.error or "unknown error"
                logger.info("Code execution failed (attempt %d), attempting repair…", attempt + 1)
                yield sse("agent_status", {
                    "phase": "executing",
                    "message": f"Code failed, repairing (attempt {attempt + 2})…",
                })

                fixed = await _attempt_code_repair(current_code, error_msg, language)
                if fixed:
                    repair_validation = validate_code(fixed)
                    if repair_validation.is_safe:
                        current_code = sanitize_code(fixed)
                        continue
                # Repair failed or invalid — break out
                break

        if result.exit_code != 0:
            yield ToolResult(
                tool_name="python",
                success=False,
                content=f"Code execution failed: {result.stderr or result.error or 'unknown error'}",
                metadata={"error": result.stderr or result.error or "execution_failed", "code": current_code},
            )
            return

        # Detect output files — exclude input material files
        output_files = _detect_output_files(work_dir, skip_filenames=input_filenames)
        registered: List[Dict[str, Any]] = []

        for art in output_files:
            record = await _register_artifact(art, user_id, notebook_id, session_id)
            if record:
                registered.append(record)
                yield sse("agent_artifact", record)

        content_parts = []
        if result.stdout:
            content_parts.append(result.stdout[:2000])
        if registered:
            filenames = ", ".join(r["filename"] for r in registered)
            content_parts.append(f"Generated file(s): {filenames}")

        yield ToolResult(
            tool_name="python",
            success=True,
            content="\n".join(content_parts) or "Code executed successfully.",
            metadata={"code": current_code, "language": language, "phase": "executed"},
            artifacts=registered,
        )
    except Exception as exc:
        logger.error("Artifact executor failed: %s", exc)
        yield ToolResult(
            tool_name="python",
            success=False,
            content=f"Execution error: {exc}",
            metadata={"error": str(exc), "code": code},
        )
    finally:
        try:
            shutil.rmtree(work_dir, ignore_errors=True)
        except Exception:
            pass
