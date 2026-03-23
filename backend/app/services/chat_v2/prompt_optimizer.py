from __future__ import annotations

import logging
from typing import List

from app.prompts import get_prompt_optimizer_prompt
from app.services.llm_service.llm import get_llm_structured
from app.services.llm_service.llm_schemas import OptimizedPromptsOutput
from app.services.llm_service.structured_invoker import parse_json_robust

logger = logging.getLogger(__name__)

MAX_PROMPT_LENGTH = 5000

def _clean(text: str) -> str:
    return " ".join((text or "").strip().split())


async def optimize_prompts(prompt: str, count: int = 4, context: str = "") -> List[dict]:
    user_prompt = _clean(prompt)
    if len(user_prompt) > MAX_PROMPT_LENGTH:
        user_prompt = user_prompt[:MAX_PROMPT_LENGTH]
    count = max(2, min(count, 6))

    llm = get_llm_structured()

    for attempt in range(3):
        strict_tail = ""
        if attempt > 0:
            strict_tail = (
                "\n\nCRITICAL:\n"
                "- Do not return empty arrays.\n"
                "- Return at least 2 optimized prompts.\n"
                "- Return ONLY JSON matching the exact schema."
            )

        llm_prompt = get_prompt_optimizer_prompt(user_prompt, count, context) + strict_tail
        raw = await llm.ainvoke(llm_prompt)
        text = getattr(raw, "content", str(raw)).strip()

        if not text:
            logger.warning("Prompt optimizer returned empty text on attempt %d", attempt + 1)
            continue

        data = parse_json_robust(text)
        if not isinstance(data, (dict, list)):
            logger.warning(
                "Prompt optimizer returned non-object JSON on attempt %d: %s",
                attempt + 1,
                type(data).__name__,
            )
            continue

        validated = OptimizedPromptsOutput.model_validate(data)
        prompts = [p.model_dump() if hasattr(p, "model_dump") else p for p in validated.prompts]
        prompts = [p for p in prompts if p.get("optimized_prompt")]

        if prompts:
            prompts.sort(key=lambda x: x.get("confidence", 0), reverse=True)
            logger.info("Prompt optimizer returned %d model prompts", len(prompts))
            return prompts[:count]

    raise ValueError("Prompt optimizer model output was empty after retries")
