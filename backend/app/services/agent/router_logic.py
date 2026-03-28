from __future__ import annotations

from typing import List


def should_force_rag_first(material_ids: List[str]) -> bool:
    """Central policy helper: selected materials require retrieval-first behavior."""
    return bool(material_ids)
