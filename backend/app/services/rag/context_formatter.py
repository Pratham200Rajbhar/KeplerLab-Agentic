from __future__ import annotations

import logging
from collections import OrderedDict
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

_CACHE_MAX_SIZE = 2000
_material_name_cache: OrderedDict[str, str] = OrderedDict()

def _get_material_name_sync(material_id: str) -> str:
    if material_id in _material_name_cache:
        _material_name_cache.move_to_end(material_id)
        return _material_name_cache[material_id]
    return ""

def set_material_name(material_id: str, filename: str) -> None:
    _material_name_cache[material_id] = filename
    _material_name_cache.move_to_end(material_id)
    while len(_material_name_cache) > _CACHE_MAX_SIZE:
        _material_name_cache.popitem(last=False)

def format_context_with_citations(
    chunks: List[Dict],
    max_sources: Optional[int] = None,
) -> str:
    if not chunks:
        return "No relevant context found."
    
    selected_chunks = chunks[:max_sources] if max_sources else chunks
    
    formatted_sections = []
    
    for idx, chunk in enumerate(selected_chunks, start=1):
        text = chunk.get("text", "")
        chunk_id = chunk.get("id", "unknown")
        section_title = chunk.get("section_title", "No section")
        material_id = chunk.get("material_id", None)
        score = chunk.get("score", None)
        
        header_lines = ["-" * 50]
        
        if material_id:
            material_name = (
                chunk.get("filename")
                or _get_material_name_sync(material_id)
                or f"Source-{material_id[:8]}"
            )
            header_lines.append(f"[SOURCE {idx} - Material: {material_name}]")
        else:
            header_lines.append(f"[SOURCE {idx}]")
        
        if section_title and section_title != "No section":
            header_lines.append(f"Section: {section_title}")
        
        header_lines.append(f"Chunk ID: {chunk_id}")
        
        if score is not None:
            header_lines.append(f"Confidence: {score:.2f}")
        
        header_lines.append("")
        header_lines.append("Content:")
        
        formatted_sections.append(
            "\n".join(header_lines) + f"\n{text}\n" + "-" * 50
        )
        
        logger.debug(
            "Formatted SOURCE %d: chunk=%s  material=%s  section=%s  score=%s",
            idx, chunk_id, material_id, section_title, score,
        )

    context = "\n\n".join(formatted_sections)
    logger.info("Formatted %d sources with citation metadata", len(selected_chunks))
    return context
