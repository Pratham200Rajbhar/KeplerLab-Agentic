"""Chat V2 — Context builder.

Constructs the LLM message list from conversation history,
system prompt, optional RAG documents, and the user message.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from app.prompts import get_chat_prompt

logger = logging.getLogger(__name__)

# Default system prompt when no RAG context is available (normal chat)
_SYSTEM_PROMPT = (
    "You are **KeplerLab AI** — a brilliant, knowledgeable assistant. "
    "Be thorough when depth matters; concise when it doesn't. "
    "Use Markdown (headers, bullets, code blocks, bold) to make responses scannable."
)


def build_messages(
    user_message: str,
    history: List[Dict[str, str]],
    rag_context: Optional[str] = None,
    system_prompt: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Build the LLM message list.

    Args:
        user_message: Current user message.
        history: Conversation history as list of ``{"role": ..., "content": ...}``.
        rag_context: Optional retrieved context from vector DB.
        system_prompt: Optional override for the system prompt.

    Returns:
        Messages list ready for LLM:
        ``[{"role":"system","content":"..."}, {"role":"user","content":"..."}, ...]``
    """
    messages: List[Dict[str, str]] = []

    # System prompt
    if rag_context:
        # Use the full RAG-aware prompt template
        prompt_text = get_chat_prompt(
            context=rag_context,
            chat_history=_format_history(history),
            user_message=user_message,
        )
        # The chat_prompt.txt already embeds system, context, history, and user message.
        # Return as a single user message (works with all providers including Ollama).
        messages.append({"role": "user", "content": prompt_text})
    else:
        # Normal chat — system prompt + history + user message
        messages.append({"role": "system", "content": system_prompt or _SYSTEM_PROMPT})

        # Append conversation history (last 10 turns)
        for msg in history[-20:]:  # 20 messages = 10 turns
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if content and role in ("user", "assistant"):
                messages.append({"role": role, "content": content})

        # Current user message
        messages.append({"role": "user", "content": user_message})

    return messages


def build_messages_for_tool(
    user_message: str,
    tool_context: str,
    history: List[Dict[str, str]],
    system_prompt: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Build the LLM message list with tool-provided context.

    Used when a tool (web search, code execution) provides context
    that should be included alongside the user message.

    Args:
        user_message: Current user message.
        tool_context: Context provided by tool execution.
        history: Conversation history.
        system_prompt: Optional system prompt override.

    Returns:
        Messages list for LLM.
    """
    messages: List[Dict[str, str]] = []
    messages.append({"role": "system", "content": system_prompt or _SYSTEM_PROMPT})

    for msg in history[-20:]:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if content and role in ("user", "assistant"):
            messages.append({"role": role, "content": content})

    # Combine user message with tool context
    augmented = (
        f"{user_message}\n\n"
        f"---\n"
        f"Context from tool execution:\n{tool_context}"
    )
    messages.append({"role": "user", "content": augmented})

    return messages


def _format_history(history: List[Dict[str, str]]) -> str:
    """Format history into text for the RAG prompt template."""
    if not history:
        return "None"
    lines = []
    for msg in history[-10:]:
        role = msg.get("role", "user").capitalize()
        content = msg.get("content", "")
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines) if lines else "None"
