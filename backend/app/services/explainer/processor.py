from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from functools import partial
from typing import Any

from app.db.prisma_client import prisma
from app.services.explainer.script_generator import generate_slide_scripts_async
from app.services.explainer.tts import generate_audio_file, get_audio_duration
from app.services.explainer.video_composer import compose_slide_video, concatenate_videos
from app.services.ppt.screenshot_service import ScreenshotService

logger = logging.getLogger("explainer.processor")

EXPLAINER_OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "data", "output", "explainers",
)

async def _update_status(explainer_id: str, status: str, **extra_fields) -> None:
    data: dict[str, Any] = {"status": status}
    for key, val in extra_fields.items():
        if key in ("script", "audioFiles", "chapters") and val is not None:
            data[key] = json.dumps(val)
        else:
            data[key] = val
    try:
        await prisma.explainervideo.update(
            where={"id": explainer_id},
            data=data,
        )
        logger.info("Explainer %s status → %s", explainer_id, status)
    except Exception as exc:
        logger.error("Failed to update explainer status: %s", exc)

def _extract_slides_from_presentation(presentation_data: dict) -> list[dict]:
    slides_raw = presentation_data.get("slides", [])
    slides = []

    for idx, slide in enumerate(slides_raw):
        title = slide.get("title", f"Slide {idx + 1}")
        content_parts = []
        if slide.get("bullets"):
            if isinstance(slide["bullets"], list):
                content_parts.extend(slide["bullets"])
            else:
                content_parts.append(str(slide["bullets"]))
        if slide.get("notes"):
            content_parts.append(str(slide["notes"]))
        if slide.get("content"):
            if isinstance(slide["content"], list):
                content_parts.extend(slide["content"])
            else:
                content_parts.append(str(slide["content"]))
        if not content_parts:
            content_parts.append(title)

        slides.append({
            "slide_number": idx + 1,
            "title": title,
            "content": "\n".join(content_parts),
            "html": slide.get("html", ""),
        })

    return slides

