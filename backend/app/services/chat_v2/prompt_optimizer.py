from __future__ import annotations

import logging
from typing import List

from app.prompts import get_prompt_optimizer_prompt
from app.services.llm_service.llm_schemas import OptimizedPromptsOutput
from app.services.llm_service.structured_invoker import async_invoke_structured

logger = logging.getLogger(__name__)

MAX_PROMPT_LENGTH = 5000


async def optimize_prompts(prompt: str, count: int = 4) -> List[dict]:
    if len(prompt) > MAX_PROMPT_LENGTH:
        prompt = prompt[:MAX_PROMPT_LENGTH]

    count = max(2, min(count, 6))

    llm_prompt = get_prompt_optimizer_prompt(prompt, count)
    result = await async_invoke_structured(llm_prompt, OptimizedPromptsOutput, max_retries=2)

    prompts = [p.model_dump() if hasattr(p, "model_dump") else p for p in result.prompts]
    prompts.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    return prompts[:count]
