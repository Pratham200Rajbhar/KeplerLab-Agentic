from __future__ import annotations

import html
from pathlib import Path

from app.core.config import settings
from app.services.presentation.schemas import PresentationPayload


def _render_element(element: dict) -> str:
    etype = element.get("type")
    if etype == "title":
        return f"<h1>{html.escape(str(element.get('text', '')))}</h1>"
    if etype == "subtitle":
        return f"<h2>{html.escape(str(element.get('text', '')))}</h2>"
    if etype == "bullet":
        items = element.get("items") or []
        item_html = "".join(f"<li>{html.escape(str(item))}</li>" for item in items)
        return f"<ul>{item_html}</ul>"
    if etype == "numbered_list":
      items = element.get("items") or []
      item_html = "".join(f"<li>{html.escape(str(item))}</li>" for item in items)
      return f"<ol>{item_html}</ol>"
    if etype == "paragraph":
        return f"<p>{html.escape(str(element.get('text', '')))}</p>"
    if etype == "quote":
      return f"<blockquote>{html.escape(str(element.get('text', '')))}</blockquote>"
    if etype == "code":
      return f"<pre><code>{html.escape(str(element.get('text', '')))}</code></pre>"
    if etype == "callout":
      return f"<div class=\"callout\">{html.escape(str(element.get('text', '')))}</div>"
    if etype == "divider":
      return "<hr />"
    if etype == "table":
        rows = element.get("rows") or []
        if not rows:
            return "<table></table>"
        body = []
        for row in rows:
            cols = "".join(f"<td>{html.escape(str(col))}</td>" for col in (row or []))
            body.append(f"<tr>{cols}</tr>")
        return "<table>" + "".join(body) + "</table>"
    if etype == "image":
        alt_text = html.escape(str(element.get("prompt", "image")))
        return f"<div class=\"image-placeholder\">Image: {alt_text}</div>"
    return ""


def render_presentation_html(presentation_id: str, payload: PresentationPayload) -> str:
    tokens = payload.theme_tokens.model_dump()

    slides_markup: list[str] = []
    for slide in payload.model_dump().get("slides", []):
        title = html.escape(str(slide.get("title", "")))
        elements_html = "\n".join(_render_element(el) for el in slide.get("elements", []))
        slides_markup.append(
            "\n".join(
                [
                    "<slide>",
                    f"  <div class=\"slide\">",
                    f"    <header><h1>{title}</h1></header>",
                    "    <section>",
                    elements_html,
                    "    </section>",
                    "  </div>",
                    "</slide>",
                ]
            )
        )

    html_doc = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Montserrat:wght@700&family=Playfair+Display:wght@700&family=Open+Sans:wght@400;600&display=swap" rel="stylesheet">
  <style>
    body {{
      margin: 0;
      padding: 0;
      background: {tokens['bg']};
      font-family: {tokens['body_font']};
      overflow-x: hidden;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 40px;
      padding: 40px 0;
    }}
    slide {{
      display: block;
      page-break-after: always;
      scroll-snap-align: start;
    }}
    .slide {{
      width: 1920px;
      height: 1080px;
      background: {tokens['card']};
      box-sizing: border-box;
      padding: 60px 80px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      position: relative;
      box-shadow: 0 12px 30px rgba(0, 0, 0, 0.08);
      border: 1px solid {tokens['border']};
      border-radius: 12px;
    }}
    header {{
      margin-bottom: 30px;
      border-bottom: 4px solid {tokens['accent']};
      padding-bottom: 15px;
    }}
    h1 {{
      margin: 0;
      font-size: 52px;
      line-height: 1.1;
      color: {tokens['text']};
      font-family: {tokens['header_font']};
      font-weight: 700;
    }}
    section {{
      flex: 1;
      display: flex;
      flex-direction: column;
      justify-content: flex-start;
      gap: 24px;
    }}
    h2 {{
      margin: 0;
      font-size: 36px;
      color: {tokens['accent']};
      font-family: {tokens['header_font']};
    }}
    p, li {{
      font-size: 28px;
      line-height: 1.4;
      color: {tokens['text']};
      margin: 0;
    }}
    ul {{
      margin: 0;
      padding-left: 40px;
      list-style-type: square;
    }}
    ol {{
      margin: 0;
      padding-left: 40px;
    }}
    li {{
      margin-bottom: 12px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 22px;
      margin-top: 20px;
    }}
    td {{
      border: 2px solid {tokens['border']};
      padding: 16px;
      vertical-align: top;
      color: {tokens['text']};
    }}
    .image-placeholder {{
      border: 4px dashed {tokens['accent']}44;
      background: {tokens['accent']}08;
      border-radius: 16px;
      padding: 30px;
      text-align: center;
      color: {tokens['muted']};
      font-size: 24px;
      min-height: 200px;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    blockquote {{
      margin: 0;
      border-left: 8px solid {tokens['accent']};
      padding: 16px 20px;
      background: {tokens['accent']}10;
      border-radius: 10px;
      font-size: 26px;
      color: {tokens['text']};
      font-style: italic;
    }}
    pre {{
      margin: 0;
      border: 2px solid {tokens['border']};
      border-radius: 10px;
      padding: 18px;
      background: {tokens['bg']};
      overflow: hidden;
    }}
    code {{
      font-size: 22px;
      line-height: 1.35;
      color: {tokens['text']};
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .callout {{
      border: 3px solid {tokens['accent']};
      border-radius: 12px;
      padding: 16px 20px;
      font-size: 24px;
      color: {tokens['text']};
      background: {tokens['accent']}12;
    }}
    hr {{
      border: none;
      border-top: 4px solid {tokens['border']};
      margin: 0;
    }}
  </style>
</head>
<body>
{''.join(slides_markup)}
</body>
</html>
"""

    out_dir = Path(settings.GENERATED_OUTPUT_DIR) / "presentations"
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"{presentation_id}.html"
    html_path.write_text(html_doc, encoding="utf-8")
    return str(html_path)
