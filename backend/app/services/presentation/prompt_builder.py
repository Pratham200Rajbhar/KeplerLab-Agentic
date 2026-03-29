"""
Prompt Builder — converts SlideSpec + ThemeSpec into Gemini image generation prompts.

Key improvements:
- Every prompt receives the full HEX color palette and font family.
- Strict 16:9 (1280×720) and layout rules enforced in every prompt.
- Richer style-, tone-, and argument-role-specific instructions.
- Pure functions with no side effects; designed for easy testing.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.services.presentation.slide_planner import SlideSpec, ThemeSpec


# ── Style-specific design instructions ────────────────────────────────────────

_STYLE_INSTRUCTIONS = {
    "minimal": (
        "LAYOUT STYLE — MINIMAL CLEAN:\n"
        "• Generous white space; content floats in 60% of the slide area.\n"
        "• Single clean line separates title from content zone.\n"
        "• No gradients on content area — solid background with subtle texture at most.\n"
        "• Bullet points with simple round dots, no icons or decorations.\n"
        "• Use the accent color only for the title text and the separator line."
    ),
    "modern": (
        "LAYOUT STYLE — MODERN SLEEK:\n"
        "• Bold left-edge accent bar (8px wide, full height) in accent color.\n"
        "• Title in a lightly tinted header band (secondary color, full width).\n"
        "• Content area uses card-style grouping with subtle rounded corners.\n"
        "• Thin geometric decorative element in corner (circle or triangle, opacity 0.08).\n"
        "• Use gradient only in the header band — body stays clean."
    ),
    "diagram": (
        "LAYOUT STYLE — DIAGRAM / INFOGRAPHIC:\n"
        "• Central visual: a clean flowchart, Venn diagram, or hierarchical tree.\n"
        "• Each node is a rounded rectangle in secondary color, labeled in text color.\n"
        "• Arrows use accent color; labels are concise (2–4 words per node).\n"
        "• Title sits in a narrow header strip at the top (15% of height).\n"
        "• Remaining 85% is the diagram — no bullet list, diagram IS the content."
    ),
    "chart": (
        "LAYOUT STYLE — CHART / DATA VISUALIZATION:\n"
        "• Include a clean bar chart, line graph, or donut chart occupying 55% of slide.\n"
        "• Chart uses accent color for primary data series, muted color for secondary.\n"
        "• Clear axis labels, no gridlines (or very faint ones in muted color).\n"
        "• Title strip at top (15% height); brief 2-line insight text beside chart.\n"
        "• Source/footnote text at very bottom in muted color, 10pt equivalent."
    ),
    "timeline": (
        "LAYOUT STYLE — TIMELINE:\n"
        "• Horizontal timeline spanning 80% of the slide width, vertically centered.\n"
        "• Milestone circles in accent color; connecting line in muted color.\n"
        "• Each milestone has a bold label above and a 1-line description below.\n"
        "• Title in top strip; bottom 15% left for any additional context.\n"
        "• Progressive left-to-right reading with equal spacing between milestones."
    ),
}

_TONE_INSTRUCTIONS = {
    "educational": (
        "TONE — EDUCATIONAL:\n"
        "Friendly, approachable, and clear. Large readable fonts, illustrated concepts, "
        "welcoming color warmth. Designed for students and learners — avoid jargon-heavy visuals."
    ),
    "professional": (
        "TONE — PROFESSIONAL:\n"
        "Polished, executive-level. Clean data-forward layout, restrained color use, "
        "strict alignment. Suitable for boardroom, investor, or client-facing decks."
    ),
    "creative": (
        "TONE — CREATIVE:\n"
        "Expressive and dynamic. Bold asymmetric layout, layered typography sizes, "
        "vibrant accent color used liberally. Push visual interest without sacrificing legibility."
    ),
}

_ARGUMENT_ROLE_INSTRUCTIONS = {
    "thesis": (
        "ARGUMENT ROLE — THESIS:\n"
        "This is the opening claim slide. Make it visually commanding: large title text, "
        "minimal bullets (1–2 max), strong accent color usage. It must communicate one bold idea."
    ),
    "context": (
        "ARGUMENT ROLE — CONTEXT:\n"
        "Sets the scene. Use visuals that orient the audience: maps, timelines, or definition "
        "cards. Keep tone informational; avoid over-styling."
    ),
    "evidence": (
        "ARGUMENT ROLE — EVIDENCE:\n"
        "Data and proof. Prefer chart or diagram layout. Every bullet should read as a "
        "data point or verified fact. Numbers in accent color for emphasis."
    ),
    "counterpoint": (
        "ARGUMENT ROLE — COUNTERPOINT:\n"
        "Presents opposing view or risk. Use a subtle split-panel layout — one side for 'challenge', "
        "one for 'response'. A mild warning-tone color (warm red/orange accent) is acceptable here."
    ),
    "synthesis": (
        "ARGUMENT ROLE — SYNTHESIS:\n"
        "Connects ideas into one unified takeaway. Converging arrows or a funnel diagram works well. "
        "Highlight the synthesis statement in accent color — this is the 'aha' moment."
    ),
    "summary": (
        "ARGUMENT ROLE — SUMMARY:\n"
        "Closing recap. Use a checklist or numbered list layout. Each item is a top-line takeaway. "
        "Include a subtle 'Thank you / Next steps' area at the bottom in muted color."
    ),
    "support": (
        "ARGUMENT ROLE — SUPPORT:\n"
        "Standard supporting content slide. Balanced layout, 3–5 bullet points, optional icon per "
        "bullet. Keep visual elements proportional and not distracting."
    ),
}


# ── Master slide prompt template ──────────────────────────────────────────────

_SLIDE_PROMPT_TEMPLATE = """\
Create a PROFESSIONAL PRESENTATION SLIDE IMAGE. This image will be used directly in a slide deck presentation.

