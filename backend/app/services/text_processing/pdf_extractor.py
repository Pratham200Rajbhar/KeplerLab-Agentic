from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import fitz
import pdfplumber

logger = logging.getLogger(__name__)

DIGITAL_CHARS_THRESHOLD = 150
SPARSE_PAGE_THRESHOLD = 50

@dataclass
class _Block:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    font_size: float = 12.0
    font_name: str = ""
    is_bold: bool = False
    page_num: int = 0

@dataclass
class _Meta:
    page_count: int = 0
    tables_detected: int = 0
    equations_detected: int = 0
    ocr_pages: int = 0
    method: str = "pymupdf"

class PDFExtractor:

    def __init__(self) -> None:
        self._meta = _Meta()

    def extract_text(self, pdf_path: str) -> Dict[str, Any]:
        try:
            self._meta = _Meta()
            with fitz.open(pdf_path) as doc:
                self._meta.page_count = len(doc)

                sample_indices = sorted(set([
                    0,
                    len(doc) // 4,
                    len(doc) // 2,
                    3 * len(doc) // 4,
                    len(doc) - 1,
                ]))[:min(5, len(doc))]
                sample_n = len(sample_indices)
                sample_chars = sum(len(doc[i].get_text().strip()) for i in sample_indices)
                avg_chars = sample_chars / sample_n if sample_n else 0

                if avg_chars > DIGITAL_CHARS_THRESHOLD:
                    logger.info(
                        "Digital PDF detected (avg %.0f chars/page), using PyMuPDF",
                        avg_chars,
                    )
                    text, ocr_pages = self._extract_digital(doc, pdf_path)
                    self._meta.method = "pymupdf" if not ocr_pages else "pymupdf+ocr"
                else:
                    logger.info(
                        "Scanned PDF detected (avg %.0f chars/page), routing all pages to OCR",
                        avg_chars,
                    )
                    text = ""
                    ocr_pages = list(range(len(doc)))
                    self._meta.method = "ocr"

                self._meta.ocr_pages = len(ocr_pages)

            return {
                "status": "success",
                "text": text,
                "metadata": {
                    "page_count": self._meta.page_count,
                    "tables_detected": self._meta.tables_detected,
                    "equations_detected": self._meta.equations_detected,
                    "ocr_pages": self._meta.ocr_pages,
                    "method": self._meta.method,
                },
                "ocr_needed_pages": ocr_pages,
            }

        except Exception as exc:
            logger.error("PDF extraction failed for %s: %s", pdf_path, exc)
            return {
                "status": "failed",
                "text": "",
                "metadata": {},
                "ocr_needed_pages": [],
                "error": str(exc),
            }

    def _extract_digital(
        self, doc: fitz.Document, pdf_path: str
    ) -> Tuple[str, List[int]]:
        page_texts: List[str] = []
        ocr_pages: List[int] = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = self._extract_blocks(page, page_num)
            total_chars = sum(len(b.text) for b in blocks)

            if total_chars < SPARSE_PAGE_THRESHOLD:
                ocr_pages.append(page_num)
                continue

            page_md = self._blocks_to_markdown(blocks)
            if page_md.strip():
                page_texts.append(page_md)

        tables_md = self._extract_tables(pdf_path)

        combined = "\n\n".join(page_texts)
        if tables_md:
            combined = combined + "\n\n" + tables_md

        return self._normalize(combined), ocr_pages

    def _extract_blocks(self, page: fitz.Page, page_num: int) -> List[_Block]:
        blocks: List[_Block] = []
        try:
            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    line_text = ""
                    sizes: List[float] = []
                    fonts: List[str] = []
                    bolds: List[bool] = []
                    for span in line.get("spans", []):
                        t = span.get("text", "").strip()
                        if t:
                            line_text += t + " "
                            sizes.append(span.get("size", 12.0))
                            fonts.append(span.get("font", ""))
                            bolds.append("bold" in span.get("font", "").lower())
                    line_text = line_text.strip()
                    if not line_text:
                        continue
                    bbox = line.get("bbox", [0, 0, 0, 0])
                    blocks.append(
                        _Block(
                            text=line_text,
                            x0=bbox[0],
                            y0=bbox[1],
                            x1=bbox[2],
                            y1=bbox[3],
                            font_size=max(sizes) if sizes else 12.0,
                            font_name=fonts[0] if fonts else "",
                            is_bold=any(bolds),
                            page_num=page_num,
                        )
                    )
        except Exception as exc:
            logger.warning("Block extraction failed on page %d: %s", page_num, exc)
        return blocks

    def _blocks_to_markdown(self, blocks: List[_Block]) -> str:
        if not blocks:
            return ""

        blocks = sorted(blocks, key=lambda b: (b.y0, b.x0))

        sizes = [b.font_size for b in blocks]
        avg_size = sum(sizes) / len(sizes) if sizes else 12.0

        output: List[str] = []
        prev_y1 = 0.0

        for b in blocks:
            if b.font_size > avg_size * 1.5:
                output.append(f"\n# {b.text}\n")
            elif b.font_size > avg_size * 1.2 or b.is_bold:
                output.append(f"\n## {b.text}\n")
            elif b.text.isupper() and 1 <= len(b.text.split()) <= 10:
                output.append(f"\n## {b.text}\n")
            elif "mono" in b.font_name.lower() or "courier" in b.font_name.lower():
                output.append(f"\n```\n{b.text}\n```\n")
            elif self._is_equation(b.text):
                self._meta.equations_detected += 1
                output.append(f"\n[EQUATION] {b.text}\n")
            else:
                if prev_y1 > 0 and (b.y0 - prev_y1) > avg_size * 1.5:
                    output.append("")
                output.append(b.text)

            prev_y1 = b.y1

        return "\n".join(output)

    @staticmethod
    def _is_equation(text: str) -> bool:
        markers = {"∫", "∑", "∂", "√", "π", "α", "β", "γ", "δ", "θ", "λ", "μ", "σ"}
        return any(m in text for m in markers)

    def _extract_tables(self, pdf_path: str) -> str:
        parts: List[str] = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    for idx, table in enumerate(page.extract_tables() or []):
                        if not table or not table[0]:
                            continue
                        self._meta.tables_detected += 1
                        md = self._table_to_markdown(table, page_num, idx)
                        if md:
                            parts.append(md)
        except Exception as exc:
            logger.warning("Table extraction failed: %s", exc)
        return "\n\n".join(parts)

    @staticmethod
    def _table_to_markdown(
        table: List[List[Optional[str]]],
        page_num: int,
        idx: int,
    ) -> str:
        try:
            header = [str(c).strip() if c else "" for c in table[0]]
            rows: List[str] = [
                "| " + " | ".join(header) + " |",
                "|" + "|".join("---" for _ in header) + "|",
            ]
            for row in table[1:]:
                if not row:
                    continue
                cells = [str(c).strip() if c else "" for c in row]
                cells = (cells + [""] * len(header))[: len(header)]
                rows.append("| " + " | ".join(cells) + " |")
            return f"\n**Table {idx + 1} (Page {page_num + 1})**\n\n" + "\n".join(rows)
        except Exception as exc:
            logger.warning("Failed to render table: %s", exc)
            return ""

    @staticmethod
    def _normalize(text: str) -> str:
        if not text:
            return ""

        lines = text.split("\n")
        out: List[str] = []
        prev_blank = False

        for line in lines:
            line = line.strip()
            if not line:
                if not prev_blank:
                    out.append("")
                    prev_blank = True
            else:
                out.append(line)
                prev_blank = False

        counts = Counter(l for l in out if l and len(l) <= 60)
        noise = {l for l, n in counts.items() if n > 5}
        if noise:
            out = [l for l in out if l not in noise]

        return "\n".join(out).strip()