async def process_explainer_video(
    explainer_id: str,
    presentation_data: dict,
    presentation_html: str,
    narration_language: str,
    voice_gender: str,
    voice_id: str,
    user_id: str,
    notebook_id: str,
    material_ids: list[str],
    slide_count: int,
) -> None:
    work_dir = os.path.join(EXPLAINER_OUTPUT_DIR, explainer_id)
    os.makedirs(work_dir, exist_ok=True)
    t_start = time.time()

    try:
        slides = _extract_slides_from_presentation(presentation_data)
        if not slides:
            raise ValueError("No slides found in presentation data")

        logger.info(
            "Explainer %s: %d slides extracted, starting pipeline",
            explainer_id, len(slides),
        )

        await _update_status(explainer_id, "capturing_slides")
        screenshot_svc = ScreenshotService()
        slide_images = await screenshot_svc.capture_slides(
            html_content=presentation_html,
            user_id=user_id,
            presentation_id=f"explainer_{explainer_id}",
            slide_count=len(slides),
        )

        image_paths: dict[int, str] = {}
        for img_data in slide_images:
            snum = img_data.get("slide_number", 0)
            fpath = img_data.get("file_path", "")
            if snum and fpath and os.path.exists(fpath):
                image_paths[snum] = fpath

        if not image_paths:
            logger.warning("No slide images captured — using placeholder images")
            for s in slides:
                placeholder = os.path.join(work_dir, f"slide_{s['slide_number']}.png")
                _create_placeholder_image(placeholder, s["title"])
                image_paths[s["slide_number"]] = placeholder

        await _update_status(explainer_id, "generating_script")

        scripts = await generate_slide_scripts_async(slides, narration_language, max_concurrent=3)

        await _update_status(
            explainer_id, "generating_script",
            script={"slides": [s for s in scripts]},
        )

        await _update_status(explainer_id, "generating_audio")

        async def generate_single_audio(script: dict) -> tuple[str, float]:
            slide_num = script["slide_number"]
            audio_path = os.path.join(work_dir, f"slide_{slide_num}.mp3")
            await generate_audio_file(
                text=script["script"],
                voice_id=voice_id,
                output_path=audio_path,
            )
            duration = get_audio_duration(audio_path)
            logger.info("Audio for slide %d: %.1fs", slide_num, duration)
            return audio_path, duration

        audio_tasks = [generate_single_audio(script) for script in scripts]
        audio_results = await asyncio.gather(*audio_tasks)
        
        audio_paths = [r[0] for r in audio_results]
        audio_durations = [r[1] for r in audio_results]

        await _update_status(
            explainer_id, "generating_audio",
            audioFiles=[{"slide": i + 1, "path": p, "duration": d}
                        for i, (p, d) in enumerate(zip(audio_paths, audio_durations))],
        )

        await _update_status(explainer_id, "composing_video")

        loop = asyncio.get_running_loop()

        async def compose_single_video(idx: int, script: dict) -> tuple[int, str | None]:
            slide_num = script["slide_number"]
            img_path = image_paths.get(slide_num)
            if not img_path:
                logger.warning("No image for slide %d, skipping", slide_num)
                return slide_num, None

            audio_path = os.path.join(work_dir, f"slide_{slide_num}.mp3")
            video_path = os.path.join(work_dir, f"slide_{slide_num}.mp4")
            duration = audio_durations[idx]

            await loop.run_in_executor(
                None,
                partial(compose_slide_video, img_path, audio_path, video_path, duration),
            )
            return slide_num, video_path

        video_tasks = [compose_single_video(i, script) for i, script in enumerate(scripts)]
        video_results = await asyncio.gather(*video_tasks)
        
        slide_videos = [
            path for _, path in sorted(video_results, key=lambda x: x[0])
            if path is not None
        ]

        if not slide_videos:
            raise ValueError("No slide videos were produced")

        final_path = os.path.join(work_dir, "explainer_final.mp4")
        await loop.run_in_executor(
            None,
            partial(concatenate_videos, slide_videos, final_path),
        )

        chapters = []
        cumulative_time = 0.0
        for i, (script, duration) in enumerate(zip(scripts, audio_durations)):
            chapters.append({
                "slide_number": i + 1,
                "title": script["title"],
                "start_time": round(cumulative_time, 1),
                "duration": round(duration, 1),
            })
            cumulative_time += duration

        total_duration = int(cumulative_time)

        video_url = f"/explainer/{explainer_id}/video"

        await prisma.explainervideo.update(
            where={"id": explainer_id},
            data={
                "status": "completed",
                "videoUrl": video_url,
                "duration": total_duration,
                "chapters": json.dumps(chapters),
                "completedAt": datetime.now(timezone.utc),
            },
        )

        title = presentation_data.get("title", "Explainer Video")
        content_data = {
            "explainer_id": explainer_id,
            "video_url": video_url,
            "duration": total_duration,
            "chapters": chapters,
            "slide_count": len(slides),
            "narration_language": narration_language,
        }
        gen_content_data = {
            "notebookId": notebook_id,
            "userId": user_id,
            "contentType": "explainer",
            "title": f"Explainer: {title}",
            "data": json.dumps(content_data),
            "language": narration_language,
            "materialIds": material_ids,
        }
        if len(material_ids) == 1:
            gen_content_data["materialId"] = material_ids[0]
        await prisma.generatedcontent.create(data=gen_content_data)

        elapsed = time.time() - t_start
        logger.info(
            "Explainer %s COMPLETED in %.1fs — %d slides, %ds video",
            explainer_id, elapsed, len(slides), total_duration,
        )

    except Exception as exc:
        logger.error("Explainer %s FAILED: %s", explainer_id, exc, exc_info=True)
        await _update_status(explainer_id, "failed", error=str(exc))

def _create_placeholder_image(path: str, title: str) -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGB", (1920, 1080), color=(30, 30, 30))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 48)
        except (OSError, IOError):
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), title, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = (1920 - tw) // 2
        y = (1080 - th) // 2
        draw.text((x, y), title, fill=(255, 255, 255), font=font)
        img.save(path, "PNG")
    except ImportError:
        import struct
        import zlib

        def _minimal_png():
            raw = b"\x00\x00\x00\x00"
            compressed = zlib.compress(raw)
            sig = b"\x89PNG\r\n\x1a\n"
            ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
            ihdr_chunk = _chunk(b"IHDR", ihdr)
            idat_chunk = _chunk(b"IDAT", compressed)
            iend_chunk = _chunk(b"IEND", b"")
            return sig + ihdr_chunk + idat_chunk + iend_chunk

        def _chunk(chunk_type, data):
            raw = chunk_type + data
            return struct.pack(">I", len(data)) + raw + struct.pack(">I", zlib.crc32(raw) & 0xffffffff)

        with open(path, "wb") as f:
            f.write(_minimal_png())
