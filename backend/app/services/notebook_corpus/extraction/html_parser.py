"""HTML parser — extract main content from HTML files and URLs."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from app.services.notebook_corpus.errors import SourceExtractionError
from app.services.notebook_corpus.schemas import ExtractedContent
from .normalization import normalize_text, estimate_tokens

logger = logging.getLogger(__name__)


def parse_html_file(file_path: str) -> ExtractedContent:
    """Parse a local HTML file and extract main content."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            html_content = f.read()
    except Exception as e:
        raise SourceExtractionError(f"Failed to read HTML file: {e}")

    return _extract_from_html(html_content, source_url=None)


async def extract_from_url(url: str) -> Dict[str, Any]:
    """Fetch a URL and extract main content. Returns dict with 'text', 'title', 'warnings'."""
    return await asyncio.to_thread(_fetch_and_extract, url)


def _fetch_and_extract(url: str) -> Dict[str, Any]:
    """Synchronous URL fetch + extraction."""
    warnings = []

    # Try trafilatura first (best at extracting main content)
    try:
        import trafilatura

        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            result = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=True,
                output_format="txt",
            )
            title_result = trafilatura.extract(downloaded, output_format="xml")
            title = ""
            if title_result:
                import re
                title_match = re.search(r"<title>(.*?)</title>", title_result, re.DOTALL)
                if title_match:
                    title = title_match.group(1).strip()

            if result and result.strip():
                return {"text": result.strip(), "title": title, "warnings": warnings}

        warnings.append("trafilatura returned no content, trying BeautifulSoup fallback")
    except ImportError:
        warnings.append("trafilatura not available")
    except Exception as e:
        warnings.append(f"trafilatura failed: {e}")

    # Fallback: requests + BeautifulSoup
    try:
        import requests
        from bs4 import BeautifulSoup

        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0 KeplerLab/1.0"})
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        text = soup.get_text(separator="\n", strip=True)

        if text.strip():
            return {"text": text.strip(), "title": title, "warnings": warnings}

    except Exception as e:
        warnings.append(f"BeautifulSoup fallback failed: {e}")

    return {"text": "", "title": "", "warnings": warnings}


def _extract_from_html(html_content: str, source_url: str | None = None) -> ExtractedContent:
    """Extract main content from HTML string."""
    warnings = []

    try:
        import trafilatura
        result = trafilatura.extract(html_content, include_comments=False, include_tables=True)
        if result and result.strip():
            normalized = normalize_text(result)
            return ExtractedContent(
                text=normalized,
                metadata={"source_type": "html"},
                sections=[],
                warnings=warnings,
                token_count=estimate_tokens(normalized),
                page_count=0,
            )
    except ImportError:
        pass

    # Fallback
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")
        for script in soup(["script", "style", "nav", "footer"]):
            script.decompose()
        text = soup.get_text(separator="\n", strip=True)
        normalized = normalize_text(text)
        return ExtractedContent(
            text=normalized,
            metadata={"source_type": "html"},
            sections=[],
            warnings=warnings,
            token_count=estimate_tokens(normalized),
            page_count=0,
        )
    except Exception as e:
        raise SourceExtractionError(f"HTML extraction failed: {e}")
