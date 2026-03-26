from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.services.auth import get_current_user
from app.db.prisma_client import prisma
from app.services.podcast import session_manager, qa_service, export_service
from app.services.podcast.tts_service import (
    get_segment_audio_path,
    get_audio_file_path,
    generate_voice_preview,
)
from app.services.podcast.voice_map import (
    get_voices_for_language,
    get_default_voices,
    get_preview_text,
    VOICE_MAP,
    LANGUAGE_NAMES,
)
from app.services.podcast.export_service import get_export_file_path

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/podcast", tags=["podcast"])

class CreateSessionRequest(BaseModel):
    notebook_id: str
    mode: str = Field(default="overview", pattern="^(overview|deep-dive|debate|q-and-a|full|topic)$")
    topic: Optional[str] = None
    language: str = Field(default="en", max_length=10)
    host_voice: Optional[str] = None
    guest_voice: Optional[str] = None
    material_ids: List[str] = Field(default_factory=list)

class StartGenerationRequest(BaseModel):
    pass

class QuestionRequest(BaseModel):
    question_text: str
    paused_at_segment: int
    question_audio_url: Optional[str] = None

class BookmarkRequest(BaseModel):
    segment_index: int
    label: Optional[str] = None

class AnnotationRequest(BaseModel):
    segment_index: int
    note: str

class ExportRequest(BaseModel):
    format: str = Field(pattern="^(pdf|json)$")

class UpdateSessionRequest(BaseModel):
    title: Optional[str] = None
    tags: Optional[List[str]] = None
    current_segment: Optional[int] = None

