"""
Presentation Service — orchestrator that ties together slide planning, image generation,
video creation, and WebSocket event streaming.

This is the main entry point called by the API route.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.db.prisma_client import prisma
from app.services.llm_service.llm import get_llm
from app.services.podcast.voice_map import VOICE_MAP, get_voices_for_language
from app.services.ws_manager import ws_manager

from app.services.presentation.slide_planner import generate_slide_plan, ThemeSpec
from app.services.presentation.prompt_builder import build_all_prompts, build_slide_prompt
from app.services.presentation.image_generator import generate_all_slides, generate_slide_image
from app.services.presentation.video_generator import generate_explainer_video

logger = logging.getLogger(__name__)

_OUTPUT_BASE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "output", "presentations")
)


def _ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


async def _emit(user_id: str, event_type: str, data: Dict[str, Any]) -> None:
    """Send a WebSocket event to the user."""
    payload = {"type": event_type, **data}
    try:
        await ws_manager.send_to_user(user_id, payload)
    except Exception as exc:
        logger.debug("WS emit failed for %s: %s", event_type, exc)


async def _save_artifact(
    user_id: str,
    notebook_id: Optional[str],
    filename: str,
    file_bytes: bytes,
    mime_type: str,
    output_dir: str,
) -> str:
    """Save file bytes as an Artifact record and return the artifact ID."""
    _ensure_dir(output_dir)
    file_path = os.path.join(output_dir, filename)

    with open(file_path, "wb") as f:
        f.write(file_bytes)

    artifact = await prisma.artifact.create(
        data={
            "userId": user_id,
            "notebookId": notebook_id,
            "filename": filename,
            "mimeType": mime_type,
            "sizeBytes": len(file_bytes),
            "downloadToken": secrets.token_urlsafe(32),
            "tokenExpiry": datetime.now(timezone.utc) + timedelta(hours=settings.ARTIFACT_TOKEN_EXPIRY_HOURS),
            "workspacePath": file_path,
        }
    )

    logger.info("Artifact saved: %s (%s, %d bytes)", artifact.id, filename, len(file_bytes))
    return artifact.id


async def _save_artifact_from_file(
    user_id: str,
    notebook_id: Optional[str],
    file_path: str,
    mime_type: str,
    output_dir: str,
    filename: Optional[str] = None,
) -> str:
    """Save an existing file as an artifact record and return artifact ID."""
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    return await _save_artifact(
        user_id=user_id,
        notebook_id=notebook_id,
        filename=filename or os.path.basename(file_path),
        file_bytes=file_bytes,
        mime_type=mime_type,
        output_dir=output_dir,
    )


def _parse_content_data(raw_data: Any) -> Dict[str, Any]:
    if isinstance(raw_data, str):
        try:
            parsed = json.loads(raw_data)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    if isinstance(raw_data, dict):
        return raw_data
    return {}


def _parse_json_value(raw_data: Any) -> Any:
    if isinstance(raw_data, str):
        try:
            return json.loads(raw_data)
        except json.JSONDecodeError:
            return raw_data
    return raw_data


def _normalize_slide_spec(slide: Dict[str, Any], index: int) -> Dict[str, Any]:
    title = str(slide.get("title") or f"Slide {index + 1}").strip() or f"Slide {index + 1}"
    raw_bullets = slide.get("bullets", [])
    if isinstance(raw_bullets, str):
        raw_bullets = [b.strip() for b in raw_bullets.split("\n") if b.strip()]
    elif not isinstance(raw_bullets, list):
        raw_bullets = [str(raw_bullets)] if raw_bullets else []
    bullets = [str(b).strip() for b in raw_bullets if str(b).strip()][:5]

    visual_style = str(slide.get("visual_style") or slide.get("visualStyle") or "modern").strip().lower()
    if visual_style not in {"minimal", "modern", "diagram", "chart", "timeline"}:
        visual_style = "modern"

    tone = str(slide.get("tone") or "educational").strip().lower()
    argument_role = str(
        slide.get("argument_role")
        or slide.get("argumentRole")
        or "support"
    ).strip().lower()
    if argument_role not in {"thesis", "context", "evidence", "counterpoint", "synthesis", "summary", "support"}:
        argument_role = "support"

    return {
        "title": title,
        "bullets": bullets if bullets else ["Key point"],
        "visual_style": visual_style,
        "tone": tone,
        "argument_role": argument_role,
    }


def _clean_title_candidate(raw: Any, *, max_len: int = 110) -> str:
    text = str(raw or "").strip()
    if not text:
        return ""

    text = text.splitlines()[0].strip()
    text = re.sub(r"^(title|presentation title|video title)\s*:\s*", "", text, flags=re.IGNORECASE)
    text = text.strip().strip('"\'`')
    text = re.sub(r"\s+", " ", text)

    return text[:max_len].strip()


def _fallback_title_from_slides(slides: List[Dict[str, Any]]) -> str:
    for slide in slides:
        title = _clean_title_candidate(slide.get("title") if isinstance(slide, dict) else "")
        if title:
            return title
    return "Untitled"


async def _generate_ai_presentation_title(
    *,
    topic: Optional[str],
    slide_plan: List[Dict[str, Any]],
) -> str:
    fallback = _fallback_title_from_slides(slide_plan)

    slide_titles = [
        _clean_title_candidate(slide.get("title") if isinstance(slide, dict) else "")
        for slide in slide_plan[:6]
    ]
    slide_titles = [title for title in slide_titles if title]

    prompt = (
        "Generate one concise presentation title based on the source-derived slide plan.\n"
        "Rules:\n"
        "- 3 to 9 words\n"
        "- Specific and descriptive\n"
        "- No prefixes like Title:, Presentation:, or Topic:\n"
        "- Return only the title text\n\n"
        f"Focus hint: {topic or 'none'}\n"
        f"Slide titles: {json.dumps(slide_titles, ensure_ascii=True)}\n"
    )

    try:
        llm = get_llm(mode="structured", max_tokens=64)
        response = await asyncio.to_thread(llm.invoke, prompt)
        generated = _clean_title_candidate(getattr(response, "content", None) or str(response))
        return generated or fallback
    except Exception as exc:
        logger.warning("AI presentation title generation failed: %s", exc)
        return fallback


async def _generate_ai_explainer_title(
    *,
    presentation_title: Optional[str],
    slides: List[Dict[str, Any]],
    scripts: List[str],
) -> str:
    fallback = _clean_title_candidate(presentation_title) or _fallback_title_from_slides(slides)

    slide_titles = [
        _clean_title_candidate(slide.get("title") if isinstance(slide, dict) else "")
        for slide in slides[:5]
    ]
    slide_titles = [title for title in slide_titles if title]

    script_preview = [str(s).strip() for s in scripts[:2] if str(s).strip()]

    prompt = (
        "Generate one concise title for an educational explainer video.\n"
        "Rules:\n"
        "- 3 to 9 words\n"
        "- Reflect the actual lesson topic\n"
        "- No prefixes like Title:, Video:, Explain Video:\n"
        "- Return only the title text\n\n"
        f"Presentation title: {fallback}\n"
        f"Slide titles: {json.dumps(slide_titles, ensure_ascii=True)}\n"
        f"Narration preview: {json.dumps(script_preview, ensure_ascii=True)}\n"
    )

    try:
        llm = get_llm(mode="structured", max_tokens=64)
        response = await asyncio.to_thread(llm.invoke, prompt)
        generated = _clean_title_candidate(getattr(response, "content", None) or str(response))
        return generated or fallback
    except Exception as exc:
        logger.warning("AI explainer title generation failed: %s", exc)
        return fallback


async def _render_slides_from_plan(
    *,
    user_id: str,
    presentation_id: str,
    notebook_id: Optional[str],
    slide_plan: List[Dict[str, Any]],
    output_dir: str,
    theme_spec: Optional[Dict[str, Any]] = None,
    # Legacy compat — ignored when theme_spec is provided
    theme_prompt: Optional[str] = None,
    argumentation_notes: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    prompts = build_all_prompts(
        slide_plan,
        theme_spec=theme_spec,
    )

    await _emit(user_id, "presentation_status", {
        "presentationId": presentation_id,
        "phase": "generating",
        "message": f"Generating {len(prompts)} slides...",
        "slidesTotal": len(prompts),
        "slidesCompleted": 0,
    })
    await _emit(user_id, "slide_generation_started", {
        "presentationId": presentation_id,
        "slidesTotal": len(prompts),
    })

    slides_completed = 0
    artifact_ids: List[Optional[str]] = [None] * len(prompts)

    async def on_slide_ready(idx: int, image_bytes: bytes) -> None:
        nonlocal slides_completed

        filename = f"slide_{idx:03d}.png"
        artifact_id = await _save_artifact(
            user_id=user_id,
            notebook_id=notebook_id,
            filename=filename,
            file_bytes=image_bytes,
            mime_type="image/png",
            output_dir=output_dir,
        )
        artifact_ids[idx] = artifact_id
        slides_completed += 1

        payload = {
            "presentationId": presentation_id,
            "slideIndex": idx,
            "artifactId": artifact_id,
            "imageUrl": f"/artifacts/{artifact_id}",
            "slidesCompleted": slides_completed,
            "slidesTotal": len(prompts),
        }
        await _emit(user_id, "presentation_slide_generated", payload)
        await _emit(user_id, "slide_generated", payload)

    async def on_slide_failed(idx: int, exc: Exception) -> None:
        nonlocal slides_completed
        slides_completed += 1

        failure_payload = {
            "presentationId": presentation_id,
            "slideIndex": idx,
            "error": str(exc),
            "slidesCompleted": slides_completed,
            "slidesTotal": len(prompts),
        }
        await _emit(user_id, "presentation_slide_failed", failure_payload)
        await _emit(user_id, "slide_generated", {
            **failure_payload,
            "status": "failed",
        })

    await generate_all_slides(
        prompts,
        on_slide_ready=on_slide_ready,
        on_slide_failed=on_slide_failed,
    )

    slides_data: List[Dict[str, Any]] = []
    for i, slide_spec in enumerate(slide_plan):
        slides_data.append({
            "index": i,
            "title": slide_spec["title"],
            "bullets": slide_spec["bullets"],
            "visual_style": slide_spec["visual_style"],
            "tone": slide_spec.get("tone", "educational"),
            "argument_role": slide_spec.get("argument_role", "support"),
            "artifactId": artifact_ids[i],
            "imageUrl": f"/artifacts/{artifact_ids[i]}" if artifact_ids[i] else None,
            "status": "completed" if artifact_ids[i] else "failed",
        })

    success_count = sum(1 for a in artifact_ids if a is not None)
    return slides_data, success_count


async def _extract_valid_slide_assets(
    slides: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    valid_slides: List[Dict[str, Any]] = []
    image_paths: List[str] = []

    for slide in slides:
        artifact_id = slide.get("artifactId")
        if not artifact_id:
            continue
        artifact = await prisma.artifact.find_unique(where={"id": artifact_id})
        if artifact and artifact.workspacePath and os.path.isfile(artifact.workspacePath):
            valid_slides.append(slide)
            image_paths.append(artifact.workspacePath)

    return valid_slides, image_paths


async def _upsert_generated_content(
    *,
    presentation_id: str,
    notebook_id: str,
    user_id: str,
    generated_title: Optional[str],
    material_ids: List[str],
    presentation_data: Dict[str, Any],
):
    existing = await prisma.generatedcontent.find_unique(where={"id": presentation_id})
    fallback_title = _fallback_title_from_slides(
        presentation_data.get("slides") if isinstance(presentation_data.get("slides"), list) else []
    )
    resolved_title = _clean_title_candidate(generated_title) or fallback_title

    if existing:
        content = await prisma.generatedcontent.update(
            where={"id": presentation_id},
            data={
                "title": resolved_title or existing.title,
                "data": json.dumps(presentation_data),
                "materialIds": material_ids,
            },
        )
    else:
        content = await prisma.generatedcontent.create(
            data={
                "id": presentation_id,
                "notebookId": notebook_id,
                "userId": user_id,
                "contentType": "presentation",
                "title": resolved_title,
                "data": json.dumps(presentation_data),
                "materialIds": material_ids,
            }
        )

    for material_id in material_ids:
        try:
            await prisma.generatedcontentmaterial.create(
                data={
                    "generatedContentId": presentation_id,
                    "materialId": material_id,
                }
            )
        except Exception:
            pass

    return content


async def _ensure_presentation_has_slide_images(
    *,
    user_id: str,
    content: Any,
    presentation_id: str,
    data: Dict[str, Any],
    auto_generate_slides: bool,
    fallback_notebook_id: Optional[str],
    fallback_material_ids: Optional[List[str]],
    fallback_topic: Optional[str],
    fallback_theme_prompt: Optional[str],
    fallback_target_slide_count: Optional[int],
    fallback_argumentation_notes: Optional[str],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[str]]:
    slides = data.get("slides", [])
    generated_title: Optional[str] = None
    valid_slides, image_paths = await _extract_valid_slide_assets(slides)
    if valid_slides:
        return data, valid_slides, image_paths

    if not auto_generate_slides:
        raise ValueError("No valid slide images found for video generation")

    await _emit(user_id, "presentation_status", {
        "presentationId": presentation_id,
        "phase": "planning",
        "message": "Preparing slides for explainer video...",
    })

    if slides:
        slide_plan = [_normalize_slide_spec(slide, i) for i, slide in enumerate(slides)]
        await _emit(user_id, "presentation_slide_plan_ready", {
            "presentationId": presentation_id,
            "slides": slide_plan,
            "slideCount": len(slide_plan),
        })
        await _emit(user_id, "slide_plan_ready", {
            "presentationId": presentation_id,
            "slides": slide_plan,
            "slideCount": len(slide_plan),
        })
    else:
        material_ids = [m for m in (fallback_material_ids or content.materialIds or []) if m]
        if not material_ids:
            raise ValueError(
                "No slides found and no materials available to auto-generate slides for video"
            )

        notebook_id = fallback_notebook_id or content.notebookId
        topic = fallback_topic or data.get("topic")
        theme_prompt = fallback_theme_prompt or data.get("themePrompt")
        target_slide_count = fallback_target_slide_count or data.get("targetSlideCount")
        argumentation_notes = fallback_argumentation_notes or data.get("argumentationNotes")
        slide_plan = await generate_slide_plan(
            user_id=user_id,
            material_ids=material_ids,
            notebook_id=notebook_id,
            topic=topic,
            theme=theme_prompt,
            target_slide_count=target_slide_count,
            argumentation_notes=argumentation_notes,
        )

        generated_title = await _generate_ai_presentation_title(
            topic=topic,
            slide_plan=slide_plan,
        )

        await _emit(user_id, "presentation_slide_plan_ready", {
            "presentationId": presentation_id,
            "slides": slide_plan,
            "slideCount": len(slide_plan),
        })
        await _emit(user_id, "slide_plan_ready", {
            "presentationId": presentation_id,
            "slides": slide_plan,
            "slideCount": len(slide_plan),
        })

    output_dir = _ensure_dir(os.path.join(_OUTPUT_BASE, presentation_id))
    slides_data, success_count = await _render_slides_from_plan(
        user_id=user_id,
        presentation_id=presentation_id,
        notebook_id=fallback_notebook_id or content.notebookId,
        slide_plan=slide_plan,
        output_dir=output_dir,
        theme_prompt=fallback_theme_prompt or data.get("themePrompt"),
        argumentation_notes=fallback_argumentation_notes or data.get("argumentationNotes"),
    )

    topic = fallback_topic or data.get("topic")
    theme_prompt = fallback_theme_prompt or data.get("themePrompt")
    target_slide_count = fallback_target_slide_count or data.get("targetSlideCount")
    argumentation_notes = fallback_argumentation_notes or data.get("argumentationNotes")
    updated_data = {
        **data,
        "slides": slides_data,
        "slideCount": len(slides_data),
        "successCount": success_count,
        "title": generated_title or data.get("title") or content.title,
        "topic": topic,
        "themePrompt": theme_prompt,
        "targetSlideCount": target_slide_count,
        "argumentationNotes": argumentation_notes,
        "status": "completed" if success_count > 0 else "failed",
    }

    await prisma.generatedcontent.update(
        where={"id": presentation_id},
        data={
            "data": json.dumps(updated_data),
            "title": generated_title or content.title,
        },
    )

    await _emit(user_id, "presentation_done", {
        "presentationId": presentation_id,
        "slides": slides_data,
        "slideCount": len(slides_data),
        "successCount": success_count,
        "autoGenerated": True,
    })

    valid_slides, image_paths = await _extract_valid_slide_assets(slides_data)
    if not valid_slides:
        raise ValueError("Slides were generated but no valid slide images are available")

    return updated_data, valid_slides, image_paths


# ── Presentation generation ────────────────────────────────────────────────

async def generate_presentation(
    user_id: str,
    notebook_id: str,
    material_ids: List[str],
    topic: Optional[str] = None,
    theme_prompt: Optional[str] = None,
    target_slide_count: Optional[int] = None,
    argumentation_notes: Optional[str] = None,
    presentation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Full presentation generation pipeline.

    1. Plan slides via RAG + LLM
    2. Build image prompts
    3. Generate slide images in parallel
    4. Save as artifacts
    5. Store as GeneratedContent

    Returns the GeneratedContent record data.
    """
    presentation_id = presentation_id or str(uuid.uuid4())
    output_dir = _ensure_dir(os.path.join(_OUTPUT_BASE, presentation_id))

    try:
        # Step 1: Plan + generate theme concurrently
        await _emit(user_id, "presentation_status", {
            "presentationId": presentation_id,
            "phase": "planning",
            "message": "Planning slides and generating color theme...",
        })

        # generate_slide_plan now returns (slide_plan, theme_spec) — runs theme gen in parallel
        slide_plan, theme_spec = await generate_slide_plan(
            user_id=user_id,
            material_ids=material_ids,
            notebook_id=notebook_id,
            topic=topic,
            theme=theme_prompt,
            target_slide_count=target_slide_count,
            argumentation_notes=argumentation_notes,
        )

        generated_title = await _generate_ai_presentation_title(
            topic=topic,
            slide_plan=slide_plan,
        )

        await _emit(user_id, "presentation_slide_plan_ready", {
            "presentationId": presentation_id,
            "slides": slide_plan,
            "slideCount": len(slide_plan),
            "themeSpec": dict(theme_spec),
        })
        await _emit(user_id, "slide_plan_ready", {
            "presentationId": presentation_id,
            "slides": slide_plan,
            "slideCount": len(slide_plan),
            "themeSpec": dict(theme_spec),
        })

        slides_data, success_count = await _render_slides_from_plan(
            user_id=user_id,
            presentation_id=presentation_id,
            notebook_id=notebook_id,
            slide_plan=slide_plan,
            output_dir=output_dir,
            theme_spec=dict(theme_spec),
            argumentation_notes=argumentation_notes,
        )

        presentation_data = {
            "slides": slides_data,
            "slideCount": len(slides_data),
            "successCount": success_count,
            "title": generated_title,
            "topic": topic,
            "themePrompt": theme_prompt,
            "themeSpec": dict(theme_spec),
            "targetSlideCount": target_slide_count,
            "argumentationNotes": argumentation_notes,
            "status": "completed" if success_count > 0 else "failed",
        }

        content = await _upsert_generated_content(
            presentation_id=presentation_id,
            notebook_id=notebook_id,
            user_id=user_id,
            generated_title=generated_title,
            material_ids=material_ids,
            presentation_data=presentation_data,
        )

        await _emit(user_id, "presentation_done", {
            "presentationId": presentation_id,
            "slides": slides_data,
            "slideCount": len(slides_data),
            "successCount": success_count,
            "themeSpec": dict(theme_spec),
        })

        logger.info(
            "Presentation generated: id=%s slides=%d/%d user=%s",
            presentation_id, success_count, len(slide_plan), user_id,
        )

        return {
            "id": presentation_id,
            "content_type": "presentation",
            "title": content.title,
            "data": presentation_data,
            "created_at": content.createdAt.isoformat() if content.createdAt else None,
        }

    except Exception as exc:
        logger.exception("Presentation generation failed for user %s: %s", user_id, exc)

        await _emit(user_id, "presentation_error", {
            "presentationId": presentation_id,
            "error": str(exc),
        })

        raise


