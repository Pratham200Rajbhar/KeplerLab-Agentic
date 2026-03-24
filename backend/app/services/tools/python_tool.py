from __future__ import annotations

import logging
import re
from typing import AsyncIterator, List

from app.core.config import settings
from app.services.chat_v2.schemas import ToolResult
from app.services.chat_v2.streaming import sse_tool_start, sse_tool_result, sse_code_block

logger = logging.getLogger(__name__)

_LANG_PATTERNS: List[tuple[str, str]] = [
    (r"\b(javascript|js|node\.?js?)\b", "javascript"),
    (r"\b(typescript|ts)\b", "typescript"),
    (r"\b(c\+\+|cpp)\b", "cpp"),
    (r"\bjava\b(?!\s*script)", "java"),
    (r"\b(golang|in go\b|go (?:code|program|script|func))", "go"),
    (r"\brust\b", "rust"),
    (r"\b(bash|shell|sh)\b", "bash"),
    (r"\bpython\b", "python"),
    (r"\bin c\b|\bwrite c\b|\busing c\b", "c"),
]

def _detect_language(query: str) -> str:
    q = query.lower()
    for pattern, lang in _LANG_PATTERNS:
        if re.search(pattern, q):
            return lang
    return "python"


# Marker injected by executor.py when passing prior step results to python_auto
_AGENT_CONTEXT_MARKER = "── Context from previous steps ──"

async def execute(
    query: str,
    material_ids: List[str],
    user_id: str,
    notebook_id: str,
    session_id: str,
    step_index: Optional[int] = None,
) -> AsyncIterator[str | ToolResult]:
    yield sse_tool_start("python", label="Generating code…")

    try:
        from app.services.llm_service.llm import get_llm
        from app.prompts import get_code_generation_prompt, get_agent_codegen_prompt

        rag_context = ""
        files_section = ""

        # ── Agent multi-step path: query contains prior-step research context ──
        is_agent_codegen = _AGENT_CONTEXT_MARKER in query
        if is_agent_codegen:
            # Split goal from injected research context
            parts = query.split(_AGENT_CONTEXT_MARKER, 1)
            step_goal = parts[0].strip()
            prior_context = parts[1].strip() if len(parts) > 1 else ""
            # Truncate research context so the LLM focuses on code quality,
            # not on cramming 100K chars of research into a PDF.
            _MAX_CONTEXT = 12_000
            if len(prior_context) > _MAX_CONTEXT:
                prior_context = prior_context[:_MAX_CONTEXT] + "\n\n[… context truncated for brevity …]"

            # Resolve uploaded material files so LLM knows exact filenames + schemas
            if material_ids:
                try:
                    from app.services.agent.material_files import get_material_file_map, build_files_prompt_section
                    file_map = await get_material_file_map(material_ids, user_id)
                    if file_map:
                        files_section = build_files_prompt_section(file_map)
                except Exception as exc:
                    logger.warning("Agent codegen: could not resolve material filenames: %s", exc)

            base_prompt = get_agent_codegen_prompt(step_goal=step_goal, prior_context=prior_context)
            # Agent codegen always produces Python — ignore language detection
            # (the full query includes research text that can falsely trigger
            # detection of "go", "rust", "c" etc.)
            language = "python"
        else:
            language = _detect_language(query)
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

                # Resolve real uploaded filenames so the LLM uses the exact names
                try:
                    from app.services.agent.material_files import get_material_file_map, build_files_prompt_section
                    file_map = await get_material_file_map(material_ids, user_id)
                    if file_map:
                        files_section = build_files_prompt_section(file_map)
                except Exception as exc:
                    logger.warning("Could not resolve material filenames: %s", exc)

            base_prompt = get_code_generation_prompt(query)

        llm = get_llm(temperature=settings.LLM_TEMPERATURE_CODE)
        lang_instruction = (
            f"\n\nIMPORTANT: Generate the code in {language.upper()}. "
            f"Return only the raw {language} code — no markdown fences, no explanation."
        )
        prompt = base_prompt + lang_instruction
        # Inject real filenames BEFORE rag context so LLM sees them prominently
        if files_section:
            prompt = f"{prompt}\n\n{files_section}"
        if rag_context:
            prompt = f"{prompt}\n\nAvailable context from uploaded materials:\n{rag_context}"

        code_response = await llm.ainvoke(prompt)
        code = getattr(code_response, "content", str(code_response)).strip()

        for fence in (f"```{language}", "```python", "```javascript", "```typescript",
                      "```java", "```go", "```rust", "```bash", "```c", "```cpp", "```"):
            if code.startswith(fence):
                code = code[len(fence):].strip()
                break
        if code.endswith("```"):
            code = code[:-3].strip()

        yield sse_code_block(code, language, session_id, step_index=step_index)
        yield sse_tool_result("python", success=True, summary="Code generated — review before running", step_index=step_index)

        yield ToolResult(
            tool_name="python",
            success=True,
            content="Here is the code to accomplish your task:",
            metadata={"code": code, "language": language, "phase": "generated"},
        )

    except Exception as exc:
        logger.error("Code generation failed: %s", exc)
        yield sse_tool_result("python", success=False, summary="Code generation failed", step_index=step_index)
        yield ToolResult(
            tool_name="python",
            success=False,
            content="",
            metadata={"error": str(exc)},
        )
