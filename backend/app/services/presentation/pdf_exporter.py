from __future__ import annotations

import asyncio
from pathlib import Path
import subprocess
import sys

from playwright.async_api import Error as PlaywrightError, async_playwright


async def _ensure_chromium_installed() -> None:
    def _install() -> None:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            capture_output=True,
            text=True,
        )

    await asyncio.to_thread(_install)


async def export_pdf_from_html(html_path: str, pdf_path: str) -> str:
    source = Path(html_path).resolve()
    target = Path(pdf_path).resolve()

    if not source.exists():
        raise FileNotFoundError(f"HTML source not found: {source}")

    target.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as playwright:
        try:
            browser = await playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-gpu"],
            )
        except PlaywrightError as exc:
            if "Executable doesn't exist" not in str(exc):
                raise
            try:
                await _ensure_chromium_installed()
            except Exception as install_exc:
                raise RuntimeError(
                    "Chromium browser is required for PDF export. "
                    "Automatic install failed; run 'python -m playwright install chromium'."
                ) from install_exc

            browser = await playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-gpu"],
            )
        try:
            page = await browser.new_page(viewport={"width": 1920, "height": 1080})
            await page.goto(source.as_uri(), wait_until="networkidle")
            await page.add_style_tag(
                content="""
                @page { size: 16in 9in; margin: 0; }
                html, body { margin: 0 !important; padding: 0 !important; }
                """
            )
            await page.pdf(
                path=str(target),
                width="16in",
                height="9in",
                margin={"top": "0in", "right": "0in", "bottom": "0in", "left": "0in"},
                print_background=True,
                prefer_css_page_size=True,
            )
        finally:
            await browser.close()

    return str(target)
