"""
Skills API Router — CRUD + execution endpoints for Agent Skills.
"""
from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.db.prisma_client import prisma
from app.services.auth import get_current_user
from app.services.chat_v2.streaming import SSE_HEADERS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/skills", tags=["Skills"])


async def _require_notebook_access(notebook_id: str, user_id: str) -> None:
    notebook = await prisma.notebook.find_first(
        where={"id": notebook_id, "userId": user_id}
    )
    if not notebook:
        raise HTTPException(status_code=404, detail="Notebook not found")


# ── Request Models ─────────────────────────────────────────

class CreateSkillRequest(BaseModel):
    markdown: str = Field(..., min_length=10, max_length=50000)
    notebook_id: Optional[str] = None
    is_global: bool = False
    tags: Optional[List[str]] = None


class UpdateSkillRequest(BaseModel):
    markdown: str = Field(..., min_length=10, max_length=50000)
    tags: Optional[List[str]] = None


class RunSkillRequest(BaseModel):
    variables: Optional[Dict[str, str]] = None
    notebook_id: Optional[str] = None
    session_id: Optional[str] = None
    material_ids: Optional[List[str]] = None


class ValidateSkillRequest(BaseModel):
    markdown: str = Field(..., min_length=1, max_length=50000)


class SuggestSkillTagsRequest(BaseModel):
    markdown: str = Field(..., min_length=1, max_length=50000)
    max_tags: int = Field(6, ge=3, le=10)


class GenerateSkillDraftRequest(BaseModel):
    prompt: str = Field(..., min_length=6, max_length=4000)


# ── CRUD Endpoints ─────────────────────────────────────────

@router.post("")
async def create_skill_endpoint(
    request: CreateSkillRequest,
    current_user=Depends(get_current_user),
):
    """Create a new skill from markdown."""
    from app.services.skills.skill_service import create_skill

    try:
        if request.notebook_id and request.notebook_id != "draft":
            await _require_notebook_access(request.notebook_id, str(current_user.id))

        skill = await create_skill(
            user_id=str(current_user.id),
            markdown=request.markdown,
            notebook_id=request.notebook_id,
            is_global=request.is_global,
            tags=request.tags,
        )
        return JSONResponse(content=skill, status_code=201)
    except Exception as e:
        logger.error("Failed to create skill: %s", e)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("")
async def list_skills_endpoint(
    notebook_id: Optional[str] = Query(None),
    include_global: bool = Query(True),
    current_user=Depends(get_current_user),
):
    """List skills for the current user."""
    from app.services.skills.skill_service import list_skills

    if notebook_id and notebook_id != "draft":
        await _require_notebook_access(notebook_id, str(current_user.id))

    skills = await list_skills(
        user_id=str(current_user.id),
        notebook_id=notebook_id,
        include_global=include_global,
    )
    return JSONResponse(content={"skills": skills})


@router.get("/templates")
async def get_templates_endpoint(
    current_user=Depends(get_current_user),
):
    """Get built-in skill templates."""
    from app.services.skills.skill_service import get_templates

    templates = await get_templates()
    return JSONResponse(content={"templates": templates})


@router.post("/validate")
async def validate_skill_endpoint(
    request: ValidateSkillRequest,
    current_user=Depends(get_current_user),
):
    """Validate skill markdown without creating."""
    from app.services.skills.markdown_parser import validate_skill_markdown, parse_skill_markdown, skill_to_json

    is_valid, error = validate_skill_markdown(request.markdown)
    if is_valid:
        definition = parse_skill_markdown(request.markdown)
        declared = {inp.name for inp in definition.inputs}
        declared.add("user_input")
        undefined = sorted(v for v in definition.all_variables if v not in declared)
        if undefined:
            return JSONResponse(content={
                "valid": False,
                "error": "Undefined variables: " + ", ".join(undefined),
            })
        return JSONResponse(content={
            "valid": True,
            "parsed": skill_to_json(definition),
        })
    return JSONResponse(content={"valid": False, "error": error})


