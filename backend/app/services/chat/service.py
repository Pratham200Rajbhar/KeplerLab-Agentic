"""Backward-compatible service shim — delegates to chat_v2.

Any code importing from ``app.services.chat.service`` will transparently
use the new chat_v2 module.
"""

from app.services.chat_v2.message_store import (
    get_history as get_chat_history,
    save_response_blocks,
    log_agent_execution,
    clear_history as clear_chat_history,
    get_sessions as get_chat_sessions,
    ensure_session as create_chat_session,
    delete_session as delete_chat_session,
    save_user_message,
    save_assistant_message,
)
from app.services.chat_v2.service import (
    block_followup_stream,
    get_suggestions,
)


async def save_conversation(
    notebook_id: str,
    user_id: str,
    user_message: str,
    assistant_answer: str,
    session_id: str = None,
    agent_meta: dict = None,
) -> str:
    """Persist a user/assistant exchange. Returns the assistant message ID."""
    if user_message:
        await save_user_message(notebook_id, user_id, session_id, user_message)
    if assistant_answer:
        return await save_assistant_message(
            notebook_id, user_id, session_id, assistant_answer, agent_meta
        )
    return ""


def compute_confidence_score(context: str, answer: str, reranker_scores=None) -> float:
    """Compute a 0–1 confidence score (simplified)."""
    import re
    scores = []
    if reranker_scores:
        avg = sum(reranker_scores[:3]) / min(3, len(reranker_scores))
        scores.append(max(0.0, min(1.0, (avg + 5) / 10)))
    if answer:
        citations = re.findall(r'\[SOURCE\s+\d+\]', answer)
        word_count = len(answer.split())
        if word_count > 0:
            density = (len(citations) / word_count) * 100
            scores.append(min(1.0, density / 3.0))
    return round(sum(scores) / len(scores), 2) if scores else 0.5
