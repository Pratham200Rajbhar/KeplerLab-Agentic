"""Agent route — endpoints for /agent, /code execute, /web, /research modes.

POST /agent/execute       — Full agent pipeline execution (SSE)
POST /agent/execute-code  — Phase 2 code execution (user clicks Run)
GET  /agent/file/{id}     — Serve artifact files with token auth
POST /agent/refresh-token — Refresh artifact download token
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

class AgentExecuteRequest(BaseModel):
    """Request schema for agent execution."""
    message: str = Field(..., min_length=1, max_length=10000, description="User message/request")
    notebook_id: str = Field(..., description="Notebook ID")
    material_ids: List[str] = Field(default_factory=list, description="IDs of materials to use")
    session_id: Optional[str] = Field(None, description="Session ID for context")


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


class RefreshTokenRequest(BaseModel):
    artifact_id: str


# ── POST /agent/execute — Full agent pipeline ────────────────


@router.post("/execute")
async def execute_agent(
    request: AgentExecuteRequest,
    current_user=Depends(get_current_user),
):
    """Execute the full agent pipeline. Returns SSE stream.
    
    This is the main endpoint for agent execution. It:
    1. Analyzes the user request
    2. Plans execution steps
    3. Executes tools (RAG, Python sandbox, web search, etc.)
    4. Generates artifacts (charts, models, reports)
    5. Returns structured results with streaming progress
    
    Events emitted:
    - step: Current execution step/status
    - intent: Detected task type and confidence  
    - agent_start: Execution plan
    - code_generated: Generated Python code
    - artifact: Generated file info
    - tool_result: Tool execution result
    - summary: Execution summary
    - token: Response text tokens
    - done: Completion with metadata
    - error: Error information
    """
    from app.services.agent.pipeline import stream_agent
    import uuid

    session_id = request.session_id or str(uuid.uuid4())

    async def generate():
        try:
            async for event in stream_agent(
                message=request.message,
                notebook_id=request.notebook_id,
                material_ids=request.material_ids,
                session_id=session_id,
                user_id=str(current_user.id),
            ):
                yield event
        except Exception as e:
            logger.error("Agent execution failed: %s", e, exc_info=True)
            yield _sse_event("error", {"error": str(e)})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


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
                language=request.language, stdin=request.stdin,
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
                                language=request.language, stdin=request.stdin,
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
                    "stdout": result.stdout or "",
                    "stderr": result.stderr or "",
                    "summary": f"Code executed successfully. {len(artifacts)} file(s) produced.",
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
    # Delegate to execute-code with same logic, forwarding language + stdin
    exec_req = ExecuteCodeRequest(
        code=request.code,
        language=request.language,
        stdin=request.stdin,
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


# ── POST /agent/refresh-token — Refresh artifact download token


@router.post("/refresh-token")
async def refresh_artifact_token(
    request: RefreshTokenRequest,
    current_user=Depends(get_current_user),
):
    """Refresh download token for an artifact.
    
    Use this when a token has expired but the artifact is still needed.
    """
    import secrets
    from datetime import datetime, timedelta, timezone

    record = await prisma.artifact.find_unique(where={"id": request.artifact_id})
    
    if not record:
        raise HTTPException(status_code=404, detail="Artifact not found")
    
    # Verify ownership
    if record.userId != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Generate new token
    new_token = secrets.token_urlsafe(48)
    new_expiry = datetime.now(timezone.utc) + timedelta(hours=settings.ARTIFACT_TOKEN_EXPIRY_HOURS)
    
    await prisma.artifact.update(
        where={"id": request.artifact_id},
        data={
            "downloadToken": new_token,
            "tokenExpiry": new_expiry,
        }
    )
    
    return {
        "artifact_id": request.artifact_id,
        "url": f"/agent/file/{request.artifact_id}?token={new_token}",
        "expires_at": new_expiry.isoformat(),
    }


# ── GET /agent/artifacts — List user's artifacts ─────────────


@router.get("/artifacts")
async def list_artifacts(
    notebook_id: Optional[str] = Query(None, description="Filter by notebook"),
    session_id: Optional[str] = Query(None, description="Filter by session"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    current_user=Depends(get_current_user),
):
    """List artifacts for the current user.
    
    Artifacts can be filtered by notebook, session, or category.
    """
    from datetime import datetime, timezone

    where_clause = {"userId": str(current_user.id)}
    
    if notebook_id:
        where_clause["notebookId"] = notebook_id
    if session_id:
        where_clause["sessionId"] = session_id
    if category:
        where_clause["displayType"] = category

    artifacts = await prisma.artifact.find_many(
        where=where_clause,
        order={"createdAt": "desc"},
        take=limit,
    )
    
    now = datetime.now(timezone.utc)
    
    result = []
    for art in artifacts:
        is_expired = art.tokenExpiry < now
        result.append({
            "id": art.id,
            "filename": art.filename,
            "mime": art.mimeType,
            "display_type": art.displayType,
            "size": art.sizeBytes,
            "url": f"/agent/file/{art.id}?token={art.downloadToken}" if not is_expired else None,
            "is_expired": is_expired,
            "created_at": art.createdAt.isoformat(),
            "notebook_id": art.notebookId,
            "session_id": art.sessionId,
        })
    
    return {"artifacts": result, "count": len(result)}


# ── GET /agent/artifacts/by-category — Group artifacts by category


@router.get("/artifacts/by-category")
async def get_artifacts_by_category(
    notebook_id: Optional[str] = Query(None, description="Filter by notebook"),
    session_id: Optional[str] = Query(None, description="Filter by session"),
    current_user=Depends(get_current_user),
):
    """Get artifacts grouped by category.
    
    Categories: chart, table, model, report, dataset, file
    """
    from datetime import datetime, timezone
    from collections import defaultdict

    where_clause = {"userId": str(current_user.id)}
    
    if notebook_id:
        where_clause["notebookId"] = notebook_id
    if session_id:
        where_clause["sessionId"] = session_id

    artifacts = await prisma.artifact.find_many(
        where=where_clause,
        order={"createdAt": "desc"},
    )
    
    now = datetime.now(timezone.utc)
    grouped = defaultdict(list)
    
    # Category mapping based on display type
    category_map = {
        "image": "charts",
        "csv_table": "tables",
        "model_card": "models",
        "pdf_embed": "reports",
        "text_preview": "files",
        "json_tree": "files",
        "file_card": "files",
    }
    
    for art in artifacts:
        is_expired = art.tokenExpiry < now
        category = category_map.get(art.displayType, "files")
        
        grouped[category].append({
            "id": art.id,
            "filename": art.filename,
            "mime": art.mimeType,
            "display_type": art.displayType,
            "size": art.sizeBytes,
            "url": f"/agent/file/{art.id}?token={art.downloadToken}" if not is_expired else None,
            "is_expired": is_expired,
            "created_at": art.createdAt.isoformat(),
        })
    
    return {
        "charts": grouped.get("charts", []),
        "tables": grouped.get("tables", []),
        "models": grouped.get("models", []),
        "reports": grouped.get("reports", []),
        "datasets": grouped.get("datasets", []),
        "files": grouped.get("files", []),
        "total_count": len(artifacts),
    }


# ── Helpers ───────────────────────────────────────────────────


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _register_code_artifact(art, current_user, request):
    """Copy a code-produced artifact to permanent storage and register it."""
    import os
    import shutil
    import secrets
    import uuid
    from datetime import datetime, timedelta, timezone
    from app.services.agent.tools import classify_artifact

    fpath = art.get("path", "")
    if not fpath or not os.path.isfile(fpath):
        return None

    filename = art.get("filename", os.path.basename(fpath))
    mime = art.get("mime", "application/octet-stream")
    display_type = art.get("display_type", classify_artifact(filename, mime))
    size = art.get("size", os.path.getsize(fpath))

    _DISPLAY_TYPE_CATEGORY = {
        "image":        "charts",
        "csv_table":    "datasets",
        "json_tree":    "datasets",
        "text_preview": "reports",
        "html_preview": "reports",
        "pdf_embed":    "reports",
    }
    _MODEL_EXTS = {".pkl", ".pickle", ".joblib", ".h5", ".pt", ".pth", ".onnx", ".pb", ".keras"}
    ext = os.path.splitext(filename)[1].lower()
    category = "models" if ext in _MODEL_EXTS else _DISPLAY_TYPE_CATEGORY.get(display_type, "files")

    # Pre-generate stable UUID and copy to permanent storage
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
    expiry = datetime.now(timezone.utc) + timedelta(days=36500)  # 100 years
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