@router.post("/suggest-tags")
async def suggest_skill_tags_endpoint(
    request: SuggestSkillTagsRequest,
    current_user=Depends(get_current_user),
):
    """Suggest AI-generated tags for skill markdown."""
    from app.services.skills.skill_service import suggest_skill_tags

    try:
        tags = await suggest_skill_tags(request.markdown, request.max_tags)
        return JSONResponse(content={"tags": tags})
    except Exception as e:
        logger.error("Failed to suggest skill tags: %s", e)
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/generate-draft")
async def generate_skill_draft_endpoint(
    request: GenerateSkillDraftRequest,
    current_user=Depends(get_current_user),
):
    """Generate a full skill markdown draft from a natural-language prompt."""
    from app.services.skills.skill_service import generate_skill_draft

    try:
        draft = await generate_skill_draft(
            user_prompt=request.prompt,
        )
        return JSONResponse(content=draft)
    except Exception as e:
        logger.error("Failed to generate skill draft: %s", e)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/runs")
async def list_skill_runs_endpoint(
    skill_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
):
    """List skill execution history."""
    from app.services.skills.skill_service import get_skill_runs

    runs = await get_skill_runs(
        user_id=str(current_user.id),
        skill_id=skill_id,
        limit=limit,
    )
    return JSONResponse(content={"runs": runs})


@router.get("/runs/{run_id}")
async def get_skill_run_endpoint(
    run_id: str,
    current_user=Depends(get_current_user),
):
    """Get a single skill run with full details."""
    from app.services.skills.skill_service import get_skill_run

    run = await get_skill_run(run_id, str(current_user.id))
    if not run:
        raise HTTPException(status_code=404, detail="Skill run not found")
    return JSONResponse(content=run)


@router.get("/{skill_id}")
async def get_skill_endpoint(
    skill_id: str,
    current_user=Depends(get_current_user),
):
    """Get a single skill by ID."""
    from app.services.skills.skill_service import get_skill

    skill = await get_skill(skill_id, str(current_user.id))
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return JSONResponse(content=skill)


@router.put("/{skill_id}")
async def update_skill_endpoint(
    skill_id: str,
    request: UpdateSkillRequest,
    current_user=Depends(get_current_user),
):
    """Update an existing skill."""
    from app.services.skills.skill_service import update_skill

    try:
        skill = await update_skill(
            skill_id=skill_id,
            user_id=str(current_user.id),
            markdown=request.markdown,
            tags=request.tags,
        )
        return JSONResponse(content=skill)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("Failed to update skill: %s", e)
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{skill_id}")
async def delete_skill_endpoint(
    skill_id: str,
    current_user=Depends(get_current_user),
):
    """Delete a skill."""
    from app.services.skills.skill_service import delete_skill

    success = await delete_skill(skill_id, str(current_user.id))
    if not success:
        raise HTTPException(status_code=404, detail="Skill not found")
    return JSONResponse(content={"deleted": True})


@router.post("/{skill_id}/run")
async def run_skill_endpoint(
    skill_id: str,
    request: RunSkillRequest,
    current_user=Depends(get_current_user),
):
    """Execute a skill (SSE streaming response)."""
    from app.services.skills.skill_service import run_skill

    if request.notebook_id and request.notebook_id != "draft":
        await _require_notebook_access(request.notebook_id, str(current_user.id))

    async def generate():
        try:
            async for event in run_skill(
                skill_id=skill_id,
                user_id=str(current_user.id),
                notebook_id=request.notebook_id,
                session_id=request.session_id,
                material_ids=request.material_ids,
                variables=request.variables,
            ):
                yield event
        except Exception as e:
            logger.error("Skill execution failed: %s", e)
            yield f"event: skill_status\ndata: {json.dumps({'status': 'failed', 'error': str(e)})}\n\n"
            yield (
                "event: skill_done\n"
                f"data: {json.dumps({'status': 'failed', 'error': str(e), 'total_steps': 0, 'successful_steps': 0, 'failed_steps': 0, 'artifacts_count': 0, 'elapsed_seconds': 0.0, 'step_logs': [], 'artifacts': [], 'final_output': ''})}\n\n"
            )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
