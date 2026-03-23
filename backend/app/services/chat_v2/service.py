from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Dict, List, Optional

from app.services.llm_service.llm import get_llm, get_llm_structured, extract_chunk_content
from app.prompts import get_suggestions_prompt, get_empty_state_suggestions_prompt, get_block_followup_prompt

from . import message_store, orchestrator

logger = logging.getLogger(__name__)

async def create_session(notebook_id: str, user_id: str, title: str = "New Chat") -> str:
    return await message_store.ensure_session(notebook_id, user_id, None, title)

async def get_sessions(notebook_id: str, user_id: str) -> List[Dict[str, Any]]:
    return await message_store.get_sessions(notebook_id, user_id)

async def delete_session(session_id: str, user_id: str) -> bool:
    return await message_store.delete_session(session_id, user_id)

async def delete_message(message_id: str, user_id: str) -> bool:
    return await message_store.delete_message_pair(message_id, user_id)

async def update_message(message_id: str, user_id: str, content: str) -> bool:
    return await message_store.update_user_message(message_id, user_id, content)

async def chat_stream(
    message: str,
    notebook_id: str,
    user_id: str,
    session_id: str,
    material_ids: List[str],
    intent_override: Optional[str] = None,
) -> AsyncIterator[str]:
    async for event in orchestrator.run(
        message=message,
        notebook_id=notebook_id,
        user_id=user_id,
        session_id=session_id,
        material_ids=material_ids,
        intent_override=intent_override,
    ):
        yield event

async def get_history(
    notebook_id: str, user_id: str, session_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    return await message_store.get_history(notebook_id, user_id, session_id)

async def clear_history(
    notebook_id: str, user_id: str, session_id: Optional[str] = None
) -> None:
    await message_store.clear_history(notebook_id, user_id, session_id)

async def block_followup_stream(
    block_id: str,
    action: str,
    question: str,
) -> AsyncIterator[str]:
    from app.db.prisma_client import prisma

    block = await prisma.responseblock.find_unique(where={"id": block_id})
    if not block:
        yield f"Error: Could not find paragraph block with ID {block_id}"
        return

    block_text = block.text

    prompt = get_block_followup_prompt(action=action, block_text=block_text, question=question)
    llm = get_llm()

    async for chunk in llm.astream(prompt):
        content = extract_chunk_content(chunk)
        if content:
            yield content

async def get_suggestions(
    partial_input: str, notebook_id: str, user_id: str
) -> List[Dict[str, Any]]:
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

    prompt = get_suggestions_prompt(
        notebook_title=notebook_title,
        materials_context=materials_context,
        partial_input=partial_input,
    )

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

_GENERAL_SUGGESTIONS = [
    "Explain how neural networks work",
    "How does reinforcement learning work?",
    "What are the basics of data analysis?",
    "How can I build an AI model?",
    "What is the difference between supervised and unsupervised learning?",
]

_FALLBACK_RESOURCE_SUGGESTIONS = [
    "Explain the main concept in these documents",
    "Summarize the key ideas from the materials",
    "What are the important topics in these files?",
    "Create flashcards from these resources",
    "Generate a quiz based on these materials",
    "What questions would an exam ask about these documents?",
]

async def get_empty_state_suggestions(
    material_ids: List[str], user_id: str
) -> Dict[str, Any]:
    from app.services.llm_service.structured_invoker import parse_json_robust
    from app.db.prisma_client import prisma

    if not material_ids:
        return {"topics": None, "suggestions": _GENERAL_SUGGESTIONS}

    materials = await prisma.material.find_many(
        where={"id": {"in": material_ids}, "userId": user_id},
    )
    if not materials:
        return {"topics": None, "suggestions": _GENERAL_SUGGESTIONS}

    material_titles = [m.title or m.filename for m in materials]
    materials_context = "\n".join(f"- {t}" for t in material_titles)

    prompt = get_empty_state_suggestions_prompt(materials_context)

    try:
        llm = get_llm_structured()
        response = await llm.ainvoke(prompt)
        text = getattr(response, "content", str(response)).strip()
        parsed = parse_json_robust(text)
        if not isinstance(parsed, dict):
            raise ValueError("LLM returned non-dict response")

        topics = [t for t in parsed.get("topics", []) if isinstance(t, str)][:5]
        suggestions = [s for s in parsed.get("suggestions", []) if isinstance(s, str)][:6]

        if not suggestions:
            raise ValueError("Empty suggestions from LLM")

        return {"topics": topics or None, "suggestions": suggestions}
    except Exception as exc:
        logger.error("get_empty_state_suggestions failed: %s", exc)
        return {"topics": None, "suggestions": _FALLBACK_RESOURCE_SUGGESTIONS}
