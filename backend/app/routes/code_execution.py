import json
import logging
import os
import secrets
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.services.auth import get_current_user
from app.core.config import settings
from app.db.prisma_client import prisma

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/code-execution", tags=["Code Execution"])

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


class ExecuteCodeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=100000)
    language: str = Field(default="python", description="Target language")
    stdin: Optional[str] = Field(default=None, description="Program stdin input")
    notebook_id: str
    session_id: Optional[str] = None
    timeout: int = Field(default=30, ge=5, le=120)


class RunGeneratedCodeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=100000)
    language: str = Field(default="python", description="Target language")
    stdin: Optional[str] = Field(default=None, description="Program stdin input")
    notebook_id: str
    session_id: Optional[str] = None
    timeout: int = Field(default=30, ge=5, le=120)


@router.post("/execute-code")
async def execute_code(
    request: ExecuteCodeRequest,
    current_user=Depends(get_current_user),
):
    from app.services.code_execution.security import validate_code, sanitize_code
    from app.services.code_execution.sandbox import run_in_sandbox
    from app.prompts import get_code_repair_prompt
    from app.services.llm_service.llm import get_llm

    async def generate():
        try:
            code = request.code
            yield _sse_event("execution_start", {"session_id": request.session_id})

            validation = validate_code(code)
            if not validation.is_safe:
                yield _sse_event("execution_blocked", {
                    "reason": "; ".join(validation.violations),
                })
                return

            code = sanitize_code(code)

            import tempfile
            os.makedirs(settings.DATA_TMP_DIR, exist_ok=True)
            work_dir = tempfile.mkdtemp(prefix="kepler_code_", dir=settings.DATA_TMP_DIR)

            result = await run_in_sandbox(
                code, work_dir=work_dir, timeout=request.timeout,
                language=request.language, stdin=request.stdin,
            )

            if result.exit_code != 0 and result.stderr and "ModuleNotFoundError" in result.stderr:
                import re
                match = re.search(r"No module named '(\w+)'", result.stderr)
                if match:
                    module_name = match.group(1)
                    if module_name in settings.APPROVED_ON_DEMAND:
                        yield _sse_event("install_progress", {
                            "package": module_name, "status": "installing",
                        })
                        try:
                            from app.services.code_execution.sandbox_env import install_package_if_missing_async
                            await install_package_if_missing_async(module_name)
                            yield _sse_event("install_progress", {
                                "package": module_name, "status": "done",
                            })
                            result = await run_in_sandbox(
                                code, work_dir=work_dir, timeout=request.timeout,
                                language=request.language, stdin=request.stdin,
                            )
                        except Exception:
                            yield _sse_event("install_progress", {
                                "package": module_name, "status": "failed",
                            })

            repair_attempt = 0
            while result.exit_code != 0 and repair_attempt < settings.MAX_CODE_REPAIR_ATTEMPTS:
                repair_attempt += 1
                try:
                    llm = get_llm(temperature=settings.LLM_TEMPERATURE_CODE)
                    repair_prompt = get_code_repair_prompt(
                        code, result.stderr or result.error or "Execution failed"
                    )
                    repair_response = await llm.ainvoke(repair_prompt)
                    repaired = getattr(repair_response, "content", str(repair_response)).strip()

                    if repaired.startswith("```python"):
                        repaired = repaired[len("```python"):].strip()
                    if repaired.startswith("```"):
                        repaired = repaired[3:].strip()
                    if repaired.endswith("```"):
                        repaired = repaired[:-3].strip()

                    rv = validate_code(repaired)
                    if not rv.is_safe:
                        break

                    yield _sse_event("repair_suggestion", {
                        "attempt": repair_attempt,
                        "code": repaired,
                        "explanation": f"Auto-repaired (attempt {repair_attempt}/{settings.MAX_CODE_REPAIR_ATTEMPTS})",
                    })
                    yield _sse_event("execution_done", {
                        "exit_code": result.exit_code,
                        "summary": "Code had an error. Repair suggestion provided.",
                        "elapsed": result.elapsed_seconds,
                        "needs_rerun": True,
                    })
                    return
                except Exception:
                    break

            if result.exit_code == 0:
                artifacts = _detect_output_files(work_dir, code)
                for art in artifacts:
                    art_event = await _register_code_artifact(art, current_user, request)
                    if art_event:
                        yield _sse_event("artifact", art_event)

                has_stdout = bool((result.stdout or "").strip())
                has_stderr = bool((result.stderr or "").strip())
                if has_stdout or has_stderr or artifacts:
                    success_summary = f"Code executed successfully. {len(artifacts)} file(s) produced."
                else:
                    success_summary = (
                        "Code executed successfully, but produced no output. "
                        "This script may only define functions/classes and not print anything."
                    )

                yield _sse_event("execution_done", {
                    "exit_code": 0,
                    "stdout": result.stdout or "",
                    "stderr": result.stderr or "",
                    "summary": success_summary,
                    "elapsed": result.elapsed_seconds,
                })
            else:
                yield _sse_event("execution_done", {
                    "exit_code": result.exit_code,
                    "stdout": result.stdout or "",
                    "stderr": result.stderr or result.error or "Execution failed",
                    "summary": result.error or result.stderr or "Execution failed",
                    "elapsed": result.elapsed_seconds,
                })

            try:
                await prisma.codeexecutionsession.create(
                    data={
                        "userId": str(current_user.id),
                        "notebookId": request.notebook_id,
                        "code": code,
                        "stdout": result.stdout[:5000] if result.stdout else None,
                        "stderr": result.stderr[:5000] if result.stderr else None,
                        "exitCode": result.exit_code,
                        "hasChart": bool(result.chart_base64),
                        "elapsedTime": result.elapsed_seconds,
                    }
                )
            except Exception as pe:
                logger.warning("Failed to persist code execution: %s", pe)

        except Exception as e:
            logger.error("Code execution failed: %s", e)
            yield _sse_event("error", {"error": str(e)})

    return StreamingResponse(generate(), media_type="text/event-stream", headers=_SSE_HEADERS)


