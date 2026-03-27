from __future__ import annotations

import ipaddress
import asyncio
import logging
import socket
import uuid
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.services.chat_v2.schemas import ToolResult
from app.services.llm_service.llm import get_llm
from app.services.llm_service.structured_invoker import parse_json_robust
from app.services.tools.research_tool import execute as run_research_tool
from app.services.tools.web_search_tool import execute as run_web_search_tool

logger = logging.getLogger(__name__)

MAX_RESOURCES = 10
TOOL_TIMEOUT_SECONDS = 35


async def _collect_tool_result(stream) -> Optional[ToolResult]:
    result: Optional[ToolResult] = None
    async for item in stream:
        if isinstance(item, ToolResult):
            result = item
    return result


def _infer_resource_type(title: str, url: str, declared_type: str = "") -> str:
    kind = (declared_type or "").strip().lower()
    if kind in {"pdf", "youtube", "article", "audio", "video", "document", "slides"}:
        return kind

    lower_url = (url or "").lower()
    lower_title = (title or "").lower()
    audio_exts = (".mp3", ".wav", ".m4a", ".aac", ".ogg")
    video_exts = (".mp4", ".webm", ".mkv", ".avi", ".mov")
    doc_exts = (".doc", ".docx", ".txt", ".md", ".rtf")
    slide_exts = (".ppt", ".pptx")

    if "youtube.com" in lower_url or "youtu.be" in lower_url:
        return "youtube"
    if "podcast" in lower_url or "soundcloud.com" in lower_url or lower_url.endswith(audio_exts):
        return "audio"
    if lower_url.endswith(video_exts):
        return "video"
    if lower_url.endswith(".pdf") or "pdf" in lower_title:
        return "pdf"
    if lower_url.endswith(doc_exts):
        return "document"
    if lower_url.endswith(slide_exts):
        return "slides"
    return "article"


async def _is_safe_public_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False
        if not parsed.hostname:
            return False
        if parsed.hostname in {"localhost"}:
            return False

        try:
            ip = ipaddress.ip_address(parsed.hostname)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
            return True
        except ValueError:
            pass

        loop = asyncio.get_running_loop()
        resolved_ips = await loop.run_in_executor(None, socket.getaddrinfo, parsed.hostname, None)
        for _, _, _, _, addr in resolved_ips:
            ip = ipaddress.ip_address(addr[0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
        return True
    except Exception:
        return False


async def _sanitize_resources(resources: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    cleaned: List[Dict[str, str]] = []
    seen_urls: set[str] = set()

    for item in resources:
        title = str(item.get("title", "")).strip()
        url = str(item.get("url", "")).strip()
        if not title or not url or url in seen_urls:
            continue
        if not await _is_safe_public_url(url):
            continue

        seen_urls.add(url)
        cleaned.append(
            {
                "type": _infer_resource_type(title, url, str(item.get("type", ""))),
                "title": title[:220],
                "url": url,
            }
        )
        if len(cleaned) >= MAX_RESOURCES:
            break

    return cleaned


async def build_resources(
    query: str,
    user_id: str,
    notebook_id: Optional[str] = None,
) -> Dict[str, Any]:
    async def _run_with_timeout(coro_stream):
        try:
            return await asyncio.wait_for(_collect_tool_result(coro_stream), timeout=TOOL_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            logger.warning("AI resource builder tool timed out after %ss", TOOL_TIMEOUT_SECONDS)
            return None

    research_query = (
        f"{query}\n\n"
        "Focus on high-quality PDFs, YouTube explainers, audio lectures/podcasts, "
        "and authoritative study articles or documents."
    )

    web_result, research_result = await asyncio.gather(
        _run_with_timeout(run_web_search_tool(query=query, user_id=user_id)),
        _run_with_timeout(
            run_research_tool(
                query=research_query,
                user_id=user_id,
                notebook_id=notebook_id,
                session_id=f"ai-resource-builder-{uuid.uuid4().hex[:10]}",
                material_ids=[],
            )
        )
    )

    web_context = (web_result.content if web_result and web_result.success else "")[:16000]
    research_context = (research_result.content if research_result and research_result.success else "")[:16000]
    web_sources = (web_result.metadata.get("sources", []) if web_result else [])[:15]

    llm = get_llm(mode="structured", temperature=0.1)
    prompt = (
        "You are an AI Resource Builder.\n"
        "Your job is to:\n"
        "- Search the web\n"
        "- Find high-quality PDFs, YouTube videos, audio resources, and articles/documents\n"
        "- Extract useful information\n"
        "- Generate structured study notes\n\n"
        "Use the provided web_search and research outputs as your source of truth.\n"
        "Prefer educational, reputable sources and avoid low-quality SEO/spam pages.\n"
        f"Limit resources to at most {MAX_RESOURCES}.\n"
        "Return JSON only with this shape:\n"
        "{\n"
        '  "resources": [{"type": "pdf | youtube | article | audio | video | document | slides", "title": "...", "url": "..."}],\n'
        '  "notes": "structured notes"\n'
        "}\n\n"
        f"User Query:\n{query}\n\n"
        f"Web Search Sources (metadata):\n{web_sources}\n\n"
        f"Web Search Extracted Context:\n{web_context}\n\n"
        f"Research Context:\n{research_context}\n"
    )

    response = await llm.ainvoke(prompt)
    raw = getattr(response, "content", str(response))

    parsed = parse_json_robust(raw)
    raw_resources = parsed.get("resources", []) if isinstance(parsed, dict) else []
    raw_notes = parsed.get("notes", "") if isinstance(parsed, dict) else ""

    resources = await _sanitize_resources(raw_resources if isinstance(raw_resources, list) else [])
    notes = str(raw_notes).strip()
    if not notes:
        notes = "No notes were generated. Please refine the query and try again."

    if not resources and web_sources:
        resources = await _sanitize_resources(
            [
                {
                    "type": _infer_resource_type(src.get("title", ""), src.get("url", "")),
                    "title": src.get("title", "Untitled source"),
                    "url": src.get("url", ""),
                }
                for src in web_sources
            ]
        )

    return {
        "resources": resources,
        "notes": notes,
        "meta": {
            "intent": "AGENT",
            "tools_used": ["web_search", "research"],
            "resource_count": len(resources),
        },
    }
