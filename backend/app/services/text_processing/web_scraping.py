from __future__ import annotations

import logging
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

from .file_detector import FileTypeDetector

_SELENIUM_DOMAINS = frozenset({
    "twitter.com", "x.com", "facebook.com", "instagram.com",
    "linkedin.com", "reddit.com", "tiktok.com",
})

class WebScrapingService:

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(_DEFAULT_HEADERS)

    def detect_url_type(self, url: str) -> Dict[str, Any]:
        try:
            resp = self.session.head(url, timeout=10, allow_redirects=True)
            if resp.status_code in (403, 404, 405):
                resp = self.session.get(url, timeout=10, stream=True, allow_redirects=True)
                resp.close()

            ct = resp.headers.get("Content-Type", "").lower().split(";")[0].strip()
            cl = 0
            try:
                cl = int(resp.headers.get("Content-Length", 0))
            except ValueError:
                pass

            category = FileTypeDetector.SUPPORTED_TYPES.get(ct)
            if not category:
                cat = FileTypeDetector._mime_to_category(ct)
                category = cat if cat != "unknown" else "web"

            if category == "web":
                ext_cat = FileTypeDetector.detect_from_extension(url)
                if ext_cat:
                    category = ext_cat

            return {
                "content_type":   ct,
                "content_length": cl,
                "category":       category,
                "status":         "success",
            }

        except Exception as exc:
            logger.debug("Header detection failed for %s: %s — using URL extension", url, exc)

        ext_cat = FileTypeDetector.detect_from_extension(url)
        if ext_cat:
            return {
                "content_type":   "unknown",
                "content_length": 0,
                "category":       ext_cat,
                "status":         "extension_fallback",
            }

        return {"status": "failed", "error": "Could not determine URL type", "category": "web"}

    def download_url_to_temp(self, url: str, max_size_mb: int = 100) -> Optional[str]:
        max_bytes = max_size_mb * 1024 * 1024
        ext = Path(urlparse(url).path.split("?")[0]).suffix or ".tmp"

        for attempt in range(1, 4):
            try:
                resp = self.session.get(url, timeout=60, stream=True, allow_redirects=True)
                resp.raise_for_status()

                cl = int(resp.headers.get("Content-Length", 0))
                if cl and cl > max_bytes:
                    raise ValueError(f"Remote file is {cl / 1e6:.1f} MB — exceeds {max_size_mb} MB limit")

                with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
                    downloaded = 0
                    for chunk in resp.iter_content(chunk_size=65536):
                        if chunk:
                            tmp.write(chunk)
                            downloaded += len(chunk)
                            if downloaded > max_bytes:
                                tmp.close()
                                os.remove(tmp.name)
                                raise ValueError("Download exceeded size limit mid-stream")
                    return tmp.name

            except ValueError:
                raise
            except Exception as exc:
                backoff = 2 ** (attempt - 1)
                logger.warning(
                    "Download attempt %d/%d failed for %s: %s (retry in %ds)",
                    attempt, 3, url, exc, backoff,
                )
                if attempt < 3:
                    time.sleep(backoff)

        logger.error("All download attempts failed for %s", url)
        return None

    def extract_content_from_url(self, url: str) -> Dict[str, Any]:
        if not _is_valid_url(url):
            return _web_fail(url, f"Invalid URL: {url}")

        from app.core.config import settings
        if settings.WEB_SCRAPE_ENDPOINT:
            try:
                resp = requests.post(
                    settings.WEB_SCRAPE_ENDPOINT,
                    json={"url": url},
                    timeout=30
                )
                resp.raise_for_status()
                data = resp.json()
                text = data.get("text") or data.get("content", "")
                title = data.get("title") or url
                
                if text:
                    return {
                        "url": url,
                        "title": title,
                        "text": _clean_text(text),
                        "method": "external_endpoint",
                        "status": "success",
                        "word_count": len(text.split())
                    }
            except Exception as e:
                logger.warning(f"External web scrape failed for {url}: {e}. Falling back to default.")

        method = "selenium" if _needs_selenium(url) else "requests"

        result = self._scrape_with_retry(url, method)

        if result["status"] == "failed" and method == "requests":
            err = str(result.get("error", "")).lower()
            if any(x in err for x in ("403", "429", "forbidden", "cloudflare", "rate", "blocked",
                                       "connection", "timeout", "ssl", "5")):
                logger.info("Retrying %s with Selenium (reason: %s)", url, result.get("error"))
                result = self._scrape_with_retry(url, "selenium")

        if result["status"] == "success":
            result["text"] = _clean_text(result.get("text", ""))
            result["word_count"] = len(result["text"].split())
        return result

    def _scrape_with_retry(self, url: str, method: str, max_attempts: int = 3) -> Dict[str, Any]:
        last_err = ""
        for attempt in range(1, max_attempts + 1):
            try:
                if method == "selenium":
                    result = self._scrape_with_selenium(url)
                else:
                    result = self._scrape_with_requests(url)

                if result["status"] == "success":
                    return result

                last_err = str(result.get("error", ""))

            except Exception as exc:
                last_err = str(exc)

            backoff = 2 ** (attempt - 1)
            if attempt < max_attempts:
                logger.debug("Scrape attempt %d/%d failed (%s): retrying in %ds", attempt, max_attempts, last_err, backoff)
                time.sleep(backoff)

        return _web_fail(url, last_err or "All scrape attempts failed", method)

    def _scrape_with_requests(self, url: str, max_bytes: int = 4 * 1024 * 1024) -> Dict[str, Any]:
        resp = self.session.get(url, timeout=25, stream=True)
        resp.raise_for_status()

        content = b""
        for chunk in resp.iter_content(chunk_size=65536):
            content += chunk
            if len(content) >= max_bytes:
                break

        soup = BeautifulSoup(content, "html.parser")
        title = (soup.find("title") or object())
        title_text = title.get_text().strip() if hasattr(title, "get_text") else url

        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "iframe", "noscript", "form"]):
            tag.decompose()

        text = _extract_structured_text(soup)
        if not text.strip():
            return _web_fail(url, "Empty page content", "requests")

        return {"url": url, "title": title_text, "text": text, "method": "requests", "status": "success",
                "response_code": resp.status_code}

    def _scrape_with_selenium(self, url: str) -> Dict[str, Any]:
        driver = None
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import WebDriverWait
            from webdriver_manager.chrome import ChromeDriverManager

            opts = Options()
            opts.add_argument("--headless=new")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--window-size=1920,1080")
            opts.add_argument("--disable-blink-features=AutomationControlled")
            opts.add_argument(f"user-agent={_DEFAULT_HEADERS['User-Agent']}")
            opts.add_experimental_option("excludeSwitches", ["enable-automation"])
            opts.add_experimental_option("useAutomationExtension", False)

            service = Service(ChromeDriverManager().install())
            driver  = webdriver.Chrome(service=service, options=opts)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            driver.get(url)
            WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            time.sleep(2)

            title  = driver.title or url
            soup   = BeautifulSoup(driver.page_source, "html.parser")
            for tag in soup(["script", "style", "nav", "header", "footer", "aside", "iframe", "noscript"]):
                tag.decompose()
            text = _extract_structured_text(soup)

            return {"url": url, "title": title, "text": text, "method": "selenium", "status": "success"}

        except Exception as exc:
            return _web_fail(url, str(exc), "selenium")
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

    def get_page_title_fast(self, url: str, max_bytes: int = 65536, timeout: int = 8) -> Optional[str]:
        try:
            if not _is_valid_url(url):
                return None
            resp = self.session.get(url, timeout=timeout, stream=True)
            resp.raise_for_status()
            chunk = b""
            for b in resp.iter_content(chunk_size=4096):
                chunk += b
                if len(chunk) >= max_bytes:
                    break
            soup = BeautifulSoup(chunk.decode("utf-8", errors="ignore"), "html.parser")
            tag = soup.find("title")
            return tag.get_text().strip() or None if tag else None
        except Exception:
            return None

    def get_page_metadata(self, url: str) -> Dict[str, Any]:
        try:
            resp = self.session.get(url, timeout=15)
            soup = BeautifulSoup(resp.content, "html.parser")
            meta: Dict[str, Any] = {
                "url":            url,
                "status_code":    resp.status_code,
                "content_type":   resp.headers.get("content-type", ""),
                "content_length": resp.headers.get("content-length", ""),
                "title":          "",
                "description":    "",
                "keywords":       "",
                "author":         "",
                "language":       "",
            }
            if (t := soup.find("title")):
                meta["title"] = t.get_text().strip()
            for name, key in [("description", "description"), ("keywords", "keywords"), ("author", "author")]:
                if (m := soup.find("meta", attrs={"name": name})):
                    meta[key] = m.get("content", "").strip()
            if (h := soup.find("html")):
                meta["language"] = h.get("lang", "").strip()
            return meta
        except Exception as exc:
            return {"url": url, "error": str(exc)}