# ── Single slide regeneration ──────────────────────────────────────────────

async def regenerate_slide(
    user_id: str,
    presentation_id: str,
    slide_index: int,
) -> Dict[str, Any]:
    """Regenerate a single slide in an existing presentation."""
    content = await prisma.generatedcontent.find_unique(
        where={"id": presentation_id}
    )
    if not content or content.userId != user_id:
        raise ValueError("Presentation not found")

    data = _parse_content_data(content.data)
    slides = data.get("slides", [])

    if slide_index < 0 or slide_index >= len(slides):
        raise ValueError(f"Invalid slide index: {slide_index}")

    slide_spec = _normalize_slide_spec(slides[slide_index], slide_index)
    # Reuse the stored ThemeSpec so the regenerated slide matches the deck palette
    stored_theme = data.get("themeSpec")
    theme_spec = stored_theme if isinstance(stored_theme, dict) and stored_theme else None
    prompt = build_slide_prompt(slide_spec, slide_index, len(slides), theme_spec=theme_spec)

    output_dir = _ensure_dir(os.path.join(_OUTPUT_BASE, presentation_id))
    image_bytes = await generate_slide_image(prompt)

    filename = f"slide_{slide_index:03d}_regen.png"
    aid = await _save_artifact(
        user_id=user_id,
        notebook_id=content.notebookId,
        filename=filename,
        file_bytes=image_bytes,
        mime_type="image/png",
        output_dir=output_dir,
    )

    # Update the slide data
    slides[slide_index]["artifactId"] = aid
    slides[slide_index]["imageUrl"] = f"/artifacts/{aid}"
    slides[slide_index]["status"] = "completed"
    data["slides"] = slides

    await prisma.generatedcontent.update(
        where={"id": presentation_id},
        data={"data": json.dumps(data)},
    )

    await _emit(user_id, "presentation_slide_generated", {
        "presentationId": presentation_id,
        "slideIndex": slide_index,
        "artifactId": aid,
        "imageUrl": f"/artifacts/{aid}",
        "regenerated": True,
    })
    await _emit(user_id, "slide_generated", {
        "presentationId": presentation_id,
        "slideIndex": slide_index,
        "artifactId": aid,
        "imageUrl": f"/artifacts/{aid}",
        "regenerated": True,
    })

    return {
        "slideIndex": slide_index,
        "artifactId": aid,
        "imageUrl": f"/artifacts/{aid}",
    }