══════════════════════════════════════════════════
STRICT TECHNICAL REQUIREMENTS (NON-NEGOTIABLE):
══════════════════════════════════════════════════
• Canvas size: EXACTLY 1280 × 720 pixels — 16:9 widescreen landscape
• Orientation: landscape ONLY — never portrait, never square
• Edges: clean rectangular border, no drop shadow on the canvas itself
• Format: single flat image, no device frame, no presentation app chrome

══════════════════════════════════════════════════
SLIDE IDENTITY:
══════════════════════════════════════════════════
Slide {slide_number} of {total_slides}
Title: "{title}"
Argument Role: {argument_role}

══════════════════════════════════════════════════
COLOR SYSTEM (USE THESE EXACT HEX VALUES):
══════════════════════════════════════════════════
• Background (primary):  {color_primary}
• Surface / cards:       {color_secondary}
• Headings / highlights: {color_accent}
• Body text:             {color_text}
• Captions / subtitles:  {color_muted}
• Font family:           {font_family} (sans-serif ONLY — no serif fonts anywhere)

IMPORTANT: Apply these colors consistently. Do NOT introduce any other colors not listed above.
The accent color {color_accent} should be used for the slide title text and any call-out elements.

══════════════════════════════════════════════════
CONTENT TO DISPLAY:
══════════════════════════════════════════════════
Slide Title (display prominently): {title}

Bullet Points (display all of these clearly):
{bullet_text}

══════════════════════════════════════════════════
TYPOGRAPHY RULES:
══════════════════════════════════════════════════
• Title: {font_family}, Bold, minimum 42pt equivalent — color: {color_accent}
• Bullets: {font_family}, Regular or Medium, minimum 24pt equivalent — color: {color_text}
• Captions/footnotes: {font_family}, Light, 14pt equivalent — color: {color_muted}
• Line spacing: 1.4× for bullets; 1.2× for title
• Maximum 5 bullet points visible; trim if needed
• NO bold on bullet text (bold is reserved for title only)

══════════════════════════════════════════════════
LAYOUT STRUCTURE:
══════════════════════════════════════════════════
• Top strip (12% height): slide title area
• Content zone (75% height): bullets and visual elements  
• Bottom strip (13% height): slide number "{slide_number}/{total_slides}" in bottom-right corner (muted color, 12pt)
• Left/right margins: minimum 6% of width
• Never let text touch the canvas edge

══════════════════════════════════════════════════
VISUAL STYLE DIRECTIVE:
══════════════════════════════════════════════════
Mood: {mood}

{style_instruction}

══════════════════════════════════════════════════
TONE:
══════════════════════════════════════════════════
{tone_instruction}

══════════════════════════════════════════════════
ARGUMENT ROLE DESIGN INTENT:
══════════════════════════════════════════════════
{argument_role_instruction}

