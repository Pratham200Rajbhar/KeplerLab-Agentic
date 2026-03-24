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
    # Additional common verbs people use when requesting file outputs:
    "compile", "convert", "prepare", "put", "turn", "format", "organize",
    "assemble", "summarize", "summarise", "collect", "gather",
}

_FORMAT_KEYWORDS = {
    "pdf", "csv", "excel", "spreadsheet", "document", "docx", "word",
    "powerpoint", "pptx", "html", "report", "file", "image", "chart",
    "png", "jpg", "svg", "scatter", "plot", "histogram", "graph", "figure",
    "heatmap", "boxplot", "visualization", "bar chart", "line chart",
    "note", "notes",
}

# Matches "into a PDF", "into an Excel file", "into a structured report", etc.
import re as _re
_INTO_FORMAT_PATTERN = _re.compile(
    r"\binto\s+(?:a\s+|an\s+|the\s+)?(?:\w+\s+)*"
    r"(?:pdf|csv|excel|xlsx|docx|word|pptx|powerpoint|html|report|document|spreadsheet|chart)\b",
    _re.IGNORECASE,
)


def detect_file_generation_intent(goal: str) -> bool:
    """Return *True* if the user's goal implies producing a downloadable file or visual output."""
    lower = goal.lower()
    has_action = any(kw in lower for kw in _FILE_KEYWORDS)
    has_format = any(kw in lower for kw in _FORMAT_KEYWORDS)
    has_as     = " as " in lower        # "… as pdf", "… as csv"
    has_into   = bool(_INTO_FORMAT_PATTERN.search(lower))  # "… into a PDF document"
    return (has_action and has_format) or has_as or has_into


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
    skip = {"_kepler_exec.py", "_kepler_bin", "__pycache__", "Main.java"}
    if skip_filenames:
        skip.update(skip_filenames)
    results: List[Dict[str, Any]] = []
    for root, dirs, files in os.walk(work_dir):
        # Prune hidden / cache dirs in-place
        dirs[:] = [d for d in dirs if not d.startswith("__") and not d.startswith(".")]
        for fname in files:
            if fname in skip or fname.startswith("__") or fname.startswith("."):
                continue
            # Also skip the script files (.py, .js etc.) by prefix
            if fname.startswith("_kepler_exec"):
                continue
            fpath = os.path.join(root, fname)
            if not os.path.isfile(fpath):
                continue
            size = os.path.getsize(fpath)
            if size == 0:
                continue
            mime = _guess_mime(fname)
            # Use a relative path as display name (e.g. "output/chart.png")
            display_name = os.path.relpath(fpath, work_dir)
            results.append({
                "filename": display_name,
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

Fix the code so it runs without errors and PRODUCES the output file. Key rules:
- For PDF Generation:
  • Use the provided `kepler_fpdf.PDF` (or `KeplerPDF`) class for robust layout.
  • Example: `from kepler_fpdf import PDF; pdf = PDF(); pdf.add_section("Title"); pdf.multi_cell(0, 10, "Text"); pdf.output("out.pdf")`
  • The `PDF` class automatically loads fonts and handles Unicode/Sanitization.
  • To avoid "not enough space" errors, ALWAYS ensure you are at the correct X/Y before `multi_cell(0)`.
- For charts: `plt.savefig()` then `plt.close()`, NEVER `plt.show()`
- Use relative filenames only (no subdirectories)
- `print("SAVED: <filename>")` after writing each file
- Do NOT wrap in try/except that silently swallows errors — let errors propagate so they can be diagnosed

Return ONLY the corrected {language} code — no markdown fences, no explanation.
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
    timeout: int = 600,
    material_ids: Optional[List[str]] = None,
    step_index: Optional[int] = None,
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
        logger.warning("Code validation failed: %s", validation.violations)
        yield ToolResult(
            tool_name="python",
            success=False,
            content=f"Code validation failed: {'; '.join(validation.violations)}",
            metadata={"error": "validation_failed"},
        )
        return

    code = sanitize_code(code, ensure_file_output=True)
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

        # Copy Kepler Utilities (Root Solution for robust generation)
        try:
            util_src = os.path.join(os.path.dirname(__file__), "kepler_fpdf.py")
            if os.path.exists(util_src):
                shutil.copy2(util_src, os.path.join(work_dir, "kepler_fpdf.py"))
                input_filenames.add("kepler_fpdf.py")
                logger.info("Copied kepler_fpdf.py to sandbox")
        except Exception as util_exc:
            logger.warning("Failed to copy kepler_fpdf utility: %s", util_exc)

        # Copy Unicode fonts for PDF generation support
        try:
            font_dir = "/usr/share/fonts/truetype/dejavu"
            font_files = ["DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans-Oblique.ttf"]
            for font_file in font_files:
                src = os.path.join(font_dir, font_file)
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(work_dir, font_file))
                    input_filenames.add(font_file)
                    logger.info("Copied %s to sandbox", font_file)
                else:
                    # Alternative path
                    alt_src = os.path.join("/usr/share/fonts/dejavu", font_file)
                    if os.path.exists(alt_src):
                        shutil.copy2(alt_src, os.path.join(work_dir, font_file))
                        input_filenames.add(font_file)
                        logger.info("Copied %s to sandbox (alt path)", font_file)
        except Exception as font_exc:
            logger.warning("Failed to copy fonts to sandbox: %s", font_exc)

        # Execute with auto-repair loop
        current_code = code
        result = None
        for attempt in range(1 + MAX_CODE_REPAIR_ATTEMPTS):
            result = await run_in_sandbox(
                current_code, work_dir=work_dir, timeout=timeout, language=language,
            )

            # Determine if this attempt truly succeeded
            is_hard_fail = result.exit_code != 0
            is_silent_fail = False
            if not is_hard_fail:
                # Code exited 0 — check for "silent failure" where a try/except
                # caught the real error and no files were produced.
                _stdout_lower = (result.stdout or "").lower()
                _error_hints = ("error", "traceback", "exception", "failed", "not enough")
                _has_error = any(kw in _stdout_lower for kw in _error_hints)
                _has_output = any(
                    os.path.isfile(os.path.join(work_dir, f))
                    and os.path.getsize(os.path.join(work_dir, f)) > 0
                    and not f.startswith("_kepler")
                    for f in os.listdir(work_dir)
                )
                if _has_error and not _has_output:
                    is_silent_fail = True

            if not is_hard_fail and not is_silent_fail:
                break  # genuine success

            # Attempt repair if retries remain
            if attempt < MAX_CODE_REPAIR_ATTEMPTS:
                if is_hard_fail:
                    error_msg = result.stderr or result.error or "unknown error"
                else:
                    error_msg = (result.stdout or "")[-1500:]
                logger.error(
                    "Code execution %s (attempt %d) exit_code=%d\n--- OUTPUT ---\n%s\n--- END ---",
                    "failed" if is_hard_fail else "silent-failed",
                    attempt + 1, result.exit_code, error_msg[:2000],
                )
                logger.info("Attempting code repair (attempt %d)…", attempt + 1)
                yield sse("agent_status", {
                    "phase": "executing",
                    "message": f"Code issue detected, repairing (attempt {attempt + 2})…",
                    "step_index": step_index,
                })
                fixed = await _attempt_code_repair(current_code, error_msg, language)
                if fixed:
                    repair_validation = validate_code(fixed)
                    if repair_validation.is_safe:
                        current_code = sanitize_code(fixed, ensure_file_output=True)
                        continue
            # Repair failed or out of retries — break
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

        # Cross-check: parse stdout "SAVED: <filename>" and verify those files exist
        if result.stdout:
            import re as _re
            saved_mentions = _re.findall(r"(?:SAVED|Saved):\s*(\S+)", result.stdout)
            detected_names = {of["filename"] for of in output_files}
            for mentioned in saved_mentions:
                mentioned = mentioned.strip().strip("'\"")
                if mentioned not in detected_names:
                    fpath = os.path.join(work_dir, mentioned)
                    if os.path.isfile(fpath) and os.path.getsize(fpath) > 0:
                        mime = _guess_mime(mentioned)
                        output_files.append({
                            "filename": mentioned,
                            "mime": mime,
                            "display_type": _classify_display_type(mentioned, mime),
                            "path": fpath,
                            "size": os.path.getsize(fpath),
                        })
                        logger.info("  → stdout cross-check found: %s", mentioned)

        logger.info(
            "Artifact detection: found %d output file(s) in %s",
            len(output_files), work_dir,
        )
        for of in output_files:
            logger.info("  → %s (%d bytes, %s)", of["filename"], of["size"], of["mime"])

        registered: List[Dict[str, Any]] = []

        for art in output_files:
            record = await _register_artifact(art, user_id, notebook_id, session_id)
            if record:
                registered.append(record)
                if step_index is not None:
                    record["step_index"] = step_index
                yield sse("agent_artifact", record)
            else:
                logger.warning("Failed to register artifact: %s", art.get("filename"))

        content_parts = []
        if result.stdout:
            content_parts.append(result.stdout[:2000])
        if registered:
            filenames = ", ".join(r["filename"] for r in registered)
            content_parts.append(f"Generated file(s): {filenames}")
        elif not registered and output_files:
            content_parts.append("Files were produced but could not be registered as artifacts.")
        elif not output_files:
            # Log debugging info when no files detected despite successful execution
            logger.warning(
                "Code executed OK but no output files found in %s. "
                "Stdout (last 500 chars): %s",
                work_dir, (result.stdout or "")[-500:]
            )
            # List what IS in the directory for debugging
            try:
                all_entries = os.listdir(work_dir)
                logger.warning("  Work dir contents: %s", all_entries)
            except Exception:
                pass

        yield ToolResult(
            tool_name="python",
            success=True,
            content="\n".join(content_parts) or "Code executed successfully (no output files detected).",
            metadata={
                "code": current_code,
                "language": language,
                "phase": "executed",
                "output_file_count": len(output_files),
                "registered_count": len(registered),
            },
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
