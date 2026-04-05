from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from app.db.prisma_client import prisma
from app.prompts import get_podcast_qa_prompt
from app.services.llm_service.llm import get_llm
from app.services.podcast.tts_service import synthesize_single
from app.services.podcast.voice_map import LANGUAGE_NAMES

logger = logging.getLogger(__name__)

async def _context_for_question(
    user_id: str,
    question: str,
    material_ids: list,
    notebook_id: Optional[str],
) -> str:
    terms = {t for t in str(question).lower().split() if len(t) > 3}
    where: Dict[str, object] = {"userId": str(user_id)}
    ids = [str(mid) for mid in (material_ids or []) if str(mid).strip()]
    if ids:
        where["id"] = {"in": ids}
    elif notebook_id:
        where["notebookId"] = str(notebook_id)
    else:
        return "No relevant context available."

    materials = await prisma.material.find_many(where=where, order={"updatedAt": "desc"})
    scored: list[tuple[int, str]] = []
    for material in materials:
        text = str(getattr(material, "originalText", "") or "").strip()
        if not text:
            continue
        snippet = text[:6000]
        lower = snippet.lower()
        score = sum(1 for term in terms if term in lower)
        title = str(getattr(material, "title", None) or getattr(material, "filename", None) or material.id)
        scored.append((score, f"[SOURCE - Material: {title}]\n{snippet}"))

    if not scored:
        return "No relevant context available."

    scored.sort(key=lambda item: item[0], reverse=True)
    top_blocks = [block for _, block in scored[:4]]
    return "\n\n".join(top_blocks)

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

    context = await _context_for_question(
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
