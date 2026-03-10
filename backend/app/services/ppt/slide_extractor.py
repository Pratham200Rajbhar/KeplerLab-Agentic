from __future__ import annotations

import logging
import re
import time
from typing import List, Dict

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger("ppt.extractor")

SLIDE_WIDTH = 1920
SLIDE_HEIGHT = 1080

_SLIDE_RESET_CSS = f"""
/* === Slide isolation reset === */
*, *::before, *::after {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}}
html, body {{
    width: {SLIDE_WIDTH}px;
    height: {SLIDE_HEIGHT}px;
    overflow: hidden;
    margin: 0;
    padding: 0;
    background: #000;
}}
.slide {{
    width: {SLIDE_WIDTH}px  !important;
    height: {SLIDE_HEIGHT}px !important;
    min-height: {SLIDE_HEIGHT}px !important;
    max-height: {SLIDE_HEIGHT}px !important;
    overflow: hidden !important;
    position: relative !important;
}}
"""

def extract_slides(html_content: str) -> List[Dict]:
    t0 = time.time()

    try:
        soup = BeautifulSoup(html_content, "html.parser")
    except Exception as exc:
        logger.error("BeautifulSoup parse failed: %s", exc)
        return []

    head_css = _extract_head_css(soup)

    slide_elements = _find_slide_elements(soup)

    if not slide_elements:
        logger.warning("No .slide elements found in HTML — returning empty list")
        return []

    logger.info(
        "Found %d slide elements | head_css_length=%d chars",
        len(slide_elements),
        len(head_css),
    )

    slides: List[Dict] = []

    for idx, slide_el in enumerate(slide_elements, start=1):
        slide_id = slide_el.get("id") or f"slide-{idx}"

        try:
            slide_html = _build_slide_html(
                slide_element=slide_el,
                head_css=head_css,
                slide_number=idx,
                slide_id=slide_id,
            )
            slides.append(
                {
                    "slide_number": idx,
                    "slide_id": slide_id,
                    "html": slide_html,
                }
            )
        except Exception as exc:
            logger.error("Failed to build HTML for slide %d: %s", idx, exc)
            continue

    elapsed = time.time() - t0
    logger.info(
        "Slide extraction complete | extracted=%d/%d | time=%.3fs",
        len(slides),
        len(slide_elements),
        elapsed,
    )
    return slides

def _extract_head_css(soup: BeautifulSoup) -> str:
    css_blocks: List[str] = []

    for style_tag in soup.find_all("style"):
        content = style_tag.get_text()
        if content.strip():
            css_blocks.append(content)

    return "\n\n".join(css_blocks)

def _find_slide_elements(soup: BeautifulSoup) -> List[Tag]:
    def _has_slide_class(tag):
        if tag.name not in ("section", "div"):
            return False
        classes = tag.get("class", [])
        if isinstance(classes, str):
            classes = classes.split()
        return "slide" in classes

    return soup.find_all(_has_slide_class)

def _build_slide_html(
    slide_element: Tag,
    head_css: str,
    slide_number: int,
    slide_id: str,
) -> str:
    slide_markup = str(slide_element)

    if 'class="slide"' not in slide_markup and "class='slide'" not in slide_markup:
        pass

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width={SLIDE_WIDTH}">
  <title>Slide {slide_number}</title>
  <style>
{head_css}
  </style>
  <style>
{_SLIDE_RESET_CSS}
  </style>
</head>
<body>
{slide_markup}
</body>
</html>"""

    return html
