"""PDF parser using PyMuPDF (fitz) with pdfplumber fallback."""
from __future__ import annotations

import logging
from typing import List, Dict, Any

from app.services.notebook_corpus.errors import SourceExtractionError
from app.services.notebook_corpus.schemas import ExtractedContent
from .normalization import normalize_text, estimate_tokens

logger = logging.getLogger(__name__)


def parse_pdf(file_path: str) -> ExtractedContent:
    """Extract text from PDF with page boundaries preserved."""
    pages: List[Dict[str, Any]] = []
    warnings: List[str] = []

    try:
        import fitz  # PyMuPDF

        doc = fitz.open(file_path)
        for page_idx, page in enumerate(doc):
            text = page.get_text("text")
            if text.strip():
                pages.append({
                    "page_number": page_idx + 1,
                    "text": text.strip(),
                })
        doc.close()

    except ImportError:
        warnings.append("PyMuPDF not available, falling back to pdfplumber")
        try:
            import pdfplumber

            with pdfplumber.open(file_path) as pdf:
                for page_idx, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    if text.strip():
                        pages.append({
                            "page_number": page_idx + 1,
                            "text": text.strip(),
                        })
        except Exception as e:
            raise SourceExtractionError(f"PDF extraction failed: {e}")

    except Exception as e:
        # Fall back to pdfplumber
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                for page_idx, page in enumerate(pdf.pages):
                    text = page.extract_text() or ""
                    if text.strip():
                        pages.append({
                            "page_number": page_idx + 1,
                            "text": text.strip(),
                        })
            warnings.append(f"PyMuPDF fallback triggered: {e}")
        except Exception as e2:
            raise SourceExtractionError(f"PDF extraction failed with both parsers: {e}; {e2}")

    if not pages:
        # Try OCR as last resort
        warnings.append("No text extracted from PDF — may need OCR")
        return ExtractedContent(
            text="",
            metadata={"page_count": 0, "required_ocr": True},
            sections=[],
            warnings=warnings,
            token_count=0,
            page_count=0,
        )

    # Build sections from pages
    sections = [
        {"title": f"Page {p['page_number']}", "text": p["text"], "page_number": p["page_number"]}
        for p in pages
    ]

    full_text = "\n\n".join(
        f"[Page {p['page_number']}]\n{p['text']}" for p in pages
    )
    normalized = normalize_text(full_text)
    token_count = estimate_tokens(normalized)

    return ExtractedContent(
        text=normalized,
        metadata={"page_count": len(pages), "source_type": "pdf"},
        sections=sections,
        warnings=warnings,
        token_count=token_count,
        page_count=len(pages),
    )
