"""
Video Generator — creates explainer videos by combining slide images + TTS audio via ffmpeg.

Reuses the existing TTS service (edge_tts) from podcast/tts_service.py for audio
generation and shells out to ffmpeg for video composition.

Script generation is now delegated to slide_narrator.py which provides:
- Vision-augmented narration (slide image → LLM)
- RAG-grounded context injection
- Argument-role-aware rhetorical style
- Parallel generation with semaphore
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

from app.services.podcast.tts_service import synthesize_segment
# New narrator — replaces the old _SCRIPT_PROMPT logic
from app.services.presentation.slide_narrator import generate_narration_scripts

logger = logging.getLogger(__name__)

_OUTPUT_BASE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "output", "presentations")
)

_transcription_service_instance: Optional[Any] = None

_LANGUAGE_NAMES = {
    "as": "Assamese", "bn": "Bengali", "en": "English", "es": "Spanish",
    "fr": "French", "de": "German", "gu": "Gujarati", "hi": "Hindi",
    "ja": "Japanese", "kn": "Kannada", "ml": "Malayalam", "mr": "Marathi",
    "ne": "Nepali", "or": "Odia", "pa": "Punjabi", "pt": "Portuguese",
    "ar": "Arabic", "ta": "Tamil", "te": "Telugu", "ur": "Urdu",
}


def _ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def _get_transcription_service():
    global _transcription_service_instance
    if _transcription_service_instance is None:
        logger.info("Whisper transcription service is disabled (legacy text_processing pipeline removed)")
        _transcription_service_instance = False
    return _transcription_service_instance


def _format_timestamp(seconds: float, *, srt: bool) -> str:
    total_ms = max(0, int(round((seconds or 0.0) * 1000)))
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, millis = divmod(rem, 1_000)
    sep = "," if srt else "."
    return f"{hours:02d}:{minutes:02d}:{secs:02d}{sep}{millis:03d}"


def _normalize_segments(raw_segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for seg in raw_segments or []:
        text = str(seg.get("text") or "").strip()
        if not text:
            continue
        try:
            start = max(0.0, float(seg.get("start", 0.0)))
            end = max(start, float(seg.get("end", start)))
        except (TypeError, ValueError):
            continue
        normalized.append({
            "start": round(start, 3),
            "end": round(end, 3),
            "text": text,
        })
    return normalized


def _write_subtitle_files(segments: List[Dict[str, Any]], output_dir: str) -> List[Dict[str, str]]:
    if not segments:
        return []

    _ensure_dir(output_dir)

    vtt_path = os.path.join(output_dir, "explainer_subtitles.vtt")
    srt_path = os.path.join(output_dir, "explainer_subtitles.srt")

    vtt_lines: List[str] = ["WEBVTT", ""]
    srt_lines: List[str] = []

    for idx, segment in enumerate(segments, start=1):
        start = float(segment["start"])
        end = float(segment["end"])
        text = segment["text"]

        vtt_lines.append(f"{_format_timestamp(start, srt=False)} --> {_format_timestamp(end, srt=False)}")
        vtt_lines.append(text)
        vtt_lines.append("")

        srt_lines.append(str(idx))
        srt_lines.append(f"{_format_timestamp(start, srt=True)} --> {_format_timestamp(end, srt=True)}")
        srt_lines.append(text)
        srt_lines.append("")

    with open(vtt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(vtt_lines).strip() + "\n")

    with open(srt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines).strip() + "\n")

    return [
        {"format": "vtt", "path": vtt_path},
        {"format": "srt", "path": srt_path},
    ]


async def transcribe_video_with_whisper(
    video_path: str,
    output_dir: str,
    language: Optional[str] = "en",
    on_progress: Optional[callable] = None,
) -> Dict[str, Any]:
    """Transcribe the final video with Whisper and export subtitle files."""
    try:
        if on_progress:
            await on_progress("transcribing", {"message": "Transcribing video with Whisper..."})

        service = _get_transcription_service()
        if not service:
            return {
                "status": "failed",
                "text": "",
                "language": language or "unknown",
                "segments": [],
                "subtitle_files": [],
                "error": "Transcription service is disabled",
            }
        raw_result = await asyncio.to_thread(
            service.transcribe_with_timestamps,
            file_path=video_path,
            language=language,
        )

        if raw_result.get("status") != "success":
            raise RuntimeError(raw_result.get("error") or "Whisper transcription failed")

        segments = _normalize_segments(raw_result.get("segments", []))
        subtitle_files = _write_subtitle_files(segments, output_dir)

        return {
            "status": "success",
            "text": str(raw_result.get("text") or "").strip(),
            "language": raw_result.get("language") or "unknown",
            "segments": segments,
            "subtitle_files": subtitle_files,
        }
    except Exception as exc:
        logger.warning("Whisper transcription failed for %s: %s", video_path, exc)
        return {
            "status": "failed",
            "text": "",
            "language": language or "unknown",
            "segments": [],
            "subtitle_files": [],
            "error": str(exc),
        }


# ── Script generation — now delegates to slide_narrator ───────────────────────

async def generate_slide_scripts(
    slides: List[Dict],
    narration_language: str = "en",
    narration_style: Optional[str] = None,
    narration_notes: Optional[str] = None,
    image_paths: Optional[List[Optional[str]]] = None,
    context_chunks: Optional[Dict[int, str]] = None,
    presentation_title: Optional[str] = None,
    use_vision: bool = True,
) -> List[str]:
    """
    Generate educator-quality narration scripts for all slides.

    Delegates to slide_narrator.generate_narration_scripts which provides:
    - Vision-augmented LLM calls (sends actual slide image if available)
    - RAG context injection per slide
    - Argument-role-aware rhetorical style
    - Parallel generation
    - Smart fallback chain
    """
    return await generate_narration_scripts(
        slides,
        image_paths=image_paths,
        context_chunks=context_chunks,
        narration_language=narration_language,
        narration_style=narration_style,
        narration_notes=narration_notes,
        presentation_title=presentation_title,
        use_vision=use_vision,
    )



# ── Audio generation ───────────────────────────────────────────────────────

async def generate_slide_audio(
    scripts: List[str],
    output_dir: str,
    voice_id: str,
) -> List[Dict]:
    """Generate TTS audio for each slide script.

    Returns list of dicts with 'path', 'duration_ms', 'index'.
    """
    _ensure_dir(output_dir)
    audio_results: List[Dict] = []

    for i, script in enumerate(scripts):
        audio_path = os.path.join(output_dir, f"slide_{i:03d}_audio.mp3")
        try:
            duration_ms = await synthesize_segment(
                text=script,
                voice_id=voice_id,
                output_path=audio_path,
            )
            audio_results.append({
                "index": i,
                "path": audio_path,
                "duration_ms": duration_ms,
            })
            logger.info("Audio generated for slide %d: %dms", i, duration_ms)
        except Exception as exc:
            logger.error("TTS failed for slide %d: %s", i, exc)
            audio_results.append({
                "index": i,
                "path": None,
                "duration_ms": 0,
                "error": str(exc),
            })

    return audio_results


# ── Video creation (ffmpeg) ────────────────────────────────────────────────

async def create_slide_video(
    image_path: str,
    audio_path: str,
    output_path: str,
) -> str:
    """Create a video segment from a single slide image + audio using ffmpeg.

    The video duration matches the audio duration.
    Returns the output path.
    """
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", image_path,
        "-i", audio_path,
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
        "-shortest",
        "-movflags", "+faststart",
        output_path,
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        error_msg = stderr.decode("utf-8", errors="replace")[-500:]
        raise RuntimeError(f"ffmpeg slide video failed (exit {proc.returncode}): {error_msg}")

    logger.info("Slide video created: %s", output_path)
    return output_path


async def merge_videos(
    video_paths: List[str],
    output_path: str,
) -> str:
    """Concatenate multiple slide videos into a single final video using ffmpeg concat demuxer.

    Returns the output path.
    """
    # Create a concat list file
    concat_file = output_path + ".concat.txt"
    try:
        with open(concat_file, "w") as f:
            for vp in video_paths:
                # ffmpeg concat demuxer requires escaped single quotes
                escaped = vp.replace("'", "'\\''")
                f.write(f"file '{escaped}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            "-movflags", "+faststart",
            output_path,
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            error_msg = stderr.decode("utf-8", errors="replace")[-500:]
            raise RuntimeError(f"ffmpeg merge failed (exit {proc.returncode}): {error_msg}")

        logger.info("Final video merged: %s (%d segments)", output_path, len(video_paths))
        return output_path

    finally:
        # Clean up concat file
        try:
            os.unlink(concat_file)
        except OSError:
            pass


# ── Full video pipeline ────────────────────────────────────────────────────

async def generate_explainer_video(
    slides: List[Dict],
    image_paths: List[str],
    output_dir: str,
    voice_id: str,
    narration_language: str = "en",
    narration_style: Optional[str] = None,
    narration_notes: Optional[str] = None,
    on_progress: Optional[callable] = None,
    presentation_title: Optional[str] = None,
    context_chunks: Optional[Dict[int, str]] = None,
    use_vision: bool = True,
) -> Dict:
    """Full pipeline: scripts → audio → individual videos → merged video → whisper transcription.

    Args:
        slides: Slide specs with title/bullets/argument_role.
        image_paths: Paths to slide images (same order) — fed to vision LLM for richer narration.
        output_dir: Directory for intermediate and final output files.
        voice_id: TTS voice to use.
        narration_language: Language code for script + transcription.
        narration_style: Narration style: teacher | storyteller | expert_analyst | conversational | professional
        narration_notes: Additional per-session instructor notes.
        presentation_title: Used in the deck outline narration header.
        context_chunks: Optional dict mapping slide_index → RAG source text for grounded narration.
        use_vision: Whether to send slide images to the vision LLM (default True).
        on_progress: Async callback(stage, detail_dict) for progress updates.

    Returns:
        Dict with 'video_path', 'duration_ms', 'scripts', 'audio_files', 'transcription'.
    """
    _ensure_dir(output_dir)

    # Step 1: Generate scripts (vision-augmented, parallel, RAG-grounded)
    if on_progress:
        await on_progress("scripting", {
            "message": "Generating AI narration scripts...",
            "vision": use_vision,
        })

    scripts = await generate_slide_scripts(
        slides,
        narration_language=narration_language,
        narration_style=narration_style,
        narration_notes=narration_notes,
        image_paths=image_paths if use_vision else None,
        context_chunks=context_chunks,
        presentation_title=presentation_title,
        use_vision=use_vision,
    )

    if on_progress:
        await on_progress("script_done", {"message": "Scripts ready", "count": len(scripts)})

    # Step 2: Generate audio
    if on_progress:
        await on_progress("audio", {"message": "Generating narration audio..."})
    audio_results = await generate_slide_audio(scripts, output_dir, voice_id)

    if on_progress:
        await on_progress("audio_done", {"message": "Audio ready", "count": len(audio_results)})

    # Step 3: Create individual slide videos
    if on_progress:
        await on_progress("rendering", {"message": "Composing slide videos..."})

    slide_video_paths: List[str] = []
    for i, (img_path, audio_info) in enumerate(zip(image_paths, audio_results)):
        if not audio_info.get("path") or not os.path.isfile(img_path):
            logger.warning("Skipping slide %d: missing image or audio", i)
            continue

        video_path = os.path.join(output_dir, f"slide_{i:03d}_video.mp4")
        try:
            await create_slide_video(img_path, audio_info["path"], video_path)
            slide_video_paths.append(video_path)
        except Exception as exc:
            logger.error("Failed to create video for slide %d: %s", i, exc)

    if not slide_video_paths:
        raise RuntimeError("No slide videos were created successfully")

    # Step 4: Merge into final video
    if on_progress:
        await on_progress("merging", {"message": "Merging final video..."})

    final_path = os.path.join(output_dir, "final_explainer.mp4")
    await merge_videos(slide_video_paths, final_path)

    # Step 5: Whisper transcription + subtitle files
    transcription = await transcribe_video_with_whisper(
        video_path=final_path,
        output_dir=output_dir,
        language=narration_language,
        on_progress=on_progress,
    )

    total_duration = sum(a.get("duration_ms", 0) for a in audio_results if a.get("path"))

    if on_progress:
        await on_progress(
            "done",
            {
                "message": "Video complete!",
                "duration_ms": total_duration,
                "transcript_segments": len(transcription.get("segments", [])),
            },
        )

    return {
        "video_path": final_path,
        "duration_ms": total_duration,
        "scripts": scripts,
        "audio_files": [a for a in audio_results if a.get("path")],
        "transcription": transcription,
    }


