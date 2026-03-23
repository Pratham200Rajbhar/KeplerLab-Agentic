from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.services.llm_service.llm import get_llm
from app.core.config import settings
from app.prompts import get_explainer_slide_prompt

logger = logging.getLogger("explainer.script")

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "gu": "Gujarati",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "ta": "Tamil",
    "te": "Telugu",
    "mr": "Marathi",
    "bn": "Bengali",
}

def _build_slide_prompt(
    slide_number: int,
    total_slides: int,
    title: str,
    content: str,
    narration_language: str,
) -> str:
    lang_name = LANGUAGE_NAMES.get(narration_language, narration_language)

    return get_explainer_slide_prompt(
        slide_number=slide_number,
        total_slides=total_slides,
        title=title,
        content=content,
        language=lang_name,
    )

def _generate_single_script(
    slide: dict,
    idx: int,
    total: int,
    narration_language: str,
) -> dict[str, str]:
    llm = get_llm(temperature=settings.LLM_TEMPERATURE_CREATIVE)
    
    title = slide.get("title", f"Slide {idx}")
    content = slide.get("content", "")
    if isinstance(content, list):
        content = "\n".join(f"• {item}" for item in content)

    prompt = _build_slide_prompt(idx, total, title, content, narration_language)
    
    try:
        response = llm.invoke(prompt)
        script_text = response.content.strip() if hasattr(response, "content") else str(response).strip()
    except Exception as exc:
        logger.error("Script generation failed for slide %d: %s", idx, exc)
        script_text = f"[Script generation failed for slide {idx}]"

    logger.info("Script for slide %d generated (%d chars)", idx, len(script_text))
    
    return {
        "slide_number": idx,
        "title": title,
        "script": script_text,
    }

async def generate_slide_scripts_async(
    slides: list[dict[str, Any]],
    narration_language: str,
    max_concurrent: int = 3,
) -> list[dict[str, str]]:
    total = len(slides)
    logger.info("Generating scripts for %d slides (parallel, max %d concurrent)", total, max_concurrent)

    loop = asyncio.get_running_loop()
    
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def generate_with_semaphore(slide: dict, idx: int) -> dict[str, str]:
        async with semaphore:
            return await loop.run_in_executor(
                None,
                _generate_single_script,
                slide, idx, total, narration_language,
            )
    
    tasks = [
        generate_with_semaphore(slide, idx)
        for idx, slide in enumerate(slides, start=1)
    ]
    
    results = await asyncio.gather(*tasks)
    
    return sorted(results, key=lambda x: x["slide_number"])