def _needs_selenium(url: str) -> bool:
    domain = urlparse(url).netloc.lower()
    return any(d in domain for d in _SELENIUM_DOMAINS)

def _is_valid_url(url: str) -> bool:
    try:
        r = urlparse(url)
        return bool(r.scheme and r.netloc)
    except Exception:
        return False

def _web_fail(url: str, error: str, method: str = "unknown") -> Dict[str, Any]:
    return {"url": url, "title": "", "text": "", "method": method,
            "status": "failed", "error": error, "word_count": 0}

def _extract_structured_text(soup: BeautifulSoup) -> str:
    for sel in ["main", "article", '[role="main"]', ".main-content", ".content",
                ".post-content", ".article-content", ".entry-content", "#main", "#content"]:
        elem = soup.select_one(sel)
        if elem:
            return _elem_to_text(elem)
    body = soup.find("body")
    return _elem_to_text(body) if body else soup.get_text(separator=" ", strip=True)

def _elem_to_text(elem) -> str:
    parts = []
    for tag in elem.descendants:
        if not hasattr(tag, "name") or not tag.name:
            continue
        if tag.name in ("h1",):
            t = tag.get_text(strip=True)
            if t: parts.append(f"\n# {t}\n")
        elif tag.name in ("h2",):
            t = tag.get_text(strip=True)
            if t: parts.append(f"\n## {t}\n")
        elif tag.name in ("h3", "h4", "h5", "h6"):
            t = tag.get_text(strip=True)
            if t: parts.append(f"\n### {t}\n")
        elif tag.name == "li":
            t = tag.get_text(strip=True)
            if t: parts.append(f"- {t}")
        elif tag.name == "p":
            t = tag.get_text(separator=" ", strip=True)
            if t: parts.append(t)
        elif tag.name in ("td", "th"):
            t = tag.get_text(strip=True)
            if t: parts.append(t + " | ")
        elif tag.name == "tr":
            parts.append("")
    return "\n".join(parts)

def _clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ufffd]", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return "\n".join(lines)