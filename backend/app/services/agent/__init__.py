"""Agent service — multi-step autonomous task execution with tools.

This module provides a complete agent execution pipeline for:
- Intent detection and task classification
- Intelligent tool selection
- Sandboxed code execution  
- Artifact detection and management
- Result validation and synthesis

Components:
- state.py: Enhanced agent state management
- tool_selector.py: Intelligent tool selection
- execution_engine.py: Tool execution with error handling
- artifact_detector.py: File detection and categorization
- result_validator.py: Result validation and summary generation
- pipeline.py: Main orchestration pipeline
- schemas.py: Pydantic models
- tools.py: Tool implementations
"""

from app.services.agent.pipeline import stream_agent
from app.services.agent.state import (
    AgentExecutionState,
    create_agent_state,
    ExecutionPhase,
    ArtifactCategory,
    DatasetMetadata,
    ModelMetadata,
)
from app.services.agent.tool_selector import (
    TaskType,
    classify_task,
    select_tool,
    generate_execution_plan,
)
from app.services.agent.execution_engine import (
    ExecutionEngine,
    ExecutionResult,
    execute_tool_step,
)
from app.services.agent.artifact_detector import (
    ArtifactDetector,
    detect_output_files,
    classify_artifact,
)
from app.services.agent.result_validator import (
    ResultValidator,
    SummaryGenerator,
    ValidationResult,
    ExecutionSummary,
)
from app.services.agent.schemas import (
    AgentPlan,
    AgentState,
    PlanStep,
    StepResult,
)
from app.services.agent.tools import (
    AgentContext,
    ToolOutput,
    TOOL_REGISTRY,
)

__all__ = [
    # Pipeline
    "stream_agent",
    # State
    "AgentExecutionState",
    "create_agent_state",
    "ExecutionPhase",
    "ArtifactCategory",
    "DatasetMetadata",
    "ModelMetadata",
    # Tool Selection
    "TaskType",
    "classify_task",
    "select_tool",
    "generate_execution_plan",
    # Execution
    "ExecutionEngine",
    "ExecutionResult",
    "execute_tool_step",
    # Artifacts
    "ArtifactDetector",
    "detect_output_files",
    "classify_artifact",
    # Validation
    "ResultValidator",
    "SummaryGenerator",
    "ValidationResult",
    "ExecutionSummary",
    # Schemas
    "AgentPlan",
    "AgentState",
    "PlanStep",
    "StepResult",
    # Tools
    "AgentContext",
    "ToolOutput",
    "TOOL_REGISTRY",
]
