"""
Slide Planner — generates a structured slide plan AND a coherent color/typography
ThemeSpec from user materials via RAG + LLM.

Key changes:
- ThemeSpec TypedDict carries hex colors, font, and mood for the entire deck.
- _generate_deck_theme() runs in parallel with slide planning (no extra latency).
- When the user supplies a theme string it is parsed/refined by the LLM into ThemeSpec.
- generate_slide_plan() now returns (List[SlideSpec], ThemeSpec).
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple, TypedDict

from app.db.prisma_client import prisma
from app.services.llm_service.llm import get_llm

logger = logging.getLogger(__name__)


# ── TypedDicts ────────────────────────────────────────────────────────────────

class ThemeSpec(TypedDict):
    primary: str        # HEX — dominant background / brand colour
    secondary: str      # HEX — secondary / card background
    accent: str         # HEX — headings, highlights, CTA elements
    text: str           # HEX — body text on primary background
    muted: str          # HEX — sub-text, captions
    font_family: str    # e.g. "Inter", "Roboto", "Poppins", "Montserrat"
    mood: str           # e.g. "clean", "bold", "academic", "corporate", "vibrant"


class SlideSpec(TypedDict):
    title: str
    bullets: List[str]
    visual_style: str
    tone: str
    argument_role: str


# ── Constants ─────────────────────────────────────────────────────────────────

MAX_SLIDES = 25
MIN_SLIDES = 3
MAX_BULLETS = 5

_ARGUMENT_ROLE_VALUES = {
    "thesis",
    "context",
    "evidence",
    "counterpoint",
    "synthesis",
    "summary",
    "support",
}

# Fallback theme used when LLM theme generation fails
_DEFAULT_THEME: ThemeSpec = ThemeSpec(
    primary="#0f172a",
    secondary="#1e293b",
    accent="#38bdf8",
    text="#e2e8f0",
    muted="#94a3b8",
    font_family="Inter",
    mood="clean",
)

# Preset themes mapped to mood keywords so freeform user strings can be matched
_PRESET_THEMES: Dict[str, ThemeSpec] = {
    "modern": ThemeSpec(
        primary="#0f172a", secondary="#1e293b", accent="#38bdf8",
        text="#e2e8f0", muted="#94a3b8", font_family="Inter", mood="clean",
    ),
    "academic": ThemeSpec(
        primary="#1a1a2e", secondary="#16213e", accent="#e94560",
        text="#eaeaea", muted="#a8a8b3", font_family="Roboto", mood="academic",
    ),
    "corporate": ThemeSpec(
        primary="#003566", secondary="#001d3d", accent="#ffd60a",
        text="#ffffff", muted="#b0c4d8", font_family="Montserrat", mood="corporate",
    ),
    "minimal": ThemeSpec(
        primary="#ffffff", secondary="#f8fafc", accent="#6366f1",
        text="#1e293b", muted="#64748b", font_family="Inter", mood="clean",
    ),
    "bold": ThemeSpec(
        primary="#10002b", secondary="#240046", accent="#ff6b6b",
        text="#ffffff", muted="#c77dff", font_family="Poppins", mood="vibrant",
    ),
    "dark": ThemeSpec(
        primary="#121212", secondary="#1e1e1e", accent="#bb86fc",
        text="#e1e1e1", muted="#9e9e9e", font_family="Inter", mood="clean",
    ),
    "warm": ThemeSpec(
        primary="#2d1b00", secondary="#3d2200", accent="#f4a261",
        text="#fef3c7", muted="#d4a76a", font_family="Merriweather Sans", mood="warm",
    ),
    "green": ThemeSpec(
        primary="#0d2818", secondary="#1a3a28", accent="#34d399",
        text="#d1fae5", muted="#6ee7b7", font_family="Roboto", mood="corporate",
    ),
}


# ── RAG helpers ───────────────────────────────────────────────────────────────

async def _load_material_context(
    user_id: str,
    material_ids: List[str],
    notebook_id: Optional[str],
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
    total = 0
    for material in materials:
        text = str(getattr(material, "originalText", "") or "").strip()
        if not text:
            continue
        title = str(getattr(material, "title", None) or getattr(material, "filename", None) or material.id)
        block = f"[SOURCE - Material: {title}]\n{text[:7000]}"
        if total + len(block) > 30_000:
            remaining = 30_000 - total
            if remaining > 128:
                blocks.append(block[:remaining])
            break
        blocks.append(block)
        total += len(block)

    return "\n\n".join(blocks)


async def _gather_context(
    user_id: str,
    material_ids: List[str],
    notebook_id: Optional[str],
    topic: Optional[str] = None,
) -> str:
    del topic
    return await _load_material_context(user_id, material_ids, notebook_id)


# ── JSON extraction ───────────────────────────────────────────────────────────

def _extract_json_array(text: str) -> List[Dict]:
    """Extract a JSON array from potentially markdown-wrapped LLM output."""
    text = text.strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "slides" in parsed:
            return parsed["slides"]
    except json.JSONDecodeError:
        pass

    for pattern in (
        r"```json\s*\n?([\s\S]*?)\n?```",
        r"```\s*\n?([\s\S]*?)\n?```",
    ):
        m = re.search(pattern, text, re.DOTALL)
        if m:
            content = m.group(1).strip()
            try:
                parsed = json.loads(content)
                if isinstance(parsed, list):
                    return parsed
                if isinstance(parsed, dict) and "slides" in parsed:
                    return parsed["slides"]
            except json.JSONDecodeError:
                cleaned = re.sub(r",\s*([}\]])", r"\1", content)
                try:
                    parsed = json.loads(cleaned)
                    if isinstance(parsed, list):
                        return parsed
                except json.JSONDecodeError:
                    pass

    m = re.search(r"(\[[\s\S]*\])", text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            cleaned = re.sub(r",\s*([}\]])", r"\1", m.group(1))
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

    raise ValueError(f"Could not extract JSON slide plan from LLM response ({len(text)} chars)")


def _extract_json_object(text: str) -> Dict[str, Any]:
    """Extract a JSON object from LLM output."""
    text = text.strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    for pattern in (
        r"```json\s*\n?([\s\S]*?)\n?```",
        r"```\s*\n?([\s\S]*?)\n?```",
    ):
        m = re.search(pattern, text, re.DOTALL)
        if m:
            content = m.group(1).strip()
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                cleaned = re.sub(r",\s*([}\]])", r"\1", content)
                try:
                    return json.loads(cleaned)
                except json.JSONDecodeError:
                    pass

    m = re.search(r"(\{[\s\S]*\})", text)
    if m:
        try:
            parsed = json.loads(m.group(1))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            cleaned = re.sub(r",\s*([}\]])", r"\1", m.group(1))
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                pass

    return {}


# ── Validation ────────────────────────────────────────────────────────────────

def _validate_slides(raw_slides: List[Dict]) -> List[SlideSpec]:
    """Validate and normalise LLM output into a clean list of SlideSpec."""
    valid: List[SlideSpec] = []

    for slide in raw_slides[:MAX_SLIDES]:
        title = str(slide.get("title", "")).strip()
        if not title:
            continue

        bullets = slide.get("bullets", slide.get("points", slide.get("content", [])))
        if isinstance(bullets, str):
            bullets = [b.strip() for b in bullets.split("\n") if b.strip()]
        if not isinstance(bullets, list):
            bullets = [str(bullets)]
        bullets = [str(b).strip() for b in bullets if str(b).strip()][:MAX_BULLETS]

        visual_style = str(slide.get("visual_style", slide.get("style", "modern"))).strip().lower()
        if visual_style not in ("diagram", "minimal", "modern", "chart", "timeline"):
            visual_style = "modern"

        tone = str(slide.get("tone", "educational")).strip().lower()
        argument_role = str(
            slide.get("argument_role", slide.get("argumentRole", "support"))
        ).strip().lower()
        if argument_role not in _ARGUMENT_ROLE_VALUES:
            argument_role = "support"

        valid.append(SlideSpec(
            title=title,
            bullets=bullets if bullets else ["Key point"],
            visual_style=visual_style,
            tone=tone,
            argument_role=argument_role,
        ))

    if len(valid) < MIN_SLIDES:
        raise ValueError(f"Slide plan has only {len(valid)} valid slides (minimum {MIN_SLIDES})")

    return valid


def _validate_hex(value: Any, fallback: str) -> str:
    """Ensure a value is a valid 6-digit hex colour."""
    if not isinstance(value, str):
        return fallback
    v = value.strip()
    if not v.startswith("#"):
        v = "#" + v
    if re.fullmatch(r"#[0-9a-fA-F]{6}", v):
        return v
    return fallback


def _validate_theme(raw: Dict[str, Any]) -> ThemeSpec:
    """Validate and coerce LLM-generated theme fields into ThemeSpec."""
    d = _DEFAULT_THEME.copy()
    d["primary"] = _validate_hex(raw.get("primary"), d["primary"])
    d["secondary"] = _validate_hex(raw.get("secondary"), d["secondary"])
    d["accent"] = _validate_hex(raw.get("accent"), d["accent"])
    d["text"] = _validate_hex(raw.get("text"), d["text"])
    d["muted"] = _validate_hex(raw.get("muted"), d["muted"])

    font = str(raw.get("font_family") or raw.get("font") or "Inter").strip()
    allowed_fonts = {
        "Inter", "Roboto", "Poppins", "Montserrat", "Outfit", "Raleway",
        "Lato", "Nunito", "Open Sans", "Source Sans Pro", "Merriweather Sans",
    }
    d["font_family"] = font if font in allowed_fonts else "Inter"

    mood = str(raw.get("mood") or "clean").strip().lower()
    d["mood"] = mood if mood in {"clean", "bold", "academic", "corporate", "vibrant", "warm"} else "clean"

    return ThemeSpec(**d)


# ── Theme matching from user prompt ──────────────────────────────────────────

def _quick_theme_from_keyword(user_theme: str) -> Optional[ThemeSpec]:
    """Try to match a user's freeform theme string to a preset quickly."""
    lowered = user_theme.lower()
    for key, spec in _PRESET_THEMES.items():
        if key in lowered:
            return spec
    return None


