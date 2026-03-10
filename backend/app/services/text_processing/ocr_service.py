import os
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Set, Tuple, Any

import easyocr
import numpy as np
import fitz
from PIL import Image, ImageEnhance, ImageFilter

from .file_detector import FileTypeDetector

logger = logging.getLogger(__name__)

_GPU_AVAILABLE: bool = False
try:
    import torch as _torch
    _GPU_AVAILABLE = _torch.cuda.is_available()
    if _GPU_AVAILABLE:
        logger.info(
            "OCR GPU mode: %s (CUDA %s)",
            _torch.cuda.get_device_name(0),
            _torch.version.cuda,
        )
        _torch.cuda.empty_cache()
    else:
        logger.info("CUDA not available — OCR will run on CPU.")
except ImportError:
    logger.info("PyTorch not installed — OCR running in CPU-only mode.")

def _flush_gpu_cache() -> None:
    if _GPU_AVAILABLE:
        try:
            _torch.cuda.empty_cache()
            _torch.cuda.synchronize()
        except Exception:
            pass

class OCRService:

    PDF_DPI: int = 200
    _MIN_LONG_EDGE: int = 1600

    def __init__(self) -> None:
        self.reader: Optional[easyocr.Reader] = None
        self._init_reader()

    def _init_reader(self) -> None:
        try:
            _flush_gpu_cache()
            self.reader = easyocr.Reader(
                ["en"],
                gpu=_GPU_AVAILABLE,
                verbose=False,
                download_enabled=True,
            )
            logger.info(
                "EasyOCR initialised in %s mode",
                "GPU" if _GPU_AVAILABLE else "CPU",
            )
            try:
                dummy = np.ones((64, 64, 3), dtype=np.uint8) * 255
                self.reader.readtext(dummy, detail=0, paragraph=False)
                _flush_gpu_cache()
                logger.info("EasyOCR warm-up complete")
            except Exception as exc:
                logger.warning("EasyOCR warm-up failed (non-fatal): %s", exc)
        except Exception as exc:
            logger.error("EasyOCR init failed: %s", exc)
            self.reader = None

    def extract_text_from_image(
        self,
        image_path: str,
        preprocess: bool = True,
    ) -> Dict[str, Any]:
        try:
            info = FileTypeDetector.detect_file_type(image_path)
            if info.get("category") != "image":
                raise ValueError("Not an image file: %s" % image_path)
            img = Image.open(image_path)
            if preprocess:
                img = self._preprocess(img)
            if self.reader:
                result = self._page_to_markdown(img)
                return {
                    "text": result["text"],
                    "confidence": result["confidence"],
                    "method": "easyocr",
                    "status": "success",
                }
            if os.environ.get("USE_TESSERACT") == "1":
                return self._tesseract(img)
            raise RuntimeError("No OCR engine available.")
        except Exception as exc:
            logger.error("Image OCR failed for %s: %s", image_path, exc)
            return {
                "text": "",
                "confidence": 0.0,
                "method": "none",
                "status": "failed",
                "error": str(exc),
            }

    def extract_text_from_pdf_images(
        self,
        pdf_path: str,
        page_numbers: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        try:
            with fitz.open(pdf_path) as probe:
                total_pages = len(probe)

            all_pages = list(range(total_pages))
            pages = [
                p for p in (page_numbers if page_numbers is not None else all_pages)
                if 0 <= p < total_pages
            ]

            logger.info(
                "OCR: processing %d/%d pages  pdf=%s",
                len(pages), total_pages, pdf_path,
            )

            rendered: List[Tuple[int, Image.Image]] = self._render_parallel(
                pdf_path, pages
            )

            _flush_gpu_cache()
            page_texts: List[str] = []
            total_conf = 0.0
            processed = 0

            for page_num, img in rendered:
                result = self._ocr_page(page_num, img, total_pages)
                if result["text"].strip():
                    page_texts.append(result["text"])
                    total_conf += result["confidence"]
                    processed += 1
                _flush_gpu_cache()

            full_text = "\n\n".join(page_texts)
            avg_conf = total_conf / processed if processed else 0.0

            return {
                "text": full_text,
                "confidence": avg_conf,
                "pages_processed": processed,
                "total_pages": total_pages,
                "status": "success",
            }

        except Exception as exc:
            logger.error("PDF OCR failed for %s: %s", pdf_path, exc)
            return {
                "text": "",
                "confidence": 0.0,
                "pages_processed": 0,
                "total_pages": 0,
                "status": "failed",
                "error": str(exc),
            }

    def _preprocess(self, image: Image.Image) -> Image.Image:
        try:
            if image.mode != "L":
                image = image.convert("RGB").convert("L")

            w, h = image.size
            long_edge = max(w, h)
            if long_edge < self._MIN_LONG_EDGE:
                scale = self._MIN_LONG_EDGE / long_edge
                image = image.resize(
                    (int(w * scale), int(h * scale)), Image.LANCZOS
                )

            image = ImageEnhance.Contrast(image).enhance(2.0)

            arr = np.array(image, dtype=np.uint8)
            thr = self._otsu_threshold(arr)
            binary = (arr > thr).astype(np.uint8) * 255
            image = Image.fromarray(binary)

            image = image.filter(ImageFilter.MedianFilter(size=3))
            return image

        except Exception as exc:
            logger.warning("Preprocessing failed (returning original): %s", exc)
            return image

    @staticmethod
    def _otsu_threshold(gray: np.ndarray) -> int:
        counts = np.bincount(gray.ravel(), minlength=256).astype(np.float64)
        total = float(gray.size)
        total_sum = float(np.dot(np.arange(256, dtype=np.float64), counts))

        sum_bg = weight_bg = 0.0
        best_thr = 0
        best_var = 0.0

        for t in range(256):
            weight_bg += counts[t]
            if weight_bg == 0:
                continue
            weight_fg = total - weight_bg
            if weight_fg == 0:
                break
            sum_bg += t * counts[t]
            mean_bg = sum_bg / weight_bg
            mean_fg = (total_sum - sum_bg) / weight_fg
            var = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
            if var > best_var:
                best_var = var
                best_thr = t

        return best_thr

    def _ocr_page(
        self,
        page_num: int,
        img: Image.Image,
        total_pages: int,
    ) -> Dict[str, Any]:
        logger.info("OCR processing page %d/%d", page_num + 1, total_pages)
        img_prep = self._preprocess(img)

        if self.reader:
            result = self._page_to_markdown(img_prep)
            if result["text"]:
                result["text"] = f"## Page {page_num + 1}\n\n{result['text']}"
                return result
            logger.warning("OCR page %d empty — retrying", page_num + 1)
            _flush_gpu_cache()
            time.sleep(0.1)
            result = self._page_to_markdown(img_prep)
            if result["text"]:
                result["text"] = f"## Page {page_num + 1}\n\n{result['text']}"
                return result
            logger.warning("OCR page %d: empty after retry — skipping", page_num + 1)
            return {"text": "", "confidence": 0.0}

        if os.environ.get("USE_TESSERACT") == "1":
            r = self._tesseract(img_prep)
            if r.get("text"):
                r["text"] = f"## Page {page_num + 1}\n\n{r['text']}"
            return r

        logger.error("No OCR engine for page %d", page_num + 1)
        return {"text": "", "confidence": 0.0}

    def _page_to_markdown(self, image: Image.Image) -> Dict[str, Any]:
        if not self.reader:
            raise RuntimeError("EasyOCR not initialised")

        try:
            arr = np.array(image, dtype=np.uint8)
            page_h, page_w = arr.shape[:2]

            detections = self.reader.readtext(
                arr,
                detail=1,
                paragraph=False,
                width_ths=0.9,
                height_ths=0.5,
                text_threshold=0.7,
                low_text=0.4,
                batch_size=32,
                workers=0,
            )

            if not detections:
                return {"text": "", "confidence": 0.0}

            detections = [d for d in detections if d[2] >= 0.35]
            if not detections:
                return {"text": "", "confidence": 0.0}

            confs = [d[2] for d in detections]
            avg_conf = sum(confs) / len(confs) * 100

            lines = self._group_into_lines(detections, page_h)
            markdown = self._lines_to_markdown(lines, page_h)
            clean = self._clean_text(markdown)

            return {"text": clean, "confidence": avg_conf}

        except Exception as exc:
            logger.error("EasyOCR page extraction failed: %s", exc)
            return {"text": "", "confidence": 0.0}

    def _group_into_lines(
        self,
        detections: List[tuple],
        page_height: int,
    ) -> List[List[tuple]]:
        if not detections:
            return []

        tolerance = max(8, int(page_height * 0.025))
        sorted_dets = sorted(detections, key=lambda d: d[0][0][1])

        lines: List[List[tuple]] = []
        current_line = [sorted_dets[0]]
        current_y = float(sorted_dets[0][0][0][1])

        for det in sorted_dets[1:]:
            y = float(det[0][0][1])
            if abs(y - current_y) <= tolerance:
                current_line.append(det)
            else:
                lines.append(current_line)
                current_line = [det]
                current_y = y

        if current_line:
            lines.append(current_line)

        for line in lines:
            line.sort(key=lambda d: d[0][0][0])

        return lines

    def _lines_to_markdown(
        self,
        lines: List[List[tuple]],
        page_height: int,
    ) -> str:
        if not lines:
            return ""

        heights: List[float] = []
        for line in lines:
            tops = [d[0][0][1] for d in line]
            bots = [d[0][2][1] for d in line]
            h = max(bots) - min(tops)
            if h > 0:
                heights.append(h)

        if heights:
            heights_sorted = sorted(heights)
            median_lh = float(heights_sorted[len(heights_sorted) // 2])
        else:
            median_lh = 20.0

        para_gap = median_lh * 1.5

        line_texts: List[str] = []
        line_ys: List[float] = []
        for line in lines:
            text = " ".join(d[1] for d in line).strip()
            if text:
                line_texts.append(text)
                line_ys.append(float(line[0][0][0][1]))

        if not line_texts:
            return ""

        output: List[str] = []
        for i, text in enumerate(line_texts):
            if i > 0 and (line_ys[i] - line_ys[i - 1]) > para_gap:
                output.append("")

            words = text.split()
            alpha = [c for c in text if c.isalpha()]
            upper_ratio = (
                sum(c.isupper() for c in alpha) / len(alpha)
                if alpha else 0.0
            )
            is_heading = (
                1 <= len(words) <= 7
                and upper_ratio > 0.70
                and len(text) < 80
            )

            if is_heading:
                output.append(f"### {text}")
            else:
                output.append(text)

        return "\n".join(output)

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""

        cleaned: List[str] = []
        seen_lines: Set[str] = set()

        for raw in text.split("\n"):
            line = "".join(ch for ch in raw if ch.isprintable() or ch == "\t")
            line = " ".join(line.split())

            key = line.lower().strip()
            if not key:
                if cleaned and cleaned[-1] != "":
                    cleaned.append("")
                continue

            if key in seen_lines:
                continue
            seen_lines.add(key)

            prefix = ""
            body = line
            if line.startswith("#"):
                parts = line.split(" ", 1)
                if len(parts) == 2 and all(c == "#" for c in parts[0]):
                    prefix = parts[0] + " "
                    body = parts[1]

            words = body.split()
            deduped: List[str] = []
            i = 0
            while i < len(words):
                deduped.append(words[i])
                j = i + 1
                while j < len(words) and words[j].lower() == words[i].lower():
                    j += 1
                i = j

            cleaned.append(prefix + " ".join(deduped))

        return "\n".join(cleaned).strip()

    def _tesseract(self, image: Image.Image) -> Dict[str, Any]:
        try:
            import pytesseract
            raw = pytesseract.image_to_string(np.array(image), lang="eng")
            return {
                "text": self._clean_text(raw.strip()),
                "confidence": 60.0,
                "status": "success",
            }
        except Exception as exc:
            logger.error("Tesseract extraction failed: %s", exc)
            return {"text": "", "confidence": 0.0, "status": "failed", "error": str(exc)}

    def _render_parallel(
        self,
        pdf_path: str,
        page_numbers: List[int],
    ) -> List[Tuple[int, Image.Image]]:
        if not page_numbers:
            return []

        scale = self.PDF_DPI / 72.0

        def _render(pn: int) -> Tuple[int, Image.Image]:
            with fitz.open(pdf_path) as doc:
                page = doc[pn]
                pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            return (pn, img)

        max_workers = min(8, len(page_numbers))
        rendered: Dict[int, Image.Image] = {}

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_render, p): p for p in page_numbers}
            for future in as_completed(futures):
                try:
                    pn, img = future.result()
                    rendered[pn] = img
                except Exception as exc:
                    logger.error("Render failed page %d: %s", futures[future], exc)

        return [(p, rendered[p]) for p in sorted(rendered)]
