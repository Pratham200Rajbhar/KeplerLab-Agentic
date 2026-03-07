"""Chat V2 — Chat service.

Top-level service consumed by the API router:
- Session management
- Message dispatch to orchestrator
- Block followup
- Suggestions
"""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from app.services.llm_service.llm import get_llm, get_llm_structured, extract_chunk_content

from . import message_store, orchestrator

logger = logging.getLogger(__name__)


# ── Session management ────────────────────────────────────────


async def create_session(notebook_id: str, user_id: str, title: str = "New Chat") -> str:
    """Create a new chat session. Returns the session ID."""
    return await message_store.ensure_session(notebook_id, user_id, None, title)


async def get_sessions(notebook_id: str, user_id: str) -> List[Dict[str, Any]]:
    """List all chat sessions for a notebook."""
    return await message_store.get_sessions(notebook_id, user_id)


async def delete_session(session_id: str, user_id: str) -> bool:
    """Delete a chat session."""
    return await message_store.delete_session(session_id, user_id)


# ── Chat dispatch ─────────────────────────────────────────────


async def chat_stream(
    message: str,
    notebook_id: str,
    user_id: str,
    session_id: str,
    material_ids: List[str],
    intent_override: Optional[str] = None,
) -> AsyncIterator[str]:
    """Stream chat response via the orchestrator.

    Args:
        message: User's message.
        notebook_id: Notebook context.
        user_id: Owner.
        session_id: Chat session (already ensured).
        material_ids: Validated material IDs.
        intent_override: Optional explicit capability override.

    Yields:
        SSE-formatted event strings.
    """
    async for event in orchestrator.run(
        message=message,
        notebook_id=notebook_id,
        user_id=user_id,
        session_id=session_id,
        material_ids=material_ids,
        intent_override=intent_override,
    ):
        yield event


# ── History ───────────────────────────────────────────────────


async def get_history(
    notebook_id: str, user_id: str, session_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve chat history."""
    return await message_store.get_history(notebook_id, user_id, session_id)


async def clear_history(
    notebook_id: str, user_id: str, session_id: Optional[str] = None
) -> None:
    """Clear chat history."""
    await message_store.clear_history(notebook_id, user_id, session_id)


# ── Block followup ────────────────────────────────────────────


async def block_followup_stream(
    block_id: str,
    action: str,
    question: str,
) -> AsyncIterator[str]:
    """Stream an LLM response for a block-level follow-up action.

    Supported actions: ask, simplify, translate, explain.
    Yields raw text chunks.
    """
    from app.db.prisma_client import prisma

    block = await prisma.responseblock.find_unique(where={"id": block_id})
    if not block:
        yield f"Error: Could not find paragraph block with ID {block_id}"
        return

    block_text = block.text

    action_prompts = {
        "ask": (
            f'Based on this specific paragraph:\n\n"{block_text}"\n\n'
            f"Answer this question: {question}"
        ),
        "simplify": (
            f"Simplify the following paragraph to make it easier to understand. "
            f'Keep the key information but use simpler language:\n\n"{block_text}"'
        ),
        "translate": f'Translate the following paragraph to {question}:\n\n"{block_text}"',
        "explain": (
            f"Explain the following paragraph in much more depth and detail. "
            f'Provide examples and context:\n\n"{block_text}"'
        ),
    }

    prompt = action_prompts.get(action, action_prompts["ask"])
    llm = get_llm()

    async for chunk in llm.astream(prompt):
        content = extract_chunk_content(chunk)
        if content:
            yield content


# ── Suggestions ───────────────────────────────────────────────


async def get_suggestions(
    partial_input: str, notebook_id: str, user_id: str
) -> List[Dict[str, Any]]:
    """Generate smart prompt suggestions based on partial input."""
    from app.services.llm_service.structured_invoker import parse_json_robust
    from app.db.prisma_client import prisma

    notebook = await prisma.notebook.find_unique(
        where={"id": notebook_id},
        include={"materials": True},
    )
    if not notebook or notebook.userId != user_id:
        return []

    notebook_title = notebook.name
    material_titles = [m.title or m.filename for m in getattr(notebook, "materials", [])]
    materials_context = (
        "\n".join(f"- {t}" for t in material_titles)
        if material_titles
        else "No materials uploaded yet."
    )

    prompt = f"""You are an expert AI prompt engineer assistant for an educational platform.
The user is typing an inquiry regarding their uploaded documents, and needs auto-complete suggestions.

Notebook Context:
Title: "{notebook_title}"
Available Materials:
{materials_context}

Partial user input: "{partial_input}"

Your task is to predict the user's intent and provide 3-5 highly optimized, agentic, and comprehensive prompt completions.
Transform the user's basic thought into a structured, powerful prompt that will yield an exceptional AI response.

Return ONLY a JSON array in the exact format:
[
    {{"suggestion": "In-depth and structured prompt replacing or extending the user's input...", "confidence": 0.95}},
    {{"suggestion": "Alternative highly optimized prompt based on the context...", "confidence": 0.85}}
]

Rules for suggestions:
1. Must logically start with or seamlessly replace/extend the user's partial input.
2. Elevate the prompt.
3. Make them context-aware based on the notebook materials.
4. Set confidence from 0.0 to 1.0 based on relevance.
5. Provide ONLY the JSON array.
"""

    try:
        llm = get_llm_structured()
        response = await llm.ainvoke(prompt)
        text = getattr(response, "content", str(response)).strip()
        parsed = parse_json_robust(text)
        if not isinstance(parsed, list):
            parsed = parsed.get("suggestions", [])

        suggestions = []
        partial_words = set(partial_input.lower().split())
        for item in parsed:
            suggestion_text = item.get("suggestion", "")
            if not suggestion_text:
                continue
            llm_conf = float(item.get("confidence", 0.5))
            # Simple lexical overlap
            suggestion_words = set(suggestion_text.lower().split())
            overlap = len(partial_words & suggestion_words) / max(len(partial_words), 1)
            final_conf = (llm_conf + overlap) / 2
            suggestions.append({
                "suggestion": suggestion_text,
                "confidence": round(final_conf, 2),
            })

        suggestions.sort(key=lambda x: x["confidence"], reverse=True)
        return suggestions[:5]
    except Exception as exc:
        logger.error("get_suggestions failed: %s", exc)
        return []