# ── LLM-based theme generation ────────────────────────────────────────────────

_THEME_GENERATION_PROMPT = """\
You are an expert presentation designer specialising in slide deck color systems.

TASK: Design a professional, cohesive color palette for a 16:9 presentation slide deck.

PRESENTATION TOPIC: {topic}
CONTENT DOMAIN: {domain_hint}
USER THEME HINT: {user_theme_hint}

RULES:
- Choose colors that work together harmoniously on a 16:9 digital slide.
- Ensure WCAG AA contrast between `text` and `primary`, and between `accent` and `primary`.
- Prefer dark backgrounds for data-heavy content; light backgrounds for clean academic work.
- The accent color should pop visually and be used for headings and important highlights.
- Select a professional sans-serif font from this list only:
  Inter, Roboto, Poppins, Montserrat, Outfit, Lato, Nunito, Open Sans, Raleway

Return ONLY a JSON object with exactly these keys (no explanation, no markdown):
{{
  "primary": "#xxxxxx",
  "secondary": "#xxxxxx",
  "accent": "#xxxxxx",
  "text": "#xxxxxx",
  "muted": "#xxxxxx",
  "font_family": "FontName",
  "mood": "clean|bold|academic|corporate|vibrant|warm"
}}

Ensure the hex values are valid 6-digit lowercase hex codes starting with #.
"""


