from __future__ import annotations

import json
import logging

from app.db.prisma_client import prisma
from app.services.chat_v2.context_builder import build_messages
from app.services.llm_service.llm import get_llm_structured
from app.services.llm_service.structured_invoker import parse_json_robust
from app.services.presentation.html_renderer import render_presentation_html
from app.services.presentation.ppt_exporter import export_pptx
from app.services.presentation.schemas import PresentationPayload
from app.services.ws_manager import ws_manager

logger = logging.getLogger(__name__)


def _build_edit_prompt(old_json: dict, instruction: str, active_slide_index: int | None = None) -> str:
    active_slide_info = ""
    if active_slide_index is not None:
        active_slide_info = f"\nThe user is currently viewing/editing Slide {active_slide_index + 1}."

    return (
        "Update the presentation JSON based on user instruction and return strict JSON only. "
        "Keep the same top-level structure: {theme, slides}. "
        "Each slide includes layout, title, elements. "
        "Supported element types: title, subtitle, bullet, paragraph, table, image, numbered_list, quote, code, callout, divider.\n\n"
        f"Old JSON:\n{json.dumps(old_json, ensure_ascii=False)}\n"
        f"{active_slide_info}\n"
        f"Instruction:\n{instruction}"
    )


def _build_single_slide_edit_prompt(slide_json: dict, instruction: str) -> str:
    return (
        "You are an AI presentation editor. Update the provided single slide JSON based on the user instruction.\n"
        "Return strict JSON only. The structure must be a single slide object containing 'layout', 'title', and 'elements'.\n"
        "Supported element types: title, subtitle, bullet, paragraph, table, image, numbered_list, quote, code, callout, divider.\n\n"
        f"Original Slide JSON:\n{json.dumps(slide_json, ensure_ascii=False)}\n\n"
        f"Instruction:\n{instruction}"
    )


async def update_presentation_content(
    presentation_id: str, user_id: str, instruction: str, active_slide_index: int | None = None
) -> dict:
    
    await ws_manager.send_to_user(user_id, {
        "type": "presentation_update_progress",
        "message": "Initializing update..."
    })
    
    existing = await prisma.generatedcontent.find_first(
        where={
            "id": presentation_id,
            "userId": user_id,
            "contentType": "presentation",
        }
    )
    if not existing:
        raise ValueError("Presentation not found")

    old_json = existing.data if isinstance(existing.data, dict) else json.loads(existing.data or "{}")

    is_single_slide = active_slide_index is not None and 0 <= active_slide_index < len(old_json.get("slides", []))

    if is_single_slide:
        target_slide = old_json["slides"][active_slide_index]
        prompt = _build_single_slide_edit_prompt(target_slide, instruction)
    else:
        prompt = _build_edit_prompt(old_json, instruction, active_slide_index)

    messages = build_messages(
        user_message=prompt,
        history=[],
        system_prompt="You are an assistant that only returns valid JSON.",
    )

    await ws_manager.send_to_user(user_id, {
        "type": "presentation_update_progress",
        "message": f"Generating AI response (this should take {'about 10 seconds' if is_single_slide else 'up to 2 minutes'})..."
    })

    llm = get_llm_structured(mode="structured")
    response = llm.invoke(messages)
    
    await ws_manager.send_to_user(user_id, {
        "type": "presentation_update_progress",
        "message": "Parsing and validating structure..."
    })
    
    parsed = parse_json_robust(getattr(response, "content", str(response)))
    
    if is_single_slide:
        from app.services.presentation.schemas import Slide
        updated_slide = Slide.model_validate(parsed)
        old_json["slides"][active_slide_index] = updated_slide.model_dump()
        payload = PresentationPayload.model_validate(old_json)
    else:
        payload = PresentationPayload.model_validate(parsed)

    await ws_manager.send_to_user(user_id, {
        "type": "presentation_update_progress",
        "message": "Rendering updated presentation slides..."
    })

    html_path = render_presentation_html(str(existing.id), payload)
    ppt_path = export_pptx(str(existing.id), payload)

    updated = await prisma.generatedcontent.update(
        where={"id": str(existing.id)},
        data={
            "data": json.dumps(payload.model_dump()),
            "htmlPath": html_path,
            "pptPath": ppt_path,
        },
    )

    return {
        "id": str(updated.id),
        "notebook_id": str(updated.notebookId),
        "user_id": str(updated.userId),
        "content_type": updated.contentType,
        "title": updated.title,
        "data": updated.data if isinstance(updated.data, dict) else json.loads(updated.data or "{}"),
        "html_path": updated.htmlPath,
        "ppt_path": updated.pptPath,
        "material_ids": updated.materialIds or [],
        "created_at": updated.createdAt.isoformat() if updated.createdAt else None,
    }
