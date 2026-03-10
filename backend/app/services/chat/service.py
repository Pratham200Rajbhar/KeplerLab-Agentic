from app.services.chat_v2.message_store import (
    save_user_message,
    save_assistant_message,
)

async def save_conversation(
    notebook_id: str,
    user_id: str,
    user_message: str,
    assistant_answer: str,
    session_id: str = None,
    agent_meta: dict = None,
) -> str:
    if user_message:
        await save_user_message(notebook_id, user_id, session_id, user_message)
    if assistant_answer:
        return await save_assistant_message(
            notebook_id, user_id, session_id, assistant_answer, agent_meta
        )
    return ""