# ── Explainer video generation ─────────────────────────────────────────────

async def generate_video(
    user_id: str,
    presentation_id: str,
    voice_id: str,
    narration_language: str = "en",
    ppt_language: str = "en",
    narration_style: Optional[str] = None,
    narration_notes: Optional[str] = None,
    auto_generate_slides: bool = True,
    fallback_notebook_id: Optional[str] = None,
    fallback_material_ids: Optional[List[str]] = None,
    fallback_topic: Optional[str] = None,
    fallback_theme_prompt: Optional[str] = None,
    fallback_target_slide_count: Optional[int] = None,
    fallback_argumentation_notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate an explainer video for an existing presentation.

    1. Load presentation data (slides + images)
    2. Generate narration scripts
    3. Generate TTS audio
    4. Create individual slide videos
    5. Merge into final video
    6. Transcribe with Whisper + create subtitle files
    7. Save artifacts + ExplainerVideo record
    """
    content = await prisma.generatedcontent.find_unique(
        where={"id": presentation_id}
    )
    if not content or content.userId != user_id:
        raise ValueError("Presentation not found")

    data = _parse_content_data(content.data)

    data, valid_slides, image_paths = await _ensure_presentation_has_slide_images(
        user_id=user_id,
        content=content,
        presentation_id=presentation_id,
        data=data,
        auto_generate_slides=auto_generate_slides,
        fallback_notebook_id=fallback_notebook_id,
        fallback_material_ids=fallback_material_ids,
        fallback_topic=fallback_topic,
        fallback_theme_prompt=fallback_theme_prompt,
        fallback_target_slide_count=fallback_target_slide_count,
        fallback_argumentation_notes=fallback_argumentation_notes,
    )

    output_dir = _ensure_dir(os.path.join(_OUTPUT_BASE, presentation_id, "video"))

    voice_gender = "unknown"
    candidate_lists = [get_voices_for_language(narration_language)] + list(VOICE_MAP.values())
    for voice_list in candidate_lists:
        for voice in voice_list:
            vid = str(voice.get("id") or voice.get("voice_id") or voice.get("voiceId") or "")
            if vid == voice_id:
                voice_gender = str(voice.get("gender") or "unknown").lower()
                break
        if voice_gender != "unknown":
            break

    # Create ExplainerVideo record
    video_record = await prisma.explainervideo.create(
        data={
            "userId": user_id,
            "presentationId": presentation_id,
            "pptLanguage": ppt_language,
            "narrationLanguage": narration_language,
            "voiceGender": voice_gender,
            "voiceId": voice_id,
            "status": "generating_script",
        }
    )

    try:
        async def on_progress(stage: str, detail: Dict) -> None:
            status_map = {
                "scripting": "generating_script",
                "script_done": "generating_audio",
                "audio": "generating_audio",
                "audio_done": "composing_video",
                "rendering": "composing_video",
                "merging": "composing_video",
                "transcribing": "composing_video",
                "done": "completed",
            }

            db_status = status_map.get(stage, "processing")
            try:
                await prisma.explainervideo.update(
                    where={"id": video_record.id},
                    data={"status": db_status},
                )
            except Exception:
                pass

            await _emit(user_id, f"video_{stage}", {
                "videoId": video_record.id,
                "presentationId": presentation_id,
                **detail,
            })

            alias_event_map = {
                "script_done": "script_generated",
                "audio_done": "audio_generated",
                "rendering": "video_rendering",
                "merging": "video_rendering",
            }
            alias_event = alias_event_map.get(stage)
            if alias_event:
                await _emit(user_id, alias_event, {
                    "videoId": video_record.id,
                    "presentationId": presentation_id,
                    **detail,
                })

        result = await generate_explainer_video(
            slides=valid_slides,
            image_paths=image_paths,
            output_dir=output_dir,
            voice_id=voice_id,
            narration_language=narration_language,
            narration_style=narration_style,
            narration_notes=narration_notes,
            on_progress=on_progress,
        )

        explainer_title = await _generate_ai_explainer_title(
            presentation_title=content.title,
            slides=valid_slides,
            scripts=result.get("scripts", []) if isinstance(result.get("scripts"), list) else [],
        )

        # Save final video as artifact
        video_path = result["video_path"]
        with open(video_path, "rb") as f:
            video_bytes = f.read()

        video_artifact_id = await _save_artifact(
            user_id=user_id,
            notebook_id=content.notebookId,
            filename="explainer_video.mp4",
            file_bytes=video_bytes,
            mime_type="video/mp4",
            output_dir=output_dir,
        )

        transcription = result.get("transcription") if isinstance(result.get("transcription"), dict) else {}
        transcript_segments = (
            transcription.get("segments")
            if isinstance(transcription.get("segments"), list)
            else []
        )
        transcript_text = str(transcription.get("text") or "").strip()
        transcript_language = str(transcription.get("language") or "unknown")
        transcript_status = str(transcription.get("status") or "failed")
        transcript_error = (
            str(transcription.get("error") or "").strip() or None
            if transcript_status != "success"
            else None
        )

        subtitle_tracks: List[Dict[str, str]] = []
        subtitle_files = (
            transcription.get("subtitle_files")
            if isinstance(transcription.get("subtitle_files"), list)
            else []
        )
        for sub in subtitle_files:
            if not isinstance(sub, dict):
                continue
            sub_path = sub.get("path")
            fmt = str(sub.get("format") or "").lower()
            if not sub_path or not os.path.isfile(sub_path):
                continue

            mime_type = "text/vtt" if fmt == "vtt" else "application/x-subrip" if fmt == "srt" else "text/plain"
            filename = f"explainer_subtitles.{fmt}" if fmt in {"vtt", "srt"} else os.path.basename(sub_path)

            subtitle_artifact_id = await _save_artifact_from_file(
                user_id=user_id,
                notebook_id=content.notebookId,
                file_path=sub_path,
                mime_type=mime_type,
                output_dir=output_dir,
                filename=filename,
            )

            subtitle_tracks.append({
                "format": fmt or "txt",
                "artifactId": subtitle_artifact_id,
                "url": f"/artifacts/{subtitle_artifact_id}",
            })

        chapters_payload = {
            "transcriptStatus": transcript_status,
            "transcriptError": transcript_error,
            "transcriptLanguage": transcript_language,
            "transcriptText": transcript_text,
            "transcriptSegments": transcript_segments,
            "subtitleTracks": subtitle_tracks,
        }

        # Update ExplainerVideo record
        await prisma.explainervideo.update(
            where={"id": video_record.id},
            data={
                "status": "completed",
                "videoUrl": f"/artifacts/{video_artifact_id}",
                "duration": result.get("duration_ms", 0),
                "script": json.dumps(result.get("scripts", [])),
                "audioFiles": json.dumps(result.get("audio_files", [])),
                "chapters": json.dumps(chapters_payload),
                "completedAt": datetime.now(timezone.utc),
            },
        )

        data["video"] = {
            "id": video_record.id,
            "title": explainer_title,
            "status": "completed",
            "voiceId": voice_id,
            "narrationLanguage": narration_language,
            "pptLanguage": ppt_language,
            "narrationStyle": narration_style,
            "narrationNotes": narration_notes,
            "videoUrl": f"/artifacts/{video_artifact_id}",
            "duration": result.get("duration_ms", 0),
            "transcriptStatus": transcript_status,
            "transcriptError": transcript_error,
            "transcriptLanguage": transcript_language,
            "transcriptText": transcript_text,
            "transcriptSegments": transcript_segments,
            "subtitleTracks": subtitle_tracks,
        }
        await prisma.generatedcontent.update(
            where={"id": presentation_id},
            data={"data": json.dumps(data)},
        )

        await _emit(user_id, "video_done", {
            "videoId": video_record.id,
            "presentationId": presentation_id,
            "videoUrl": f"/artifacts/{video_artifact_id}",
            "artifactId": video_artifact_id,
            "durationMs": result.get("duration_ms", 0),
            "transcriptSegments": len(transcript_segments),
        })

        logger.info(
            "Explainer video generated: video=%s presentation=%s duration=%dms",
            video_record.id, presentation_id, result.get("duration_ms", 0),
        )

        return {
            "videoId": video_record.id,
            "title": explainer_title,
            "voiceId": voice_id,
            "narrationLanguage": narration_language,
            "pptLanguage": ppt_language,
            "narrationStyle": narration_style,
            "narrationNotes": narration_notes,
            "videoUrl": f"/artifacts/{video_artifact_id}",
            "artifactId": video_artifact_id,
            "durationMs": result.get("duration_ms", 0),
            "transcriptStatus": transcript_status,
            "transcriptLanguage": transcript_language,
            "transcriptText": transcript_text,
            "transcriptSegments": transcript_segments,
            "subtitleTracks": subtitle_tracks,
        }

    except Exception as exc:
        logger.exception("Video generation failed: %s", exc)

        await prisma.explainervideo.update(
            where={"id": video_record.id},
            data={"status": "failed", "error": str(exc)},
        )

        data["video"] = {
            "id": video_record.id,
            "status": "failed",
            "error": str(exc),
        }
        try:
            await prisma.generatedcontent.update(
                where={"id": presentation_id},
                data={"data": json.dumps(data)},
            )
        except Exception:
            pass

        await _emit(user_id, "video_error", {
            "videoId": video_record.id,
            "presentationId": presentation_id,
            "error": str(exc),
        })

        raise


# ── Read helpers ───────────────────────────────────────────────────────────

async def get_presentation(
    presentation_id: str,
    user_id: str,
) -> Optional[Dict[str, Any]]:
    """Load a presentation by ID, verifying ownership."""
    content = await prisma.generatedcontent.find_unique(
        where={"id": presentation_id}
    )
    if not content or content.userId != user_id:
        return None

    data = _parse_content_data(content.data)

    # Check for associated video
    video = await prisma.explainervideo.find_first(
        where={"presentationId": presentation_id, "userId": user_id},
        order={"createdAt": "desc"},
    )

    persisted_video = data.get("video") if isinstance(data.get("video"), dict) else None
    resolved_video = dict(persisted_video) if isinstance(persisted_video, dict) else {}

    if video:
        resolved_video.update({
            "id": video.id,
            "status": video.status,
            "videoUrl": video.videoUrl,
            "duration": video.duration,
            "error": video.error,
        })

        parsed_script = _parse_json_value(video.script)
        parsed_audio_files = _parse_json_value(video.audioFiles)
        parsed_chapters = _parse_json_value(video.chapters)

        if isinstance(parsed_script, list):
            resolved_video["scripts"] = parsed_script
        if isinstance(parsed_audio_files, list):
            resolved_video["audioFiles"] = parsed_audio_files

        if isinstance(parsed_chapters, dict):
            for key in (
                "transcriptStatus",
                "transcriptError",
                "transcriptLanguage",
                "transcriptText",
                "transcriptSegments",
                "subtitleTracks",
            ):
                if key in parsed_chapters:
                    resolved_video[key] = parsed_chapters.get(key)

            if "transcriptSegments" not in resolved_video or not isinstance(resolved_video.get("transcriptSegments"), list):
                resolved_video["transcriptSegments"] = []
            if "subtitleTracks" not in resolved_video or not isinstance(resolved_video.get("subtitleTracks"), list):
                resolved_video["subtitleTracks"] = []

    if not resolved_video:
        resolved_video = None

    return {
        "id": content.id,
        "title": content.title,
        "contentType": content.contentType,
        "data": data,
        "createdAt": content.createdAt.isoformat() if content.createdAt else None,
        "video": resolved_video,
    }
