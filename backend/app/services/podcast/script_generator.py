from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Dict, List, Optional

from app.db.prisma_client import prisma
from app.prompts import get_podcast_script_prompt
from app.services.llm_service.llm import get_llm
from app.services.podcast.voice_map import LANGUAGE_NAMES

logger = logging.getLogger(__name__)


def _normalize_speaker(raw_speaker: object) -> str:
    token = str(raw_speaker or "").strip().lower()
    if not token:
        return ""

    # Common aliases seen in LLM outputs.
    if token in {"host", "anchor", "moderator", "narrator", "speaker1", "speaker 1", "alex"}:
        return "host"
    if token in {"guest", "expert", "speaker2", "speaker 2", "guest1", "guest 1"}:
        return "guest"

    if "host" in token or "speaker 1" in token or "speaker1" in token:
        return "host"
    if "guest" in token or "speaker 2" in token or "speaker2" in token:
        return "guest"

    return ""


def _ensure_dual_speakers(segments: List[Dict]) -> None:
    if len(segments) < 2:
        if segments:
            segments[0]["speaker"] = "host"
        return

    speakers = {str(seg.get("speaker", "")).lower() for seg in segments}
    if {"host", "guest"}.issubset(speakers):
        return

    # If model returns a monologue, force alternating dialogue.
    for i, seg in enumerate(segments):
        seg["speaker"] = "host" if i % 2 == 0 else "guest"

_MODE_QUERIES: Dict[str, List[str]] = {
    "overview": [
        "Comprehensive overview of all key topics, concepts, and findings",
        "Summary of main conclusions and takeaways",
    ],
    "deep-dive": [
        "Detailed technical explanation of core concepts and mechanisms",
        "Advanced details, edge cases, and nuanced analysis",
    ],
    "debate": [
        "Arguments for and against the main claims",
        "Counterarguments, criticisms, and alternative perspectives",
    ],
    "q-and-a": [
        "Frequently asked questions and their answers",
        "Common misconceptions and clarifications",
    ],
    "full": [
        "Comprehensive overview of all key topics, concepts, and findings",
        "Detailed analysis and supporting evidence",
    ],
    "topic": [],
}

