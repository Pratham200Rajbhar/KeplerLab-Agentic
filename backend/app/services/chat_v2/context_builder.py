from __future__ import annotations

import logging
from typing import Dict, List, Optional

from app.prompts import compose_prompt, get_chat_prompt

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = compose_prompt(
    [
        "system/base_system.md",
        "shared/style.md",
        "shared/formatting.md",
        "chat/chat_base.md",
    ],
    {
        "mode": "chat",
        "question": "",
        "conversation_history": "",
        "instructions": "",
    },
)

def build_messages(
    user_message: str,
    history: List[Dict[str, str]],
    rag_context: Optional[str] = None,
    system_prompt: Optional[str] = None,
) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []

    if rag_context:
        prompt_text = get_chat_prompt(
            context=rag_context,
            chat_history=_format_history(history),
            user_message=user_message,
        )
        messages.append({"role": "user", "content": prompt_text})
    else:
        messages.append({"role": "system", "content": system_prompt or _SYSTEM_PROMPT})

        for msg in history[-20:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if content and role in ("user", "assistant"):
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_message})

    return messages

def _format_history(history: List[Dict[str, str]]) -> str:
    if not history:
        return "None"
    lines = []
    for msg in history[-10:]:
        role = msg.get("role", "user").capitalize()
        content = msg.get("content", "")
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines) if lines else "None"
