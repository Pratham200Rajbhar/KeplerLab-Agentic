"""Code repair — self-healing code execution via LLM-based fix.

Takes broken code and stderr, asks the LLM to fix the specific error,
and returns the corrected code string.
"""

from __future__ import annotations

import logging
import re

from app.prompts import get_code_repair_prompt

logger = logging.getLogger(__name__)


def _extract_code(response_text: str) -> str:
    """Extract code from LLM response, stripping markdown fences if present."""
    text = response_text.strip()

    # Try to extract from ```python ... ``` or ``` ... ``` blocks
    pattern = r"```(?:python)?\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # If no fences, return as-is (LLM followed instructions)
    return text


async def repair_code(broken_code: str, stderr: str, llm) -> str:
    """Attempt to fix broken Python code using the LLM.

    Args:
        broken_code: The code that produced an error.
        stderr: The error output from execution.
        llm: An LLM instance with .ainvoke() method.

    Returns:
        The fixed code string.
    """
    repair_prompt = get_code_repair_prompt(broken_code, stderr)

    logger.info("[code_repair] Requesting fix for error: %s", stderr[:200])

    response = await llm.ainvoke(repair_prompt)
    raw = getattr(response, "content", None) or str(response)

    fixed_code = _extract_code(raw)

    logger.info(
        "[code_repair] Got fix (%d chars, original was %d chars)",
        len(fixed_code),
        len(broken_code),
    )

    return fixed_code
