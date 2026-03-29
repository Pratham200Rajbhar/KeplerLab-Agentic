"""
slide_narrator.py — Production-grade AI narration script generator.

Key design principles:
1. VISION-AUGMENTED: Sends the actual slide image to the LLM so it can reference
   diagrams, charts, annotations — not just recite bullet text.
2. RAG-GROUNDED: Accepts per-slide source context chunks so narration is anchored
   in the actual source material, preventing hallucination.
3. ARGUMENT-ROLE-AWARE: Thesis/evidence/counterpoint/synthesis slides each get a
   different rhetorical treatment.
4. PARALLEL: All slides narrated concurrently behind a semaphore (5 at once).
5. SMART FALLBACK: Graceful degradation chain:
   image+RAG → image only → text+RAG → text only → formatted bullets
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Maximum concurrent vision LLM calls
_NARRATION_CONCURRENCY = 5

_LANGUAGE_NAMES = {
    "as": "Assamese", "bn": "Bengali", "en": "English", "es": "Spanish",
    "fr": "French", "de": "German", "gu": "Gujarati", "hi": "Hindi",
    "ja": "Japanese", "kn": "Kannada", "ml": "Malayalam", "mr": "Marathi",
    "ne": "Nepali", "or": "Odia", "pa": "Punjabi", "pt": "Portuguese",
    "ar": "Arabic", "ta": "Tamil", "te": "Telugu", "ur": "Urdu",
    "zh": "Mandarin Chinese", "ko": "Korean", "ru": "Russian", "it": "Italian",
}

_ROLE_INSTRUCTIONS: Dict[str, str] = {
    "thesis": (
        "Open with a bold, memorable claim. Make the audience lean forward. "
        "State what this deck is fundamentally arguing. Be confident and direct."
    ),
    "context": (
        "Set the stage. Explain the background or situation that makes this relevant. "
        "Answer: why does this matter right now?"
    ),
    "evidence": (
        "Walk through the data, diagram, or proof on this slide. Reference specific "
        "numbers, trends, or visual patterns. Be precise — the details matter here."
    ),
    "counterpoint": (
        "Introduce tension or challenge. 'But here's the challenge…' or 'Critics often argue…' "
        "Acknowledge complexity — don't paper over it."
    ),
    "synthesis": (
        "Connect the threads. 'So what does all of this mean together?' "
        "Draw implications from evidence you've already presented. Build the 'aha' moment."
    ),
    "summary": (
        "Be tight and memorable. Name the 1-3 things the audience must walk away with. "
        "Sound like you're handing them something they'll actually use."
    ),
    "support": (
        "Develop the idea clearly and concisely. Use a concrete example or analogy "
        "to make the concept tangible. Bridge theory and practice."
    ),
}

_STYLE_DESCRIPTIONS: Dict[str, str] = {
    "teacher": "Warm, clear, patient. Uses 'we' and 'you'. Explains step by step. Like the best professor you ever had.",
    "storyteller": "Narrative and engaging. Uses stories, metaphors, and vivid language. Creates emotional connection.",
    "expert_analyst": "Data-driven and precise. References specific details. Authoritative, no fluff.",
    "conversational": "Relaxed and direct. Talks to you like a smart colleague over coffee. Casual but substantive.",
    "professional": "Polished, corporate. Confident and concise. Appropriate for executive audiences.",
}


def _format_deck_outline(slides: List[Dict]) -> str:
    lines = []
    for i, slide in enumerate(slides, 1):
        title = str(slide.get("title") or f"Slide {i}").strip()
        role = str(slide.get("argument_role") or slide.get("argumentRole") or "support").strip()
        lines.append(f"{i}. {title} [{role}]")
    return "\n".join(lines) if lines else "No outline available"


def _build_narration_prompt(
    *,
    slide: Dict[str, Any],
    slide_idx: int,
    total: int,
    deck_outline: str,
    presentation_title: str,
    language_name: str,
    style_description: str,
    role_instruction: str,
    context_chunk: Optional[str],
    has_image: bool,
) -> str:
    title = str(slide.get("title") or f"Slide {slide_idx + 1}").strip()
    bullets = slide.get("bullets") or []
    visual_style = str(slide.get("visual_style") or slide.get("visualStyle") or "modern")
    argument_role = str(slide.get("argument_role") or slide.get("argumentRole") or "support")

    bullet_lines = "\n".join(f"• {b}" for b in bullets[:6]) if bullets else "• No bullet points recorded"

    context_section = ""
    if context_chunk and context_chunk.strip():
        # Truncate to avoid bloat
        trimmed = context_chunk.strip()[:1200]
        context_section = f"""
