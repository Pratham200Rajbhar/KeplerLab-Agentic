"""Media transcriber — audio/video transcription via Whisper."""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, Any, List

from app.services.notebook_corpus.errors import PermanentError, SourceExtractionError
from app.services.notebook_corpus.schemas import ExtractedContent
from .normalization import normalize_text, estimate_tokens

logger = logging.getLogger(__name__)


async def transcribe_media(file_path: str) -> ExtractedContent:
    """Transcribe audio/video file using Whisper."""
    return await asyncio.to_thread(_run_whisper, file_path)


def _run_whisper(file_path: str) -> ExtractedContent:
    """Synchronous Whisper transcription."""
    warnings: List[str] = []

    try:
        import whisper
    except ImportError:
        raise PermanentError("openai-whisper is not installed — cannot transcribe media")

    try:
        model = whisper.load_model("base")
        result = model.transcribe(file_path, verbose=False)
    except Exception as e:
        raise SourceExtractionError(f"Whisper transcription failed: {e}")

    text = result.get("text", "")
    segments = result.get("segments", [])

    if not text.strip():
        raise PermanentError("Whisper produced empty transcription")

    sections: List[Dict[str, Any]] = []
    for seg in segments:
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        seg_text = seg.get("text", "").strip()
        if seg_text:
            sections.append({
                "title": f"[{_format_time(start)} - {_format_time(end)}]",
                "text": seg_text,
                "timestamp": start,
            })

    normalized = normalize_text(text)
    token_count = estimate_tokens(normalized)

    return ExtractedContent(
        text=normalized,
        metadata={
            "source_type": "audio_transcript",
            "language": result.get("language", "unknown"),
            "segment_count": len(segments),
        },
        sections=sections,
        warnings=warnings,
        token_count=token_count,
        page_count=0,
    )


def _format_time(seconds: float) -> str:
    """Format seconds as HH:MM:SS."""
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
