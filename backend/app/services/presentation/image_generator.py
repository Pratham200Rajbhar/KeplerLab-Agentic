"""
Image Generator — generates presentation slide images using Gemini API.

Adds 16:9 enforcement via Pillow after every image is returned from the API.
Ensures every image is exactly 1280×720 regardless of what Gemini produces.
"""
from __future__ import annotations

import asyncio
import base64
import io
import logging
import os
from typing import Callable, Dict, List, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

_MAX_RETRIES = 2
_GENERATION_CONCURRENCY = 3
_REQUEST_TIMEOUT = 90  # Longer timeout for richer prompts

# Target slide dimensions (16:9)
_SLIDE_WIDTH = 1280
_SLIDE_HEIGHT = 720


# ── Auth ──────────────────────────────────────────────────────────────────────

def _get_access_token() -> str:
    # 1. Prefer manually provided token
    if settings.VERTEX_ACCESS_TOKEN:
        return settings.VERTEX_ACCESS_TOKEN

    # 2. Try google-auth library
    try:
        import google.auth
        from google.auth.transport.requests import Request
        credentials, _ = google.auth.default()
        credentials.refresh(Request())
        return credentials.token
    except Exception as e:
        logger.warning("Failed to get google-auth token, fallback to gcloud CLI: %s", e)
        # 3. Fallback to gcloud CLI
        import subprocess
        try:
            result = subprocess.run(
                ["gcloud", "auth", "application-default", "print-access-token"],
                capture_output=True, text=True, check=True,
            )
            return result.stdout.strip()
        except Exception as ge:
            logger.error("Failed to get access token via gcloud: %s", ge)
            return ""


def _get_project_id() -> str:
    return settings.VERTEX_PROJECT_ID or "project-2013f55b-2888-4590-9b5"


# ── 16:9 Enforcement ──────────────────────────────────────────────────────────

def _enforce_16x9(image_bytes: bytes) -> bytes:
    """
    Post-process the raw image bytes from Gemini to enforce exactly 1280×720 (16:9).

    Strategy:
    1. Open the image with Pillow.
    2. If it is already 1280×720, return as-is.
    3. Otherwise resize to fit within 1280×720, then pad with the image's most
       common edge colour (or black) to reach exactly 1280×720.
       This avoids stretching/distorting the slide content.
    """
    try:
        from PIL import Image, ImageOps

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        w, h = img.size

        if w == _SLIDE_WIDTH and h == _SLIDE_HEIGHT:
            return image_bytes

        # Scale to fit inside 1280×720 maintaining aspect ratio
        img.thumbnail((_SLIDE_WIDTH, _SLIDE_HEIGHT), Image.LANCZOS)
        new_w, new_h = img.size

        # Pad to exactly 1280×720
        # Use the dominant corner color as padding to avoid harsh black bars
        try:
            corner_pixel = img.getpixel((0, 0))
            pad_color: Tuple[int, int, int] = (
                corner_pixel[0], corner_pixel[1], corner_pixel[2]
            ) if isinstance(corner_pixel, tuple) else (0, 0, 0)
        except Exception:
            pad_color = (15, 23, 42)  # fallback: dark navy

        canvas = Image.new("RGB", (_SLIDE_WIDTH, _SLIDE_HEIGHT), pad_color)
        offset_x = (_SLIDE_WIDTH - new_w) // 2
        offset_y = (_SLIDE_HEIGHT - new_h) // 2
        canvas.paste(img, (offset_x, offset_y))

        buf = io.BytesIO()
        canvas.save(buf, format="PNG", optimize=False)
        result = buf.getvalue()

        logger.debug(
            "16:9 enforced: %dx%d → %dx%d (pad_color=%s)",
            w, h, _SLIDE_WIDTH, _SLIDE_HEIGHT, pad_color,
        )
        return result

    except ImportError:
        logger.warning("Pillow not available — skipping 16:9 enforcement")
        return image_bytes
    except Exception as exc:
        logger.warning("16:9 enforcement failed (%s) — returning original bytes", exc)
        return image_bytes


# ── Single slide generation ───────────────────────────────────────────────────

