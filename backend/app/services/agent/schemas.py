"""Agent schemas — Pydantic models for plan, tool results, and agent state."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Plan schemas ─────────────────────────────────────────────

class ToolName(str, Enum):
    rag_tool = "rag_tool"
    python_tool = "python_tool"
    web_search_tool = "web_search_tool"
    research_tool = "research_tool"


class PlanStep(BaseModel):
    """A single step in the agent's execution plan."""
    tool: str = Field(..., description="Tool name: rag_tool, python_tool, web_search_tool, research_tool")
    description: str = Field(..., description="What this step will accomplish")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Key-value inputs for the tool")


class AgentPlan(BaseModel):
    """The full execution plan produced by the planner LLM."""
    steps: List[PlanStep] = Field(..., description="Ordered list of tool steps to execute")


# ── Tool result schemas ──────────────────────────────────────

class RAGToolResult(BaseModel):
    context: str = ""
    chunks_used: int = 0
    sources: List[Dict[str, Any]] = Field(default_factory=list)


class PythonToolResult(BaseModel):
    exit_code: int = -1
    files_produced: List[Dict[str, Any]] = Field(default_factory=list)
    code: str = ""
    error: Optional[str] = None


class WebSearchToolResult(BaseModel):
    results: List[Dict[str, str]] = Field(default_factory=list)


class ResearchToolResult(BaseModel):
    report: str = ""
    sources: List[Dict[str, Any]] = Field(default_factory=list)


# ── Agent state ──────────────────────────────────────────────

class StepResult(BaseModel):
    """Result of a single executed step."""
    step_index: int
    tool: str
    description: str
    summary: str = ""
    duration_ms: int = 0
    code: Optional[str] = None
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


class ReflectionDecision(str, Enum):
    CONTINUE = "continue"
    RESPOND = "respond"


class ReflectionResult(BaseModel):
    decision: ReflectionDecision = ReflectionDecision.RESPOND
    reason: str = ""


class AgentState(BaseModel):
    """Tracks the full mutable state of an agent execution."""
    plan: Optional[AgentPlan] = None
    step_results: List[StepResult] = Field(default_factory=list)
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)
    total_tokens: int = 0
    iteration: int = 0

    # Budget limits
    max_iterations: int = 10
    token_budget: int = 50000