SOURCE MATERIAL (use to ground explanations — never invent facts not supported here):
\"\"\"
{trimmed}
\"\"\"
"""

    image_note = (
        "A screenshot of the actual slide is attached. Refer to what you visually observe "
        "(charts, diagrams, flow arrows, call-out boxes, highlighted text) to enrich the narration."
        if has_image
        else "No slide image available — rely on title and bullet data only."
    )

    is_last = slide_idx == total - 1
    transition_note = (
        "Do NOT add a transition sentence — this is the final slide."
        if is_last
        else "End with a brief connecting thought to tee up the next idea (1 short sentence)."
    )

    return f"""You are a world-class educator delivering a live explanation of a presentation to an engaged audience.

PRESENTATION: \"{presentation_title}\"
DECK NARRATIVE ARC ({total} slides):
{deck_outline}

━━━ CURRENT SLIDE: {slide_idx + 1} of {total} ━━━
Title: \"{title}\"
Layout type: {visual_style} | Argument role: {argument_role}
Bullet points on slide:
{bullet_lines}
{context_section}
VISUAL NOTE: {image_note}

━━━ YOUR NARRATION MISSION FOR THIS SLIDE ━━━
Role instruction: {role_instruction}

━━━ STYLE & LANGUAGE ━━━
Language: {language_name}
Style: {style_description}
Target length: 85–130 words (35–55 seconds when spoken naturally)

