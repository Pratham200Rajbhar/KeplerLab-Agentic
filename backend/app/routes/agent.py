"""Agent route — endpoints for /agent, /code execute, /web, /research modes.

POST /agent/execute-code  — Phase 2 code execution (user clicks Run)
GET  /workspace/file/{id}  — Serve artifact files with token auth
"""

import json
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional

from app.services.auth import get_current_user
from app.core.config import settings
from app.db.prisma_client import prisma

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent", tags=["Agent"])

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


# ── Schemas ───────────────────────────────────────────────────

class ExecuteCodeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=100000)
    notebook_id: str
    session_id: Optional[str] = None
    timeout: int = Field(default=30, ge=5, le=120)


class RunGeneratedCodeRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=100000)
    language: str = "python"
    notebook_id: str
    session_id: Optional[str] = None
    timeout: int = Field(default=30, ge=5, le=120)


# ── POST /agent/execute-code — Phase 2 code execution ────────


@router.post("/execute-code")
async def execute_code(
    request: ExecuteCodeRequest,
    current_user=Depends(get_current_user),
):
    """Execute user-reviewed code in sandbox. Returns SSE stream.
    
    This is Phase 2 of /code mode — triggered when user clicks Run.
    """
    from app.services.code_execution.security import validate_code, sanitize_code
    from app.services.code_execution.sandbox import run_in_sandbox
    from app.services.agent.tools import classify_artifact, _guess_mime, _detect_output_files
    from app.services.llm_service.llm import get_llm
    from app.prompts import get_code_repair_prompt

    async def generate():
        try:
            code = request.code
            yield _sse_event("execution_start", {"session_id": request.session_id})

            # Step 1: Security scan
            validation = validate_code(code)
            if not validation.is_safe:
                yield _sse_event("execution_blocked", {
                    "reason": "; ".join(validation.violations),
                })
                return

            code = sanitize_code(code)

            # Step 2: Create sandbox directory
            import tempfile
            work_dir = tempfile.mkdtemp(prefix="kepler_code_")

            # Step 3: Execute
            result = await run_in_sandbox(
                code, work_dir=work_dir, timeout=request.timeout,
            )

            # Step 4: Handle ImportError
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
                            # Retry
                            result = await run_in_sandbox(
                                code, work_dir=work_dir, timeout=request.timeout,
                            )
                        except Exception as ie:
                            yield _sse_event("install_progress", {
                                "package": module_name, "status": "failed",
                            })

            # Step 5: Handle execution error — offer repair
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

                    # Strip fences
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
                    # In /code mode, user must click Run again for repaired code.
                    # We just send the suggestion and stop.
                    yield _sse_event("execution_done", {
                        "exit_code": result.exit_code,
                        "summary": "Code had an error. Repair suggestion provided.",
                        "elapsed": result.elapsed_seconds,
                        "needs_rerun": True,
                    })
                    return
                except Exception:
                    break

            # Step 6: Success or final failure
            if result.exit_code == 0:
                # Detect produced files
                artifacts = _detect_output_files(work_dir, code)
                for art in artifacts:
                    # Register artifact
                    art_event = await _register_code_artifact(art, current_user, request)
                    if art_event:
                        yield _sse_event("artifact", art_event)

                yield _sse_event("execution_done", {
                    "exit_code": 0,
                    "summary": f"Code executed successfully. {len(artifacts)} file(s) produced.",
                    "elapsed": result.elapsed_seconds,
                })
            else:
                yield _sse_event("execution_done", {
                    "exit_code": result.exit_code,
                    "summary": result.error or result.stderr or "Execution failed",
                    "elapsed": result.elapsed_seconds,
                })

            # Persist execution record
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


# ── POST /agent/run-generated — Run user-edited code ─────────


@router.post("/run-generated")
async def run_generated_code(
    request: RunGeneratedCodeRequest,
    current_user=Depends(get_current_user),
):
    """Execute user-edited generated code. Returns SSE stream."""
    # Delegate to execute-code with same logic
    exec_req = ExecuteCodeRequest(
        code=request.code,
        notebook_id=request.notebook_id,
        session_id=request.session_id,
        timeout=request.timeout,
    )
    return await execute_code(exec_req, current_user)


# ── GET /workspace/file/{artifact_id} — Serve artifact ───────


@router.get("/file/{artifact_id}")
async def serve_artifact(
    artifact_id: str,
    token: str = Query(..., description="Download token"),
):
    """Serve an artifact file with token authentication."""
    from datetime import datetime, timezone

    record = await prisma.artifact.find_unique(where={"id": artifact_id})
    if not record:
        # Try by download token
        record = await prisma.artifact.find_first(where={"downloadToken": token})

    if not record:
        raise HTTPException(status_code=404, detail="Artifact not found")

    if record.downloadToken != token:
        raise HTTPException(status_code=403, detail="Invalid token")

    if record.tokenExpiry < datetime.now(timezone.utc):
        raise HTTPException(status_code=403, detail="Token expired")

    import os
    if not os.path.isfile(record.workspacePath):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=record.workspacePath,
        filename=record.filename,
        media_type=record.mimeType,
    )


# ── Helpers ───────────────────────────────────────────────────


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _register_code_artifact(art, current_user, request):
    """Register a code-produced artifact."""
    import os
    import secrets
    from datetime import datetime, timedelta, timezone
    from app.services.agent.tools import classify_artifact

    fpath = art.get("path", "")
    if not fpath or not os.path.isfile(fpath):
        return None

    filename = art.get("filename", os.path.basename(fpath))
    mime = art.get("mime", "application/octet-stream")
    display_type = art.get("display_type", classify_artifact(filename, mime))
    size = art.get("size", os.path.getsize(fpath))

    token = secrets.token_urlsafe(48)
    expiry = datetime.now(timezone.utc) + timedelta(hours=settings.ARTIFACT_TOKEN_EXPIRY_HOURS)

    try:
        record = await prisma.artifact.create(
            data={
                "userId": str(current_user.id),
                "notebookId": request.notebook_id,
                "sessionId": request.session_id,
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
            "url": f"/agent/file/{record.id}?token={token}",
            "size": size,
        }
    except Exception as e:
        logger.error("Failed to register artifact: %s", e)
        return None