async def _generate_deck_theme(
    *,
    topic: Optional[str],
    context_preview: str,
    user_theme: Optional[str],
) -> ThemeSpec:
    """
    AI-generate a ThemeSpec.

    If user provided a theme string:
      1. Try quick keyword match to a preset first.
      2. Otherwise ask LLM to interpret + generate the palette.
    If no theme is given:
      Ask LLM to choose an appropriate palette from topic + source material context.
    """
    # Fast path: user gave a keyword that matches a preset
    if user_theme:
        preset = _quick_theme_from_keyword(user_theme)
        if preset:
            logger.info("Theme quick-matched to preset for: %r", user_theme)
            return preset

    domain_hint = context_preview[:600] if context_preview else "general educational content"
    topic_str = topic or "General overview"
    user_theme_hint = user_theme or "no theme specified — choose the best professional theme for the topic"

    prompt = _THEME_GENERATION_PROMPT.format(
        topic=topic_str,
        domain_hint=domain_hint,
        user_theme_hint=user_theme_hint,
    )

    try:
        llm = get_llm(mode="structured", max_tokens=256)
        response = await asyncio.to_thread(llm.invoke, prompt)
        response_text = response.content if hasattr(response, "content") else str(response)
        raw = _extract_json_object(response_text)
        theme = _validate_theme(raw)
        logger.info(
            "AI theme generated: primary=%s accent=%s font=%s mood=%s",
            theme["primary"], theme["accent"], theme["font_family"], theme["mood"],
        )
        return theme
    except Exception as exc:
        logger.warning("Theme generation failed, using default: %s", exc)
        return _DEFAULT_THEME.copy()


# ── Slide plan prompt ─────────────────────────────────────────────────────────

