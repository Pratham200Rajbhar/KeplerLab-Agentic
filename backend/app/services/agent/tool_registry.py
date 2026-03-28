from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .tools_registry import TOOL_REGISTRY, get_available_tools as _get_available_tools


@dataclass(frozen=True)
class ToolSchema:
    name: str
    required_params: List[str]
    description: str


def get_tool_schemas(has_materials: bool = False) -> Dict[str, ToolSchema]:
    """Return strict, testable tool schemas for planner/executor interoperability."""
    available = _get_available_tools(has_materials)
    return {
        name: ToolSchema(
            name=name,
            required_params=list(spec.required_params),
            description=spec.description,
        )
        for name, spec in available.items()
    }


__all__ = ["TOOL_REGISTRY", "ToolSchema", "get_tool_schemas"]