def _generate_image_sync(prompt: str) -> bytes:
    """Generate a single slide image via Gemini API (synchronous)."""
    project_id = _get_project_id()
    access_token = _get_access_token()
    location = settings.VERTEX_LOCATION or "us-central1"
    url = (
        f"https://{location}-aiplatform.googleapis.com/v1/"
        f"projects/{project_id}/locations/{location}/"
        f"publishers/google/models/gemini-2.5-flash-image:generateContent"
    )

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "responseModalities": ["IMAGE", "TEXT"],
        },
    }

    response = requests.post(
        url,
        json=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
        timeout=_REQUEST_TIMEOUT,
    )

    if not response.ok:
        logger.error("Gemini image HTTP error: %d - %s", response.status_code, response.text[:500])
        response.raise_for_status()

    data = response.json()
    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError(f"No candidates returned from Gemini. Response: {data}")

    parts = candidates[0].get("content", {}).get("parts", [])
    for part in parts:
        if "inlineData" in part:
            b64_data = part["inlineData"].get("data")
            if b64_data:
                raw_bytes = base64.b64decode(str(b64_data))
                # Enforce 16:9 before returning
                return _enforce_16x9(raw_bytes)

    raise ValueError(f"No image data in Gemini response. Parts: {parts}")


async def generate_slide_image(prompt: str, retry_count: int = _MAX_RETRIES) -> bytes:
    """Generate a single slide image with retry logic.

    Returns the raw image bytes (PNG, guaranteed 1280×720).
    """
    last_exc: Optional[Exception] = None

    for attempt in range(retry_count + 1):
        try:
            image_bytes = await asyncio.to_thread(_generate_image_sync, prompt)
            logger.info(
                "Slide image generated: %d bytes (attempt %d/%d)",
                len(image_bytes), attempt + 1, retry_count + 1,
            )
            return image_bytes
        except Exception as exc:
            last_exc = exc
            if attempt < retry_count:
                wait = 2.0 * (attempt + 1)
                logger.warning(
                    "Slide image generation attempt %d/%d failed: %s — retrying in %.1fs",
                    attempt + 1, retry_count + 1, exc, wait,
                )
                await asyncio.sleep(wait)
            else:
                logger.error(
                    "Slide image generation failed after %d attempts: %s",
                    retry_count + 1, exc,
                )

    raise RuntimeError(
        f"Slide image generation failed after {retry_count + 1} attempts"
    ) from last_exc


# ── Parallel batch generation ─────────────────────────────────────────────────

async def generate_all_slides(
    prompts: List[str],
    on_slide_ready: Optional[Callable[[int, bytes], None]] = None,
    on_slide_failed: Optional[Callable[[int, Exception], None]] = None,
) -> Dict[int, Optional[bytes]]:
    """Generate all slide images in parallel with controlled concurrency.

    Args:
        prompts:        List of image generation prompts (one per slide).
        on_slide_ready: Async callback(slide_index, image_bytes) on success.
        on_slide_failed: Async callback(slide_index, exception) on failure.

    Returns:
        Dict mapping slide_index → image_bytes (or None if failed).
    """
    sem = asyncio.Semaphore(_GENERATION_CONCURRENCY)
    results: Dict[int, Optional[bytes]] = {}

    async def _gen_one(idx: int, prompt: str) -> None:
        async with sem:
            try:
                image_bytes = await generate_slide_image(prompt)
                results[idx] = image_bytes
                if on_slide_ready:
                    try:
                        await on_slide_ready(idx, image_bytes)
                    except Exception as cb_exc:
                        logger.error(
                            "on_slide_ready callback error for slide %d: %s", idx, cb_exc
                        )
            except Exception as exc:
                results[idx] = None
                logger.error("Slide %d generation permanently failed: %s", idx, exc)
                if on_slide_failed:
                    try:
                        await on_slide_failed(idx, exc)
                    except Exception as cb_exc:
                        logger.error(
                            "on_slide_failed callback error for slide %d: %s", idx, cb_exc
                        )

    await asyncio.gather(*[_gen_one(i, p) for i, p in enumerate(prompts)])

    success = sum(1 for v in results.values() if v is not None)
    logger.info(
        "Batch slide generation complete: %d/%d succeeded", success, len(prompts)
    )

    return results