_SLIDE_PLAN_PROMPT = """\
You are an expert presentation strategist and instructional designer.

Your task is to design a slide plan that is both visually strong and logically persuasive.

SOURCE MATERIAL:
{context}

TOPIC FOCUS:
{topic_instruction}

THEME DIRECTION:
{theme_instruction}

ARGUMENTATION NOTES:
{argumentation_notes}

MASTER ARGUMENTATION BLUEPRINT (MANDATORY):
- Build one central thesis that answers the topic focus.
- Arrange slides so each one has a clear argumentative role.
- Ensure claims are grounded in source evidence, examples, or data.
- Include at least one slide that addresses a risk, limitation, or counterpoint.
- End with a synthesis that turns findings into practical takeaways.
- Avoid repetition; each slide should move the argument forward.

SLIDE COUNT TARGET:
- Target exactly {target_slides} slides whenever possible.
- Allowed range: {min_slides} to {max_slides} slides.

REQUIREMENTS:
- Create between {min_slides} and {max_slides} slides
- Each slide must have:
  - "title": a clear, concise slide title
  - "bullets": an array of 2-5 key points (short, readable bullet points)
  - "visual_style": one of "minimal", "modern", "diagram", "chart", "timeline"
    - "tone": "educational" (default) or "professional" or "creative"
    - "argument_role": one of "thesis", "context", "evidence", "counterpoint", "synthesis", "summary", "support"
- First slide should be a title/overview slide
- Last slide should be a summary/takeaway slide
- Content must be concise and suitable for visual slides (not paragraphs)
- Focus on the most important information

Return ONLY a JSON array of slide objects. No explanation, no markdown wrapping.

Example output format:
[
  {{"title": "Introduction to Topic", "bullets": ["Key point 1", "Key point 2"], "visual_style": "modern", "tone": "educational", "argument_role": "thesis"}},
  {{"title": "Core Concepts", "bullets": ["Concept A", "Concept B", "Concept C"], "visual_style": "diagram", "tone": "educational", "argument_role": "evidence"}}
]"""


def _bounded_slide_count(target_slide_count: Optional[int]) -> int:
    if target_slide_count is None:
        return 10
    return max(MIN_SLIDES, min(MAX_SLIDES, int(target_slide_count)))


def _build_slide_plan_prompt(
    *,
    context: str,
    topic: Optional[str],
    theme: Optional[str],
    target_slide_count: Optional[int],
    argumentation_notes: Optional[str],
) -> str:
    topic_instruction = (
        f'Focus the presentation specifically on: "{topic}"'
        if topic
        else "Cover the most important topics from the source material comprehensively."
    )
    theme_instruction = (theme or "Use a clean, modern educational visual direction.").strip()
    notes = (
        argumentation_notes
        or "Emphasize clear claim-to-evidence flow and practical implications."
    ).strip()
    target_slides = _bounded_slide_count(target_slide_count)

    return _SLIDE_PLAN_PROMPT.format(
        context=context[:8000],
        topic_instruction=topic_instruction,
        theme_instruction=theme_instruction,
        argumentation_notes=notes,
        target_slides=target_slides,
        min_slides=MIN_SLIDES,
        max_slides=MAX_SLIDES,
    )


# ── Main entry point ──────────────────────────────────────────────────────────

async def generate_slide_plan(
    user_id: str,
    material_ids: List[str],
    notebook_id: Optional[str] = None,
    topic: Optional[str] = None,
    theme: Optional[str] = None,
    target_slide_count: Optional[int] = None,
    argumentation_notes: Optional[str] = None,
) -> Tuple[List[SlideSpec], ThemeSpec]:
    """
    Generate a structured slide plan AND a deck ThemeSpec from user materials.

    Both operations run concurrently — theme generation adds zero serial latency.

    Returns:
        (slide_plan, theme_spec) — validated slide list and colour/font theme.
    """
    logger.info(
        "Generating slide plan: user=%s materials=%d topic=%r",
        user_id, len(material_ids), topic,
    )

    context = await _gather_context(user_id, material_ids, notebook_id, topic)
    if not context or context == "No relevant context found.":
        raise ValueError(
            "No relevant content found in the selected materials for presentation generation."
        )

    logger.info("Slide plan context gathered: %d chars", len(context))

    # Run slide planning and theme generation concurrently
    slides_prompt = _build_slide_plan_prompt(
        context=context,
        topic=topic,
        theme=theme,
        target_slide_count=target_slide_count,
        argumentation_notes=argumentation_notes,
    )

    llm = get_llm(mode="structured", max_tokens=4000)

    slide_plan_coro = asyncio.to_thread(llm.invoke, slides_prompt)
    theme_coro = _generate_deck_theme(
        topic=topic,
        context_preview=context[:1200],
        user_theme=theme,
    )

    slide_response, theme_spec = await asyncio.gather(slide_plan_coro, theme_coro)

    response_text = slide_response.content if hasattr(slide_response, "content") else str(slide_response)
    logger.info("Slide plan LLM response: %d chars", len(response_text))

    raw_slides = _extract_json_array(response_text)
    validated = _validate_slides(raw_slides)

    logger.info(
        "Slide plan validated: %d slides | theme: primary=%s accent=%s font=%s",
        len(validated), theme_spec["primary"], theme_spec["accent"], theme_spec["font_family"],
    )
    return validated, theme_spec
