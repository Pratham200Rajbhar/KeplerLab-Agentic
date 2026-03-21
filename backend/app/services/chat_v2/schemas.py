from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

class Capability(str, Enum):

    NORMAL_CHAT = "NORMAL_CHAT"
    RAG = "RAG"
    CODE_EXECUTION = "CODE_EXECUTION"
    WEB_SEARCH = "WEB_SEARCH"
    WEB_RESEARCH = "WEB_RESEARCH"
    AGENT = "AGENT"

class ChatRequest(BaseModel):

    message: str = Field(..., min_length=1, max_length=50000)
    notebook_id: str
    session_id: Optional[str] = None
    material_id: Optional[str] = None
    material_ids: Optional[List[str]] = None
    stream: Optional[bool] = True
    intent_override: Optional[str] = None

class BlockFollowupRequest(BaseModel):
    block_id: str
    question: str = Field(..., min_length=1, max_length=10000)
    action: str = "ask"
    selection: Optional[str] = None

class SuggestionRequest(BaseModel):
    partial_input: str = Field(..., min_length=1, max_length=1000)
    notebook_id: str

class EmptyStateSuggestionRequest(BaseModel):
    material_ids: List[str] = Field(default_factory=list)
    notebook_id: Optional[str] = None

class CreateSessionRequest(BaseModel):
    notebook_id: str
    title: Optional[str] = "New Chat"

class OptimizePromptsRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=5000)
    count: int = Field(default=4, ge=2, le=6)

class ToolResult(BaseModel):

    tool_name: str
    success: bool = True
    content: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)

class LLMMessage(BaseModel):

    role: str
    content: str