@router.post("/session")
async def create_session(req: CreateSessionRequest, user=Depends(get_current_user)):
    if req.mode in ("topic", "deep-dive") and not req.topic:
        raise HTTPException(400, "Topic is required for topic/deep-dive mode")
    if not req.material_ids:
        raise HTTPException(400, "At least one material ID is required")

    try:
        result = await session_manager.create_session(
            user_id=user.id,
            notebook_id=req.notebook_id,
            mode=req.mode,
            topic=req.topic,
            language=req.language,
            host_voice=req.host_voice,
            guest_voice=req.guest_voice,
            material_ids=req.material_ids,
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.get("/session/{session_id}")
async def get_session(session_id: str, user=Depends(get_current_user)):
    result = await session_manager.get_session(session_id, user.id)
    if not result:
        raise HTTPException(404, "Session not found")
    return result

@router.get("/sessions/{notebook_id}")
async def list_sessions(notebook_id: str, user=Depends(get_current_user)):
    return await session_manager.get_sessions_for_notebook(notebook_id, user.id)

@router.patch("/session/{session_id}")
async def update_session(
    session_id: str, req: UpdateSessionRequest, user=Depends(get_current_user)
):
    if req.title is not None:
        result = await session_manager.update_session_title(session_id, user.id, req.title)
        if not result:
            raise HTTPException(404, "Session not found")
    if req.tags is not None:
        result = await session_manager.update_session_tags(session_id, user.id, req.tags)
        if not result:
            raise HTTPException(404, "Session not found")
    if req.current_segment is not None:
        session = await session_manager.get_session(session_id, str(user.id))
        if not session:
            raise HTTPException(404, "Session not found")
        await session_manager.update_current_segment(session_id, req.current_segment)
    
    return await session_manager.get_session(session_id, user.id)

@router.delete("/session/{session_id}")
async def delete_session(session_id: str, user=Depends(get_current_user)):
    deleted = await session_manager.delete_session(session_id, user.id)
    if not deleted:
        raise HTTPException(404, "Session not found")
    return {"deleted": True}

@router.post("/session/{session_id}/start")
async def start_generation(session_id: str, user=Depends(get_current_user)):
    try:
        await session_manager.start_generation(session_id, user.id)
        return {"status": "started", "session_id": session_id}
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.get("/session/{session_id}/segment/{segment_index}/audio")
async def get_segment_audio(
    session_id: str, segment_index: int, user=Depends(get_current_user)
):
    path = get_segment_audio_path(session_id, segment_index)
    if not path:
        raise HTTPException(404, "Audio segment not found")
    return FileResponse(path, media_type="audio/mpeg")

@router.get("/session/{session_id}/audio/{filename}")
async def get_audio_file(
    session_id: str, filename: str, user=Depends(get_current_user)
):
    path = get_audio_file_path(session_id, filename)
    if not path:
        raise HTTPException(404, "Audio file not found")
    return FileResponse(path, media_type="audio/mpeg")

@router.post("/session/{session_id}/question")
async def ask_question(
    session_id: str, req: QuestionRequest, user=Depends(get_current_user)
):
    try:
        result = await qa_service.handle_question(
            session_id=session_id,
            user_id=user.id,
            question_text=req.question_text,
            paused_at_segment=req.paused_at_segment,
            question_audio_url=req.question_audio_url,
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.get("/session/{session_id}/doubts")
async def get_doubts(session_id: str, user=Depends(get_current_user)):
    return await qa_service.get_doubts(session_id, user.id)

@router.post("/session/{session_id}/bookmark")
async def add_bookmark(
    session_id: str, req: BookmarkRequest, user=Depends(get_current_user)
):
    db = prisma
    
    session = await db.podcastsession.find_first(
        where={"id": session_id, "userId": user.id}
    )
    if not session:
        raise HTTPException(404, "Session not found")
    
    bookmark = await db.podcastbookmark.create(
        data={
            "sessionId": session_id,
            "segmentIndex": req.segment_index,
            "label": req.label,
        }
    )
    return {
        "id": bookmark.id,
        "segmentIndex": bookmark.segmentIndex,
        "label": bookmark.label,
    }

@router.get("/session/{session_id}/bookmarks")
async def get_bookmarks(session_id: str, user=Depends(get_current_user)):
    db = prisma
    
    bookmarks = await db.podcastbookmark.find_many(
        where={"sessionId": session_id, "session": {"userId": user.id}},
        order={"segmentIndex": "asc"},
    )
    return [
        {
            "id": b.id,
            "segmentIndex": b.segmentIndex,
            "label": b.label,
            "createdAt": b.createdAt.isoformat() if b.createdAt else None,
        }
        for b in bookmarks
    ]

@router.delete("/session/{session_id}/bookmark/{bookmark_id}")
async def delete_bookmark(
    session_id: str, bookmark_id: str, user=Depends(get_current_user)
):
    db = prisma
    
    bookmark = await db.podcastbookmark.find_first(
        where={"id": bookmark_id, "session": {"id": session_id, "userId": user.id}}
    )
    if not bookmark:
        raise HTTPException(404, "Bookmark not found")
    
    await db.podcastbookmark.delete(where={"id": bookmark_id})
    return {"deleted": True}

@router.post("/session/{session_id}/annotation")
async def add_annotation(
    session_id: str, req: AnnotationRequest, user=Depends(get_current_user)
):
    db = prisma
    
    session = await db.podcastsession.find_first(
        where={"id": session_id, "userId": user.id}
    )
    if not session:
        raise HTTPException(404, "Session not found")
    
    annotation = await db.podcastannotation.create(
        data={
            "sessionId": session_id,
            "segmentIndex": req.segment_index,
            "note": req.note,
        }
    )
    return {
        "id": annotation.id,
        "segmentIndex": annotation.segmentIndex,
        "note": annotation.note,
    }

@router.delete("/session/{session_id}/annotation/{annotation_id}")
async def delete_annotation(
    session_id: str, annotation_id: str, user=Depends(get_current_user)
):
    db = prisma
    
    annotation = await db.podcastannotation.find_first(
        where={"id": annotation_id, "session": {"id": session_id, "userId": user.id}}
    )
    if not annotation:
        raise HTTPException(404, "Annotation not found")
    
    await db.podcastannotation.delete(where={"id": annotation_id})
    return {"deleted": True}

@router.post("/session/{session_id}/export")
async def trigger_export(
    session_id: str, req: ExportRequest, user=Depends(get_current_user)
):
    try:
        result = await export_service.create_export(session_id, user.id, req.format)
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.get("/export/{export_id}")
async def get_export_status(export_id: str, user=Depends(get_current_user)):
    result = await export_service.get_export(export_id)
    if not result:
        raise HTTPException(404, "Export not found")
    return result

@router.get("/export/file/{session_id}/{filename}")
async def download_export(
    session_id: str, filename: str, user=Depends(get_current_user)
):
    path = get_export_file_path(session_id, filename)
    if not path:
        raise HTTPException(404, "Export file not found")
    
    media_type = "application/json" if filename.endswith(".json") else "application/pdf"
    return FileResponse(path, media_type=media_type, filename=filename)

@router.post("/session/{session_id}/summary")
async def generate_summary(session_id: str, user=Depends(get_current_user)):
    try:
        summary = await export_service.generate_summary(session_id, user.id)
        return {"summary": summary}
    except ValueError as e:
        raise HTTPException(400, str(e))

@router.get("/voices")
async def get_voices(language: str = Query(default="en")):
    voices = get_voices_for_language(language)
    defaults = get_default_voices(language)
    return {
        "language": language,
        "language_name": LANGUAGE_NAMES.get(language, language),
        "voices": voices,
        "defaults": defaults,
    }

@router.get("/voices/all")
async def get_all_voices():
    return {
        lang: {
            "language_name": LANGUAGE_NAMES.get(lang, lang),
            "voices": voices,
            "defaults": get_default_voices(lang),
        }
        for lang, voices in VOICE_MAP.items()
    }

@router.get("/languages")
async def get_languages():
    return [
        {"code": code, "name": name}
        for code, name in LANGUAGE_NAMES.items()
        if code in VOICE_MAP
    ]

@router.post("/voice/preview")
async def preview_voice(
    voice_id: str = Query(...),
    language: str = Query(default="en"),
):
    text = get_preview_text(language)
    audio_bytes = await generate_voice_preview(voice_id, text)
    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Content-Disposition": f"inline; filename=preview_{voice_id}.mp3"},
    )

@router.post("/session/{session_id}/satisfaction")
async def check_satisfaction(
    session_id: str,
    message: str = Query(...),
    user=Depends(get_current_user),
):
    from app.services.podcast.satisfaction_detector import detect_satisfaction
    
    db = prisma
    session = await db.podcastsession.find_first(
        where={"id": session_id, "userId": user.id}
    )
    if not session:
        raise HTTPException(404, "Session not found")
    
    action, confidence = await detect_satisfaction(message, session.language)
    return {"action": action, "confidence": confidence}
