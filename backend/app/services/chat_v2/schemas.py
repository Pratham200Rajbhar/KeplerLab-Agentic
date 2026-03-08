"""Chat V2 — Request/response schemas and enums."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Capability modes ──────────────────────────────────────────


class Capability(str, Enum):
    """Capability the router selects for a given request."""

    NORMAL_CHAT = "NORMAL_CHAT"
    RAG = "RAG"
    CODE_EXECUTION = "CODE_EXECUTION"
    WEB_SEARCH = "WEB_SEARCH"
    AGENT = "AGENT"
    WEB_RESEARCH = "WEB_RESEARCH"


# ── API request / response models ─────────────────────────────


class ChatRequest(BaseModel):
    """Incoming chat request from the frontend."""

    message: str = Field(..., min_length=1, max_length=50000)
    notebook_id: str
    session_id: Optional[str] = None
    material_id: Optional[str] = None
    material_ids: Optional[List[str]] = None
    stream: Optional[bool] = True
    intent_override: Optional[str] = None  # AGENT | WEB_RESEARCH | CODE_EXECUTION | WEB_SEARCH


class BlockFollowupRequest(BaseModel):
    block_id: str
    question: str = Field(..., min_length=1, max_length=10000)
    action: str = "ask"


class SuggestionRequest(BaseModel):
    partial_input: str = Field(..., min_length=1, max_length=1000)
    notebook_id: str


class EmptyStateSuggestionRequest(BaseModel):
    material_ids: List[str] = Field(default_factory=list)
    notebook_id: Optional[str] = None


class CreateSessionRequest(BaseModel):
    notebook_id: str
    title: Optional[str] = "New Chat"


# ── Internal data containers ──────────────────────────────────


class ToolResult(BaseModel):
    """Result returned by a tool execution."""

    tool_name: str
    success: bool = True
    content: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)


class LLMMessage(BaseModel):
    """A single message in the LLM context window."""

    role: str  # system | user | assistant
    content: str