@router.post("/run-generated")
async def run_generated_code(
    request: RunGeneratedCodeRequest,
    current_user=Depends(get_current_user),
):
    exec_req = ExecuteCodeRequest(
        code=request.code,
        language=request.language,
        stdin=request.stdin,
        notebook_id=request.notebook_id,
        session_id=request.session_id,
        timeout=request.timeout,
    )
    return await execute_code(exec_req, current_user)


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _guess_mime(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    mime_map = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml",
        ".csv": "text/csv",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
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


def _classify_artifact(filename: str, mime: str) -> str:
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


def _detect_output_files(work_dir: str, original_code: str):
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
        display_type = _classify_artifact(fname, mime)
        artifacts.append({
            "filename": fname,
            "mime": mime,
            "display_type": display_type,
            "path": fpath,
            "size": stat.st_size,
        })

    return artifacts


_DISPLAY_TYPE_CATEGORY = {
    "image":        "charts",
    "csv_table":    "datasets",
    "json_tree":    "datasets",
    "text_preview": "reports",
    "html_preview": "reports",
    "pdf_embed":    "reports",
}
_MODEL_EXTS = {".pkl", ".pickle", ".joblib", ".h5", ".pt", ".pth", ".onnx", ".pb", ".keras"}


async def _register_code_artifact(art, current_user, request):
    fpath = art.get("path", "")
    if not fpath or not os.path.isfile(fpath):
        return None

    filename = art.get("filename", os.path.basename(fpath))
    mime = art.get("mime", "application/octet-stream")
    display_type = art.get("display_type", _classify_artifact(filename, mime))
    size = art.get("size", os.path.getsize(fpath))

    ext = os.path.splitext(filename)[1].lower()
    category = "models" if ext in _MODEL_EXTS else _DISPLAY_TYPE_CATEGORY.get(display_type, "files")

    artifact_id = str(uuid.uuid4())
    artifacts_dir = os.path.abspath(settings.ARTIFACTS_DIR)
    os.makedirs(artifacts_dir, exist_ok=True)
    permanent_path = os.path.join(artifacts_dir, f"{artifact_id}{ext}")
    try:
        shutil.copy2(fpath, permanent_path)
    except Exception as copy_err:
        logger.error("Failed to copy code artifact to permanent storage: %s", copy_err)
        return None

    token = secrets.token_urlsafe(48)
    expiry = datetime.now(timezone.utc) + timedelta(days=36500)
    try:
        record = await prisma.artifact.create(
            data={
                "id": artifact_id,
                "userId": str(current_user.id),
                "notebookId": request.notebook_id,
                "sessionId": request.session_id,
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
            "category": category,
            "display_type": display_type,
            "url": f"/api/artifacts/{record.id}",
            "size": size,
        }
    except Exception as e:
        logger.error("Failed to register code artifact: %s", e)
        try:
            os.remove(permanent_path)
        except OSError:
            pass
        return None
