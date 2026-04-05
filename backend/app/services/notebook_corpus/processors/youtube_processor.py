"""YouTube source processor — extracts transcripts from YouTube videos."""
from __future__ import annotations

import logging
from typing import Any, Dict

from app.services.notebook_corpus.enums import SourceType
from app.services.notebook_corpus.errors import PermanentError, SourceExtractionError, TransientError
from app.services.notebook_corpus.fingerprints import compute_fingerprint
from app.services.notebook_corpus.schemas import ExtractedContent
from app.services.notebook_corpus.validators import validate_youtube_source

from . import register_processor
from .base import BaseSourceProcessor

logger = logging.getLogger(__name__)


@register_processor(SourceType.YOUTUBE)
class YouTubeProcessor(BaseSourceProcessor):
    """Processes YouTube sources by extracting transcripts."""

    async def validate_input(self, *, source_data: Dict[str, Any]) -> None:
        url = source_data.get("url", "")
        video_id = validate_youtube_source(url)
        source_data["video_id"] = video_id

    async def normalize_input(self, *, source_data: Dict[str, Any]) -> Dict[str, Any]:
        return source_data

    async def extract_content(self, *, source_data: Dict[str, Any]) -> ExtractedContent:
        import asyncio
        from app.services.notebook_corpus.extraction.normalization import normalize_text, estimate_tokens

        video_id = source_data.get("video_id", "")
        url = source_data.get("url", "")

        try:
            transcript_data = await asyncio.to_thread(self._fetch_transcript, video_id)
        except Exception as e:
            err_str = str(e).lower()
            if "no transcript" in err_str or "disabled" in err_str:
                raise PermanentError(f"No transcript available for YouTube video: {url}")
            if "too many requests" in err_str or "rate" in err_str:
                raise TransientError(f"YouTube rate limited: {e}")
            raise SourceExtractionError(f"Failed to extract YouTube transcript: {e}")

        full_text = transcript_data["text"]
        if not full_text.strip():
            raise PermanentError(f"Empty transcript for YouTube video: {url}")

        normalized = normalize_text(full_text)
        token_count = estimate_tokens(normalized)
        source_data["fingerprint"] = compute_fingerprint(normalized)

        # Use video title from transcript API if available
        title = transcript_data.get("title", "")
        if title and not source_data.get("title"):
            source_data["title"] = title[:510]

        sections = []
        for seg in transcript_data.get("segments", []):
            sections.append({
                "title": f"[{seg.get('start', 0):.0f}s]",
                "text": seg.get("text", ""),
                "timestamp": seg.get("start", 0),
            })

        return ExtractedContent(
            text=normalized,
            metadata={
                "url": url,
                "video_id": video_id,
                "title": title,
                "source_type": "youtube",
                "segment_count": len(transcript_data.get("segments", [])),
            },
            sections=sections,
            warnings=[],
            token_count=token_count,
            page_count=0,
        )

    @staticmethod
    def _fetch_transcript(video_id: str) -> Dict[str, Any]:
        """Synchronous transcript fetch — runs in thread pool."""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi

            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # Try to get manually created transcript first, then auto-generated
            transcript = None
            for t in transcript_list:
                if not t.is_generated:
                    transcript = t
                    break
            if transcript is None:
                transcript = transcript_list.find_transcript(["en"])

            segments = transcript.fetch()
            # segments is a list of dicts with 'text', 'start', 'duration'
            segment_list = []
            text_parts = []
            for seg in segments:
                seg_dict = {
                    "text": seg.get("text", seg.text if hasattr(seg, "text") else str(seg)),
                    "start": seg.get("start", seg.start if hasattr(seg, "start") else 0),
                    "duration": seg.get("duration", seg.duration if hasattr(seg, "duration") else 0),
                }
                segment_list.append(seg_dict)
                text_parts.append(seg_dict["text"])

            return {
                "text": " ".join(text_parts),
                "segments": segment_list,
                "title": "",
            }
        except Exception:
            # Fallback: try simpler API
            from youtube_transcript_api import YouTubeTranscriptApi
            segments = YouTubeTranscriptApi.get_transcript(video_id)
            text_parts = [s["text"] for s in segments]
            return {
                "text": " ".join(text_parts),
                "segments": segments,
                "title": "",
            }
