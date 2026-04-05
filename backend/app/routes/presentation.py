"""
Presentation API routes — endpoints for generating presentations and explainer videos.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.services.auth import get_current_user
from app.services.podcast.voice_map import (
    normalize_language_code,
    validate_voice,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/presentation", tags=["Presentation"])


# ── Request / Response models ──────────────────────────────────────────────

class GeneratePresentationRequest(BaseModel):
    notebook_id: str
    material_ids: List[str]
    topic: Optional[str] = None
    theme_prompt: Optional[str] = None
    slide_count: Optional[int] = Field(default=None, ge=3, le=25)
    argumentation_notes: Optional[str] = None


class GenerateVideoRequest(BaseModel):
    voice_id: str
    narration_language: str = "en"
    ppt_language: str = "en"
    narration_style: Optional[str] = None
    narration_notes: Optional[str] = None
    auto_generate_slides: bool = True
    notebook_id: Optional[str] = None
    material_ids: Optional[List[str]] = None
    topic: Optional[str] = None
    theme_prompt: Optional[str] = None
    slide_count: Optional[int] = Field(default=None, ge=3, le=25)
    argumentation_notes: Optional[str] = None


class RegenerateSlideRequest(BaseModel):
    slide_index: int = Field(..., ge=0)


class PresentationResponse(BaseModel):
    id: str
    jobId: str
    status: str = "started"
    message: str = "Generation started"


class VideoResponse(BaseModel):
    videoId: str
    jobId: str
    status: str = "started"
    message: str = "Video generation started"


def _resolve_voice_for_language(
    requested_voice_id: str,
    language: str,
) -> str:
    normalized_language = normalize_language_code(language)
    if validate_voice(requested_voice_id, normalized_language):
        return requested_voice_id
    raise ValueError(
        f"Voice '{requested_voice_id}' is not valid for language '{normalized_language}'"
    )


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/generate", response_model=PresentationResponse)
async def generate_presentation_endpoint(
    req: GeneratePresentationRequest,
    user=Depends(get_current_user),
):
    """Start async presentation generation. Progress is streamed via WebSocket."""
    user_id = str(user.id)

    if not req.material_ids:
        raise HTTPException(status_code=400, detail="At least one material_id is required")

    if len(req.material_ids) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 materials per presentation")

    from app.services.presentation.presentation_service import generate_presentation

    presentation_id = str(uuid.uuid4())
    job_id = "legacy-job-none"  # Return a placeholder for compatibility with Response models

    # Fire and forget — results come via WebSocket
    async def _run():
        try:
            await generate_presentation(
                user_id=user_id,
                notebook_id=req.notebook_id,
                material_ids=req.material_ids,
                topic=req.topic,
                theme_prompt=req.theme_prompt,
                target_slide_count=req.slide_count,
                argumentation_notes=req.argumentation_notes,
                presentation_id=presentation_id,
            )
        except Exception as exc:
            logger.exception("Background presentation generation failed: %s", exc)

    asyncio.create_task(_run())

    return PresentationResponse(
        id=presentation_id,
        jobId=job_id,
        status="started",
        message=f"Generating presentation from {len(req.material_ids)} source(s)...",
    )


@router.post("/{presentation_id}/generate-video", response_model=VideoResponse)
async def generate_video_endpoint(
    presentation_id: str,
    req: GenerateVideoRequest,
    user=Depends(get_current_user),
):
    """Start async explainer video generation for an existing presentation."""
    user_id = str(user.id)

    from app.services.presentation.presentation_service import get_presentation

    existing = await get_presentation(presentation_id, user_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Presentation not found")

    from app.services.presentation.presentation_service import generate_video

    try:
        normalized_narration_language = normalize_language_code(req.narration_language)
        resolved_voice_id = _resolve_voice_for_language(
            requested_voice_id=req.voice_id,
            language=normalized_narration_language,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    job_id = "legacy-job-none"

    async def _run():
        try:
            result = await generate_video(
                user_id=user_id,
                presentation_id=presentation_id,
                voice_id=resolved_voice_id,
                narration_language=normalized_narration_language,
                ppt_language=req.ppt_language,
                narration_style=req.narration_style,
                narration_notes=req.narration_notes,
                auto_generate_slides=req.auto_generate_slides,
                fallback_notebook_id=req.notebook_id,
                fallback_material_ids=req.material_ids,
                fallback_topic=req.topic,
                fallback_theme_prompt=req.theme_prompt,
                fallback_target_slide_count=req.slide_count,
                fallback_argumentation_notes=req.argumentation_notes,
            )
        except Exception as exc:
            logger.exception("Background video generation failed: %s", exc)

    asyncio.create_task(_run())

    return VideoResponse(
        videoId="pending",
        jobId=job_id,
        status="started",
        message="Generating explainer video...",
    )


@router.get("/{presentation_id}")
async def get_presentation_endpoint(
    presentation_id: str,
    user=Depends(get_current_user),
):
    """Get presentation details including slides and video status."""
    from app.services.presentation.presentation_service import get_presentation

    result = await get_presentation(presentation_id, str(user.id))
    if not result:
        raise HTTPException(status_code=404, detail="Presentation not found")

    return result


@router.get("/{presentation_id}/slides")
async def get_slides_endpoint(
    presentation_id: str,
    user=Depends(get_current_user),
):
    """Get the slides for a presentation."""
    from app.services.presentation.presentation_service import get_presentation

    result = await get_presentation(presentation_id, str(user.id))
    if not result:
        raise HTTPException(status_code=404, detail="Presentation not found")

    return {"slides": result.get("data", {}).get("slides", [])}


@router.get("/{presentation_id}/video")
async def get_video_endpoint(
    presentation_id: str,
    user=Depends(get_current_user),
):
    """Get the video details for a presentation."""
    from app.services.presentation.presentation_service import get_presentation

    result = await get_presentation(presentation_id, str(user.id))
    if not result:
        raise HTTPException(status_code=404, detail="Presentation not found")

    if not result.get("video"):
        raise HTTPException(status_code=404, detail="No video found for this presentation")

    return result["video"]


@router.post("/{presentation_id}/slides/{slide_index}/regenerate")
async def regenerate_slide_endpoint(
    presentation_id: str,
    slide_index: int,
    user=Depends(get_current_user),
):
    """Regenerate a single slide in an existing presentation."""
    user_id = str(user.id)

    from app.services.presentation.presentation_service import regenerate_slide

    try:
        result = await regenerate_slide(user_id, presentation_id, slide_index)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Slide regeneration failed: %s", exc)
        raise HTTPException(status_code=500, detail="Slide regeneration failed")


# ── Export endpoints ──────────────────────────────────────────────────────────

@router.get("/{presentation_id}/export/pptx")
async def export_pptx(
    presentation_id: str,
    user=Depends(get_current_user),
):
    """Export a completed presentation as a PPTX file (16:9, images embedded)."""
    import asyncio
    from fastapi.responses import Response
    from app.services.presentation.presentation_service import get_presentation
    from app.services.presentation.export_service import build_pptx, resolve_slide_image_paths

    user_id = str(user.id)

    data = await get_presentation(presentation_id, user_id)
    if not data:
        raise HTTPException(status_code=404, detail="Presentation not found")

    pdata = data.get("data", {}) or {}
    slides = pdata.get("slides", [])
    if not slides:
        raise HTTPException(status_code=404, detail="No slides found in this presentation")

    theme_spec = pdata.get("themeSpec")
    title = str(pdata.get("title") or data.get("title") or "Presentation")

    enriched = await resolve_slide_image_paths(slides)

    try:
        pptx_bytes = await asyncio.to_thread(
            build_pptx, enriched, title, theme_spec
        )
    except Exception as exc:
        logger.exception("PPTX export failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"PPTX export failed: {exc}")

    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)[:60]
    return Response(
        content=pptx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_title}.pptx"',
            "Content-Length": str(len(pptx_bytes)),
        },
    )


@router.get("/{presentation_id}/export/pdf")
async def export_pdf(
    presentation_id: str,
    user=Depends(get_current_user),
):
    """Export a completed presentation as a multi-page PDF (1280×720 per page)."""
    import asyncio
    from fastapi.responses import Response
    from app.services.presentation.presentation_service import get_presentation
    from app.services.presentation.export_service import build_pdf, resolve_slide_image_paths

    user_id = str(user.id)

    data = await get_presentation(presentation_id, user_id)
    if not data:
        raise HTTPException(status_code=404, detail="Presentation not found")

    pdata = data.get("data", {}) or {}
    slides = pdata.get("slides", [])
    if not slides:
        raise HTTPException(status_code=404, detail="No slides found in this presentation")

    theme_spec = pdata.get("themeSpec")
    title = str(pdata.get("title") or data.get("title") or "Presentation")

    enriched = await resolve_slide_image_paths(slides)

    try:
        pdf_bytes = await asyncio.to_thread(
            build_pdf, enriched, title, theme_spec
        )
    except Exception as exc:
        logger.exception("PDF export failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"PDF export failed: {exc}")

    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)[:60]
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_title}.pdf"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )



# ── PPTX Upload + Explain endpoint ────────────────────────────────────────────

from fastapi import UploadFile, File, Form

@router.post("/explain-pptx", response_model=VideoResponse)
async def explain_pptx_upload(
    voice_id: str = Form(...),
    narration_language: str = Form("en"),
    narration_style: Optional[str] = Form(None),
    narration_notes: Optional[str] = Form(None),
    notebook_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    """
    Upload a PPTX/PPT file and generate an AI explainer video from it.
    Progress is streamed via WebSocket (same events as AI-generated deck).
    """
    user_id = str(user.id)

    filename = file.filename or "upload.pptx"
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in {"pptx", "ppt"}:
        raise HTTPException(status_code=422, detail="Only .pptx and .ppt files are supported")

    file_bytes = await file.read()
    if len(file_bytes) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 100 MB)")

    try:
        normalized_language = normalize_language_code(narration_language)
        resolved_voice = _resolve_voice_for_language(voice_id, normalized_language)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    from app.db.prisma_client import prisma
    if not notebook_id:
        logger.info("No notebook_id provided, creating 'Global Hub'")
        hub_query = await prisma.notebook.find_first(
            where={"userId": user.id, "name": "Global Hub"}
        )
        if hub_query:
            notebook_id = hub_query.id
        else:
            new_hub = await prisma.notebook.create(
                data={"userId": user.id, "name": "Global Hub"}
            )
            notebook_id = new_hub.id

    presentation_id = str(uuid.uuid4())
    job_id = "legacy-job-none"

    async def _run():
        try:
            await _explain_pptx_pipeline(
                user_id=user_id,
                presentation_id=presentation_id,
                file_bytes=file_bytes,
                filename=filename,
                voice_id=resolved_voice,
                narration_language=normalized_language,
                narration_style=narration_style,
                narration_notes=narration_notes,
                notebook_id=notebook_id,
            )
        except Exception as exc:
            logger.exception("PPTX explain pipeline failed: %s", exc)

    asyncio.create_task(_run())

    return VideoResponse(
        videoId=presentation_id,
        jobId=job_id,
        status="started",
        message=f"Extracting and explaining {filename}...",
    )


async def _explain_pptx_pipeline(
    *,
    user_id: str,
    presentation_id: str,
    file_bytes: bytes,
    filename: str,
    voice_id: str,
    narration_language: str,
    narration_style,
    narration_notes,
    notebook_id: str,
) -> None:
    """Full background pipeline: extract PPTX → save artifacts → generate video."""
    import json
    import os
    import secrets
    from datetime import datetime, timedelta, timezone

    from app.core.config import settings
    from app.db.prisma_client import prisma
    from app.services.ws_manager import ws_manager
    from app.services.presentation.pptx_extractor import extract_slides_from_pptx
    from app.services.presentation.video_generator import generate_explainer_video

    output_base = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "output", "presentations")
    )
    output_dir = os.path.join(output_base, presentation_id)
    os.makedirs(output_dir, exist_ok=True)

    async def emit(event_type: str, data: dict):
        try:
            await ws_manager.send_to_user(user_id, {"type": event_type, **data})
        except Exception:
            pass

    await emit("presentation_status", {
        "presentationId": presentation_id,
        "phase": "extracting",
        "message": f"Extracting slides from {filename}…",
    })

    extracted = await extract_slides_from_pptx(file_bytes, filename)

    slide_data = []
    image_paths = []
    context_chunks = {}

    for slide in extracted:
        img_filename = f"slide_{slide.index:03d}.png"
        img_path = os.path.join(output_dir, img_filename)
        with open(img_path, "wb") as f:
            f.write(slide.image_bytes)

        artifact = await prisma.artifact.create(data={
            "userId": user_id,
            "notebookId": notebook_id,
            "filename": img_filename,
            "mimeType": "image/png",
            "sizeBytes": len(slide.image_bytes),
            "downloadToken": secrets.token_urlsafe(32),
            "tokenExpiry": datetime.now(timezone.utc) + timedelta(hours=settings.ARTIFACT_TOKEN_EXPIRY_HOURS),
            "workspacePath": img_path,
        })

        sd = {
            "title": slide.title,
            "bullets": slide.bullets,
            "argument_role": slide.argument_role,
            "visual_style": slide.visual_style,
            "imageUrl": f"/artifacts/{artifact.id}",
            "artifactId": artifact.id,
            "status": "completed",
            "index": slide.index,
        }
        slide_data.append(sd)
        image_paths.append(img_path)
        if slide.raw_text.strip():
            context_chunks[slide.index] = slide.raw_text

        await emit("presentation_slide_generated", {
            "presentationId": presentation_id,
            "slideIndex": slide.index,
            "artifactId": artifact.id,
            "imageUrl": f"/artifacts/{artifact.id}",
            "slidesCompleted": slide.index + 1,
            "slidesTotal": len(extracted),
        })

    deck_title = extracted[0].title if extracted else filename.rsplit(".", 1)[0]
    content_json = {
        "title": deck_title,
        "slides": slide_data,
        "source": "pptx_upload",
        "filename": filename,
    }

    db_record = await prisma.generatedcontent.create(data={
        "user": {"connect": {"id": user_id}},
        "notebook": {"connect": {"id": notebook_id}},
        "contentType": "presentation",
        "title": deck_title,
        "data": json.dumps(content_json),
    })
    canonical_id = db_record.id

    await emit("presentation_slide_plan_ready", {
        "presentationId": canonical_id,
        "slidePlan": slide_data,
        "slideCount": len(slide_data),
        "message": f"Slides extracted from {filename}",
    })

    async def on_progress(stage: str, detail: dict):
        await emit("video_progress", {"presentationId": canonical_id, "stage": stage, **detail})

    result = await generate_explainer_video(
        slides=slide_data,
        image_paths=image_paths,
        output_dir=output_dir,
        voice_id=voice_id,
        narration_language=narration_language,
        narration_style=narration_style,
        narration_notes=narration_notes,
        presentation_title=deck_title,
        context_chunks=context_chunks,
        use_vision=True,
        on_progress=on_progress,
    )

    video_artifact = await prisma.artifact.create(data={
        "userId": user_id,
        "notebookId": None,
        "filename": "final_explainer.mp4",
        "mimeType": "video/mp4",
        "sizeBytes": os.path.getsize(result["video_path"]),
        "downloadToken": secrets.token_urlsafe(32),
        "tokenExpiry": datetime.now(timezone.utc) + timedelta(hours=settings.ARTIFACT_TOKEN_EXPIRY_HOURS),
        "workspacePath": result["video_path"],
    })

    transcription = result.get("transcription", {})
    video_data = {
        "videoUrl": f"/artifacts/{video_artifact.id}",
        "durationMs": result["duration_ms"],
        "scripts": result["scripts"],
        "transcriptText": transcription.get("text", ""),
        "transcriptSegments": transcription.get("segments", []),
        "subtitleTracks": [],
        "status": "completed",
    }
    content_json["video"] = video_data

    await prisma.generatedcontent.update(
        where={"id": canonical_id},
        data={"data": json.dumps(content_json)},
    )

    await emit("video_progress", {
        "presentationId": canonical_id,
        "stage": "done",
        "message": "Explainer video ready!",
        "videoUrl": f"/artifacts/{video_artifact.id}",
        "durationMs": result["duration_ms"],
    })