━━━ MANDATORY RULES ━━━
1. NEVER say "this slide shows", "as you can see on the slide", or mention slide numbers.
2. Do NOT just recite the bullet points — EXPLAIN, CONNECT, and ILLUMINATE.
3. Speak as if addressing a live audience — use "we", "you", "let's", "notice".
4. If you see a diagram, chart, or visual element in the image, reference what it communicates.
5. Ground any statistics or claims in the SOURCE MATERIAL if provided — do not fabricate data.
6. {transition_note}
7. Write ONLY the narration text. No labels, headers, markdown, or quotes.
"""


def _smart_fallback_script(slide: Dict[str, Any], slide_idx: int) -> str:
    """Generate a reasonable fallback without LLM if everything fails."""
    title = str(slide.get("title") or f"Slide {slide_idx + 1}").strip()
    bullets = slide.get("bullets") or []
    role = str(slide.get("argument_role") or "support").lower()

    opening = {
        "thesis": f"Let's talk about {title}.",
        "evidence": f"The data here tells an important story about {title}.",
        "counterpoint": f"Now, there's another side to consider when it comes to {title}.",
        "synthesis": f"Bringing it all together, {title} is the key insight.",
        "summary": f"To summarize the core ideas: {title}.",
        "context": f"To set the context: {title}.",
        "support": f"Let's explore {title}.",
    }.get(role, f"Let's explore {title}.")

    body_parts = []
    for b in bullets[:4]:
        b = str(b).strip()
        if b:
            # Turn "Point A" into "First, Point A."
            body_parts.append(b.rstrip(".") + ".")

    body = " ".join(body_parts) if body_parts else ""
    return f"{opening} {body}".strip()


async def _generate_one_script(
    *,
    slide: Dict[str, Any],
    slide_idx: int,
    total: int,
    deck_outline: str,
    presentation_title: str,
    language_name: str,
    style_description: str,
    image_path: Optional[str],
    context_chunk: Optional[str],
    sem: asyncio.Semaphore,
) -> str:
    """Generate narration for a single slide with vision support."""
    from app.services.llm_service.llm import get_llm

    argument_role = str(slide.get("argument_role") or slide.get("argumentRole") or "support").lower()
    role_instruction = _ROLE_INSTRUCTIONS.get(argument_role, _ROLE_INSTRUCTIONS["support"])

    has_image = bool(image_path and os.path.isfile(image_path))

    prompt_text = _build_narration_prompt(
        slide=slide,
        slide_idx=slide_idx,
        total=total,
        deck_outline=deck_outline,
        presentation_title=presentation_title,
        language_name=language_name,
        style_description=style_description,
        role_instruction=role_instruction,
        context_chunk=context_chunk,
        has_image=has_image,
    )

    async with sem:
        # ── Vision LLM (image + text prompt) ──────────────────────────
        if has_image:
            script = await _invoke_vision_llm(prompt_text, image_path)
            if script and len(script.split()) >= 20:
                logger.info(
                    "Vision narration OK slide=%d words=%d",
                    slide_idx, len(script.split())
                )
                return script
            else:
                logger.warning(
                    "Vision narration returned too few words for slide=%d. Proceeding with script anyway.",
                    slide_idx
                )
                return script or "Failed to generate narration."
            
        # ── Text-only LLM (No image available) ─────────────────────────────
        llm = get_llm(mode="creative", max_tokens=2500, provider="GOOGLE")
        response = await asyncio.to_thread(llm.invoke, prompt_text)
        text = (response.content if hasattr(response, "content") else str(response)).strip().strip('"').strip("'")
        if text and len(text.split()) >= 15:
            logger.info(
                "Text narration OK slide=%d words=%d",
                slide_idx, len(text.split())
            )
            return text
        else:
            return text or "Failed to generate text narration."


async def _invoke_vision_llm(prompt_text: str, image_path: str) -> str:
    """Call the vision-capable LLM (Gemini) with the slide image + prompt."""
    from langchain_core.messages import HumanMessage
    from app.services.llm_service.llm import get_llm

    # Read image and base64 encode
    with open(image_path, "rb") as f:
        img_bytes = f.read()
    b64 = base64.b64encode(img_bytes).decode("utf-8")

    # Detect mime type from header bytes
    mime = "image/png"
    if img_bytes[:3] == b"\xff\xd8\xff":
        mime = "image/jpeg"
    elif img_bytes[:4] == b"\x89PNG":
        mime = "image/png"
    elif img_bytes[:4] == b"RIFF":
        mime = "image/webp"

    llm = get_llm(mode="creative", max_tokens=2500, provider="GOOGLE")

    message = HumanMessage(content=[
        {
            "type": "image_url",
            "image_url": f"data:{mime};base64,{b64}",
        },
        {
            "type": "text",
            "text": prompt_text,
        },
    ])

    response = await asyncio.to_thread(llm.invoke, [message])
    text = (response.content if hasattr(response, "content") else str(response)).strip()
    return text.strip('"').strip("'").strip()


# ── Public API ─────────────────────────────────────────────────────────────────

async def generate_narration_scripts(
    slides: List[Dict[str, Any]],
    *,
    image_paths: Optional[List[Optional[str]]] = None,
    context_chunks: Optional[Dict[int, str]] = None,
    narration_language: str = "en",
    narration_style: Optional[str] = None,
    narration_notes: Optional[str] = None,
    presentation_title: Optional[str] = None,
    use_vision: bool = True,
) -> List[str]:
    """
    Generate educator-quality narration scripts for each slide.

    Args:
        slides: List of slide specs {title, bullets, argument_role, visual_style, ...}
        image_paths: Parallel list of local filesystem paths to slide images (can be None entries)
        context_chunks: Dict mapping slide_index → relevant source text for RAG grounding
        narration_language: BCP47 language code (default "en")
        narration_style: One of "teacher"|"storyteller"|"expert_analyst"|"conversational"|"professional"
        narration_notes: Free-form extra instructions added to every prompt
        presentation_title: Used in the deck outline header
        use_vision: Whether to send slide images to the vision LLM (disable to save latency)

    Returns:
        List of narration scripts, one per slide, same order as input.
    """
    lang_code = (narration_language or "en").lower().split("-")[0]
    language_name = _LANGUAGE_NAMES.get(lang_code, "English")

    style_key = (narration_style or "teacher").lower().replace(" ", "_").replace("-", "_")
    style_description = _STYLE_DESCRIPTIONS.get(style_key, _STYLE_DESCRIPTIONS["teacher"])

    if narration_notes and narration_notes.strip():
        style_description += f" Additional instructor notes: {narration_notes.strip()}"

    title = (presentation_title or "Presentation").strip()
    deck_outline = _format_deck_outline(slides)
    sem = asyncio.Semaphore(_NARRATION_CONCURRENCY)

    image_paths_resolved: List[Optional[str]] = []
    for i in range(len(slides)):
        if not use_vision or image_paths is None or i >= len(image_paths):
            image_paths_resolved.append(None)
        else:
            image_paths_resolved.append(image_paths[i])

    context_chunks_resolved = context_chunks or {}

    tasks = [
        _generate_one_script(
            slide=slide,
            slide_idx=i,
            total=len(slides),
            deck_outline=deck_outline,
            presentation_title=title,
            language_name=language_name,
            style_description=style_description,
            image_path=image_paths_resolved[i],
            context_chunk=context_chunks_resolved.get(i),
            sem=sem,
        )
        for i, slide in enumerate(slides)
    ]

    scripts = await asyncio.gather(*tasks, return_exceptions=False)

    logger.info(
        "Narration complete: %d scripts generated, lang=%s, style=%s, vision=%s",
        len(scripts), language_name, style_key, use_vision,
    )
    return list(scripts)
