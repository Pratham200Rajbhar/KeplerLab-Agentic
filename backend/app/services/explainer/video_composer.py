from __future__ import annotations

import logging
import os
import subprocess

logger = logging.getLogger("explainer.video")

def compose_slide_video(
    image_path: str,
    audio_path: str,
    output_path: str,
    duration: float,
) -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

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
        "-t", str(duration + 0.1),
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:-1:-1:color=black",
        output_path,
    ]

    logger.info("Composing slide video: %s + %s → %s", image_path, audio_path, output_path)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        logger.error("ffmpeg slide composition failed: %s", result.stderr)
        raise RuntimeError(f"ffmpeg failed: {result.stderr[:500]}")

    logger.info("Slide video created: %s (%d bytes)", output_path, os.path.getsize(output_path))
    return output_path

def concatenate_videos(
    video_paths: list[str],
    output_path: str,
) -> str:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    concat_file = output_path + ".concat.txt"
    with open(concat_file, "w") as f:
        for vp in video_paths:
            f.write(f"file '{vp}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        output_path,
    ]

    logger.info("Concatenating %d videos → %s", len(video_paths), output_path)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    try:
        os.remove(concat_file)
    except OSError:
        pass

    if result.returncode != 0:
        logger.error("ffmpeg concatenation failed: %s", result.stderr)
        raise RuntimeError(f"ffmpeg concat failed: {result.stderr[:500]}")

    file_size = os.path.getsize(output_path)
    logger.info("Final video created: %s (%.1f MB)", output_path, file_size / 1024 / 1024)
    return output_path
