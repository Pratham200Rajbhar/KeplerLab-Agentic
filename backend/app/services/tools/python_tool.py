"""Python tool — Generates code via LLM for review before execution.

Phase 1: LLM generates code based on user message + optional RAG context.
Phase 2: User clicks "Run" → handled by a separate execution endpoint.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator, List, Optional

from app.core.config import settings
from app.services.chat_v2.schemas import ToolResult
from app.services.chat_v2.streaming import sse_tool_start, sse_tool_result, sse_code_block

logger = logging.getLogger(__name__)


async def execute(
    query: str,
    material_ids: List[str],
    user_id: str,
    notebook_id: str,
    session_id: str,
) -> AsyncIterator[str | ToolResult]:
    """Generate Python code for the user's request.

    Yields:
        SSE events (tool_start, code_block, tool_result) for streaming.
        Final yield is always a ToolResult.
    """
    yield sse_tool_start("python", label="Generating code…")

    try:
        from app.services.llm_service.llm import get_llm
        from app.prompts import get_code_generation_prompt

        # Optional RAG context for data-related queries
        rag_context = ""
        if material_ids:
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

        # Generate code
        llm = get_llm(temperature=settings.LLM_TEMPERATURE_CODE)
        prompt = get_code_generation_prompt(query)
        if rag_context:
            prompt = f"{prompt}\n\nAvailable context from uploaded materials:\n{rag_context}"

        code_response = await llm.ainvoke(prompt)
        code = getattr(code_response, "content", str(code_response)).strip()

        # Strip markdown fences
        if code.startswith("```python"):
            code = code[len("```python"):].strip()
        if code.startswith("```"):
            code = code[3:].strip()
        if code.endswith("```"):
            code = code[:-3].strip()

        yield sse_code_block(code, "python", session_id)
        yield sse_tool_result("python", success=True, summary="Code generated — review before running")

        yield ToolResult(
            tool_name="python",
            success=True,
            content=f"Here is the code to accomplish your task:",
            metadata={"code": code, "phase": "generated"},
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
