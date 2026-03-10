from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from app.db.prisma_client import prisma
from app.prompts import get_podcast_qa_prompt
from app.services.llm_service.llm import get_llm
from app.services.rag.secure_retriever import secure_similarity_search_enhanced
from app.services.podcast.tts_service import synthesize_single
from app.services.podcast.voice_map import LANGUAGE_NAMES

logger = logging.getLogger(__name__)

def _rag_for_question(
    user_id: str,
    question: str,
    material_ids: list,
    notebook_id: Optional[str],
) -> str:
    nb_filter = notebook_id if not material_ids else None
    ctx = secure_similarity_search_enhanced(
        user_id=user_id,
        query=question,
        material_ids=material_ids,
        notebook_id=nb_filter,
        use_mmr=True,
        use_reranker=True,
        return_formatted=True,
    )
    if not ctx or ctx == "No relevant context found.":
        ctx = secure_similarity_search_enhanced(
            user_id=user_id,
            query=question,
            material_ids=material_ids,
            notebook_id=None,
            use_mmr=False,
            use_reranker=False,
            return_formatted=True,
        )
    return ctx or "No relevant context available."

async def handle_question(
    session_id: str,
    user_id: str,
    question_text: str,
    paused_at_segment: int,
    question_audio_url: Optional[str] = None,
) -> Dict:
    db = prisma
    session = await db.podcastsession.find_first(
        where={"id": session_id, "userId": user_id}
    )
    if not session:
        raise ValueError("Session not found")

    logger.info(
        "Q&A: session=%s segment=%d question=%s",
        session_id, paused_at_segment, question_text[:80],
    )

    context = await asyncio.to_thread(
        _rag_for_question,
        user_id, question_text, session.materialIds, session.notebookId,
    )

    language_name = LANGUAGE_NAMES.get(session.language, "English")
    prompt = get_podcast_qa_prompt(
        language=language_name,
        context=context,
        question=question_text,
    )

    llm = get_llm(mode="chat", max_tokens=2000)
    response = await asyncio.to_thread(llm.invoke, prompt)
    answer_text = response.content if hasattr(response, "content") else str(response)

    answer_filename = f"qa_{uuid.uuid4().hex[:8]}.mp3"
    tts_result = await synthesize_single(
        session_id=session_id,
        text=answer_text,
        voice_id=session.guestVoice,
        filename=answer_filename,
    )

    doubt = await db.podcastdoubt.create(
        data={
            "sessionId": session_id,
            "pausedAtSegment": paused_at_segment,
            "questionText": question_text,
            "questionAudioUrl": question_audio_url,
            "answerText": answer_text,
            "answerAudioUrl": tts_result["audio_url"],
        },
    )

    logger.info("Q&A answered: doubt=%s answer_len=%d", doubt.id, len(answer_text))

    return {
        "id": doubt.id,
        "questionText": question_text,
        "answerText": answer_text,
        "audioPath": tts_result["audio_url"],
        "answerDurationMs": tts_result["duration_ms"],
        "pausedAtSegment": paused_at_segment,
    }

async def get_doubts(session_id: str, user_id: str) -> list:
    db = prisma
    session = await db.podcastsession.find_first(
        where={"id": session_id, "userId": user_id}
    )
    if not session:
        return []

    doubts = await db.podcastdoubt.find_many(
        where={"sessionId": session_id},
        order={"createdAt": "asc"},
    )

    return [
        {
            "id": d.id,
            "pausedAtSegment": d.pausedAtSegment,
            "questionText": d.questionText,
            "questionAudioUrl": d.questionAudioUrl,
            "answerText": d.answerText,
            "audioPath": d.answerAudioUrl,
            "resolvedAt": d.resolvedAt.isoformat() if d.resolvedAt else None,
            "createdAt": d.createdAt.isoformat() if d.createdAt else None,
        }
        for d in doubts
    ]

async def resolve_doubt(doubt_id: str) -> None:
    db = prisma
    await db.podcastdoubt.update(
        where={"id": doubt_id},
        data={"resolvedAt": datetime.now(timezone.utc)},
    )