def _extract_json(text: str) -> dict:
    """Robust JSON extraction from LLM response text."""
    text = text.strip()

    # 1. Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Try extraction from markdown blocks
    for pattern in (
        r"```json\s*\n?([\s\S]*?)\n?```",
        r"```\s*\n?([\s\S]*?)\n?```",
    ):
        m = re.search(pattern, text, re.DOTALL)
        if m:
            content = m.group(1).strip()
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # Try cleaning common JSON errors in the content
                cleaned = re.sub(r",\s*([}\]])", r"\1", content)
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    pass

    # 3. Try finding the first '{' and last '}'
    m = re.search(r"(\{[\s\S]*\})", text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            # Try cleaning common JSON errors in the match
            cleaned = re.sub(r",\s*([}\]])", r"\1", m.group(1))
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

    # 4. Final attempt: cleanup and global trailing comma removal
    candidate = re.sub(r",\s*([}\]])", r"\1", text)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    logger.error("Failed to extract JSON from LLM response. Raw text length: %d. Head: %r", len(text), text[:500])
    raise ValueError(
        f"Could not extract valid JSON from LLM response "
        f"({len(text)} chars). See logs for full output."
    )

async def _load_material_context(
    user_id: str,
    material_ids: List[str],
    notebook_id: Optional[str],
    *,
    max_chars: int = 24_000,
) -> str:
    where: Dict[str, object] = {"userId": str(user_id)}
    ids = [str(mid) for mid in (material_ids or []) if str(mid).strip()]
    if ids:
        where["id"] = {"in": ids}
    elif notebook_id:
        where["notebookId"] = str(notebook_id)
    else:
        return ""

    materials = await prisma.material.find_many(where=where, order={"createdAt": "asc"})
    blocks: List[str] = []
    used = 0

    for material in materials:
        text = str(getattr(material, "originalText", "") or "").strip()
        if not text:
            continue
        title = str(getattr(material, "title", None) or getattr(material, "filename", None) or material.id)
        block = f"[SOURCE - Material: {title}]\n{text[:6000]}"
        if used + len(block) > max_chars:
            remaining = max_chars - used
            if remaining > 128:
                block = block[:remaining]
                blocks.append(block)
            break
        blocks.append(block)
        used += len(block)

    return "\n\n".join(blocks)

async def _gather_context(
    user_id: str,
    queries: List[str],
    material_ids: List[str],
    notebook_filter: Optional[str],
) -> str:
    del queries
    return await _load_material_context(user_id, material_ids, notebook_filter)

async def generate_podcast_script(
    user_id: str,
    material_ids: List[str],
    mode: str = "full",
    topic: Optional[str] = None,
    language: str = "en",
    notebook_id: Optional[str] = None,
) -> Dict:
    logger.info(
        "Generating podcast script: mode=%s language=%s materials=%d",
        mode, language, len(material_ids),
    )

    if mode == "topic" and topic:
        queries = [
            f'Detailed information about: "{topic}"',
            f'Background context and supporting details for: "{topic}"',
        ]
    else:
        queries = _MODE_QUERIES.get(mode, _MODE_QUERIES["overview"])

    notebook_filter = notebook_id if not material_ids else None

    context = await _gather_context(user_id, queries, material_ids, notebook_filter)

    if not context:
        logger.warning("No source text available for podcast context")
        raise ValueError("No relevant content found in the selected materials.")

    logger.info("Context gathered: %d chars from %d query angles", len(context), len(queries))

    language_name = LANGUAGE_NAMES.get(language, "English")
    mode_instruction = (
        f'Focus specifically on: "{topic}". Only cover content related to this topic.'
        if mode == "topic" and topic
        else {
            "overview":  "Cover all major topics and concepts comprehensively but accessibly.",
            "deep-dive": "Provide in-depth technical analysis; do not oversimplify.",
            "debate":    "Present contrasting viewpoints; host challenges, guest defends.",
            "q-and-a":   "Host asks questions, guest answers clearly and precisely.",
            "full":      "Cover everything — breadth and depth — in a long-form episode.",
        }.get(mode, "Cover all major topics and concepts from the source material comprehensively.")
    )

    prompt = get_podcast_script_prompt(
        language=language_name,
        mode_instruction=mode_instruction,
        context=context,
    )

    llm = get_llm(mode="creative", max_tokens=12000)
    response = await asyncio.to_thread(llm.invoke, prompt)

    response_text = response.content if hasattr(response, "content") else str(response)
    logger.info("Script LLM response: %d chars", len(response_text))

    result = _extract_json(response_text)

    segments: List[Dict] = result.get("segments", [])
    if not segments:
        raise ValueError("LLM returned empty segments list")

    for i, seg in enumerate(segments):
        seg["segment_index"] = i
        # Map 'content' to 'text' for TTS compatibility if LLM used 'content'
        if "content" in seg and "text" not in seg:
            seg["text"] = seg["content"]

        normalized_speaker = _normalize_speaker(seg.get("speaker"))
        if normalized_speaker:
            seg["speaker"] = normalized_speaker
        else:
            seg["speaker"] = "host" if i % 2 == 0 else "guest"

    _ensure_dual_speakers(segments)

    raw_chapters: List[Dict] = result.get("chapters", [{"name": "Full Episode", "start_segment": 0}])
    chapters: List[Dict] = [
        {
            "title": ch.get("title") or ch.get("name", f"Chapter {i + 1}"),
            "startSegment": ch.get("startSegment", ch.get("start_segment", 0)),
            "summary": ch.get("summary", ""),
        }
        for i, ch in enumerate(raw_chapters)
    ]
    title: str = result.get("title", "AI Podcast")

    logger.info(
        "Script generated: %d segments, %d chapters, title=%r",
        len(segments), len(chapters), title,
    )

    return {"segments": segments, "chapters": chapters, "title": title}