══════════════════════════════════════════════════
ABSOLUTE PROHIBITIONS:
══════════════════════════════════════════════════
✗ NO watermarks, logos, or stock photo attribution
✗ NO photos or photorealistic images unless specifically in a chart/diagram context
✗ NO serif fonts (no Times New Roman, Georgia, Palatino etc.)
✗ NO text that says "Slide X" in the title area (slide number goes in footer only)
✗ NO gradient backgrounds in the main content area (gradient only allowed in header strip)
✗ NO portrait or square orientation — must be 1280×720 landscape
✗ NO clip art or cartoon illustrations
✗ NO placeholder text like "Lorem ipsum" or "[Insert content here]"

This must look like a REAL, PREMIUM presentation slide produced by a professional designer in Keynote or Figma.\
"""


# ── Build functions ────────────────────────────────────────────────────────────

def build_slide_prompt(
    slide: "SlideSpec",
    slide_index: int,
    total_slides: int,
    theme_spec: Optional["ThemeSpec"] = None,
) -> str:
    """
    Build a Gemini image generation prompt for a single slide.

    Args:
        slide:        The slide specification dict.
        slide_index:  0-based index of this slide.
        total_slides: Total number of slides in the deck.
        theme_spec:   Optional ThemeSpec with color palette and font. Falls back
                      to safe neutral defaults if None.

    Returns:
        A complete prompt string ready for Gemini image generation.
    """
    # Resolve slide fields
    if isinstance(slide, dict):
        bullets = slide.get("bullets", [])
        title = slide.get("title") or f"Slide {slide_index + 1}"
        visual_style = str(slide.get("visual_style") or slide.get("visualStyle") or "modern").lower()
        tone = str(slide.get("tone") or "educational").lower()
        argument_role = str(slide.get("argument_role") or slide.get("argumentRole") or "support").lower()
    else:
        bullets = []
        title = f"Slide {slide_index + 1}"
        visual_style = "modern"
        tone = "educational"
        argument_role = "support"

    bullet_text = "\n".join(f"  • {b}" for b in (bullets or ["Key point"]))

    # Resolve theme
    if theme_spec:
        color_primary = theme_spec.get("primary", "#0f172a")
        color_secondary = theme_spec.get("secondary", "#1e293b")
        color_accent = theme_spec.get("accent", "#38bdf8")
        color_text = theme_spec.get("text", "#e2e8f0")
        color_muted = theme_spec.get("muted", "#94a3b8")
        font_family = theme_spec.get("font_family", "Inter")
        mood = theme_spec.get("mood", "clean")
    else:
        color_primary = "#0f172a"
        color_secondary = "#1e293b"
        color_accent = "#38bdf8"
        color_text = "#e2e8f0"
        color_muted = "#94a3b8"
        font_family = "Inter"
        mood = "clean"

    style_instruction = _STYLE_INSTRUCTIONS.get(visual_style, _STYLE_INSTRUCTIONS["modern"])
    tone_instruction = _TONE_INSTRUCTIONS.get(tone, _TONE_INSTRUCTIONS["educational"])
    argument_role_instruction = _ARGUMENT_ROLE_INSTRUCTIONS.get(
        argument_role, _ARGUMENT_ROLE_INSTRUCTIONS["support"]
    )

    return _SLIDE_PROMPT_TEMPLATE.format(
        slide_number=slide_index + 1,
        total_slides=total_slides,
        title=title,
        argument_role=argument_role,
        bullet_text=bullet_text,
        color_primary=color_primary,
        color_secondary=color_secondary,
        color_accent=color_accent,
        color_text=color_text,
        color_muted=color_muted,
        font_family=font_family,
        mood=mood,
        style_instruction=style_instruction,
        tone_instruction=tone_instruction,
        argument_role_instruction=argument_role_instruction,
    )


def build_all_prompts(
    slides: "list[SlideSpec]",
    theme_spec: "Optional[ThemeSpec]" = None,
    # Legacy compat params (ignored — theme_spec supersedes)
    deck_theme: "Optional[str]" = None,
    argumentation_notes: "Optional[str]" = None,
) -> list[str]:
    """Build prompts for all slides in the deck, applying the shared ThemeSpec."""
    total = len(slides)
    return [
        build_slide_prompt(s, i, total, theme_spec=theme_spec)
        for i, s in enumerate(slides)
    ]
