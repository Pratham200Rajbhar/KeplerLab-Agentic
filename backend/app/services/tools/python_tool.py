"""Code generation tool — generates code via LLM for review before execution.

Detects the requested language from the user query and generates code in that
language.  Phase 2 execution is handled by the /agent/execute-code endpoint.
"""

from __future__ import annotations

import logging
import re
from typing import AsyncIterator, List, Optional

from app.core.config import settings
from app.services.chat_v2.schemas import ToolResult
from app.services.chat_v2.streaming import sse_tool_start, sse_tool_result, sse_code_block

logger = logging.getLogger(__name__)

# ── Language detection ────────────────────────────────────────

_LANG_PATTERNS: List[tuple[str, str]] = [
    # (pattern, canonical_language)
    (r"\b(javascript|js|node\.?js?)\b", "javascript"),
    (r"\b(typescript|ts)\b", "typescript"),
    (r"\b(c\+\+|cpp)\b", "cpp"),
    (r"\bjava\b(?!\s*script)", "java"),   # java but not javascript
    (r"\b(golang|go)\b", "go"),
    (r"\brust\b", "rust"),
    (r"\b(bash|shell|sh)\b", "bash"),
    (r"\bpython\b", "python"),
    # C must be last to avoid false positives inside other words
    (r"\bin c\b|\bwrite c\b|\busing c\b", "c"),
]

def _detect_language(query: str) -> str:
    """Return the language requested in *query*, defaulting to 'python'."""
    q = query.lower()
    for pattern, lang in _LANG_PATTERNS:
        if re.search(pattern, q):
            return lang
    return "python"


async def execute(
    query: str,
    material_ids: List[str],
    user_id: str,
    notebook_id: str,
    session_id: str,
) -> AsyncIterator[str | ToolResult]:
    """Generate code for the user's request in the appropriate language.

    Detects the language from the query.  If the user says "write fibonacci in
    javascript" the generated code will be JavaScript, not Python.

    Yields:
        SSE events (tool_start, code_block, tool_result) for streaming.
        Final yield is always a ToolResult.
    """
    language = _detect_language(query)
    yield sse_tool_start("python", label=f"Generating {language} code…")

    try:
        from app.services.llm_service.llm import get_llm
        from app.prompts import get_code_generation_prompt

        # Optional RAG context for data-related queries (Python only — other
        # languages typically don't use uploaded datasets)
        rag_context = ""
        if material_ids and language == "python":
            try:
                import asyncio
                from app.services.rag.secure_retriever import secure_similarity_search_enhanced
                from app.services.rag.context_builder import build_context

                chunks = await asyncio.to_thread(
                    secure_similarity_search_enhanced,
                    user_id=user_id,
                    query=query,
                    material_ids=material_ids,
                    notebook_id=notebook_id,
                    use_mmr=True,
                    use_reranker=False,
                    return_formatted=True,
                )
                if chunks:
                    rag_context = chunks if isinstance(chunks, str) else build_context(chunks, max_tokens=settings.MAX_CONTEXT_TOKENS)
            except Exception:
                pass

        # Build prompt — request the specific language
        llm = get_llm(temperature=settings.LLM_TEMPERATURE_CODE)
        base_prompt = get_code_generation_prompt(query)
        lang_instruction = (
            f"\n\nIMPORTANT: Generate the code in {language.upper()}. "
            f"Return only the raw {language} code — no markdown fences, no explanation."
        )
        prompt = base_prompt + lang_instruction
        if rag_context:
            prompt = f"{prompt}\n\nAvailable context from uploaded materials:\n{rag_context}"

        code_response = await llm.ainvoke(prompt)
        code = getattr(code_response, "content", str(code_response)).strip()

        # Strip markdown fences (model may still emit them despite instructions)
        for fence in (f"```{language}", "```python", "```javascript", "```typescript",
                      "```java", "```go", "```rust", "```bash", "```c", "```cpp", "```"):
            if code.startswith(fence):
                code = code[len(fence):].strip()
                break
        if code.endswith("```"):
            code = code[:-3].strip()

        yield sse_code_block(code, language, session_id)
        yield sse_tool_result("python", success=True, summary="Code generated — review before running")

        yield ToolResult(
            tool_name="python",
            success=True,
            content="Here is the code to accomplish your task:",
            metadata={"code": code, "language": language, "phase": "generated"},
        )

    except Exception as exc:
        logger.error("Code generation failed: %s", exc)
        yield sse_tool_result("python", success=False, summary="Code generation failed")
        yield ToolResult(
            tool_name="python",
            success=False,
            content="",
            metadata={"error": str(exc)},
        )
