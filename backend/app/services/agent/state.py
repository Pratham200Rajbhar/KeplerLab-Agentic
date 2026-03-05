"""Agent State Management — Enhanced context tracking for autonomous agent execution.

Tracks:
- User query and intent
- Execution plan and progress
- Tool usage and outputs
- Generated artifacts
- Dataset metadata
- Model training results
- Error history for repair loop detection
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ExecutionPhase(str, Enum):
    """Current phase of agent execution."""
    INIT = "init"
    PLANNING = "planning"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    FAILED = "failed"


class ArtifactCategory(str, Enum):
    """Categories for artifact grouping."""
    CHART = "chart"
    TABLE = "table"
    MODEL = "model"
    REPORT = "report"
    DATASET = "dataset"
    FILE = "file"


@dataclass
class DatasetMetadata:
    """Metadata about a loaded/analyzed dataset."""
    name: str
    rows: int = 0
    columns: int = 0
    column_names: List[str] = field(default_factory=list)
    dtypes: Dict[str, str] = field(default_factory=dict)
    missing_values: Dict[str, int] = field(default_factory=dict)
    summary_stats: Dict[str, Any] = field(default_factory=dict)
    loaded_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "rows": self.rows,
            "columns": self.columns,
            "column_names": self.column_names,
            "dtypes": self.dtypes,
            "missing_values": self.missing_values,
            "summary_stats": self.summary_stats,
            "loaded_at": self.loaded_at,
        }


@dataclass
class ModelMetadata:
    """Metadata about a trained ML model."""
    name: str
    model_type: str = ""  # RandomForest, XGBoost, etc.
    algorithm: str = ""
    accuracy: float = 0.0
    metrics: Dict[str, float] = field(default_factory=dict)  # precision, recall, f1, etc.
    features_used: List[str] = field(default_factory=list)
    target_column: str = ""
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    trained_at: str = ""
    file_path: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "model_type": self.model_type,
            "algorithm": self.algorithm,
            "accuracy": self.accuracy,
            "metrics": self.metrics,
            "features_used": self.features_used,
            "target_column": self.target_column,
            "hyperparameters": self.hyperparameters,
            "trained_at": self.trained_at,
            "file_path": self.file_path,
        }


@dataclass  
class ErrorRecord:
    """Record of an error encountered during execution."""
    step_index: int
    error_type: str
    error_message: str
    code_snippet: str = ""
    timestamp: str = ""
    repair_attempted: bool = False
    repair_successful: bool = False


@dataclass
class StepProgress:
    """Progress information for a single execution step."""
    index: int
    tool: str
    description: str
    status: str = "pending"  # pending, running, completed, failed
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: int = 0
    summary: str = ""
    error: Optional[str] = None


@dataclass
class AgentExecutionState:
    """Complete runtime state of an agent execution.
    
    This state is maintained throughout the execution lifecycle and
    used for:
    - Streaming progress updates to frontend
    - Decision making during execution
    - Error recovery and repair
    - Context for follow-up queries
    - Final result synthesis
    """
    
    # Identity
    session_id: str = ""
    user_id: str = ""
    notebook_id: str = ""
    
    # Query and Intent
    user_query: str = ""
    detected_intent: str = ""
    intent_confidence: float = 0.0
    
    # Execution Control
    phase: ExecutionPhase = ExecutionPhase.INIT
    current_step_index: int = 0
    max_iterations: int = 10
    iteration: int = 0
    token_budget: int = 50000
    total_tokens: int = 0
    
    # Plan
    execution_plan: List[Dict[str, Any]] = field(default_factory=list)
    step_progress: List[StepProgress] = field(default_factory=list)
    
    # Tool Results
    tools_used: List[str] = field(default_factory=list)
    tool_outputs: List[Dict[str, Any]] = field(default_factory=list)
    
    # Artifacts
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    artifacts_by_category: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    
    # Context Awareness
    datasets: List[DatasetMetadata] = field(default_factory=list)
    models: List[ModelMetadata] = field(default_factory=list)
    charts_generated: List[str] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    
    # Code Execution
    generated_code: List[Dict[str, str]] = field(default_factory=list)  # {step, code, language}
    execution_logs: List[str] = field(default_factory=list)
    
    # Error Tracking
    errors: List[ErrorRecord] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3
    last_error_hash: str = ""  # For detecting repeated errors
    
    # Timing
    started_at: str = ""
    completed_at: str = ""
    elapsed_seconds: float = 0.0
    
    # Workspace
    work_dir: str = ""
    
    def mark_started(self) -> None:
        """Mark execution as started."""
        self.started_at = datetime.utcnow().isoformat()
        self.phase = ExecutionPhase.PLANNING
    
    def mark_completed(self, success: bool = True) -> None:
        """Mark execution as completed."""
        self.completed_at = datetime.utcnow().isoformat()
        self.phase = ExecutionPhase.COMPLETED if success else ExecutionPhase.FAILED
        if self.started_at:
            start = datetime.fromisoformat(self.started_at)
            end = datetime.fromisoformat(self.completed_at)
            self.elapsed_seconds = (end - start).total_seconds()
    
    def add_step_progress(self, step: StepProgress) -> None:
        """Add or update step progress."""
        # Update existing or add new
        for i, existing in enumerate(self.step_progress):
            if existing.index == step.index:
                self.step_progress[i] = step
                return
        self.step_progress.append(step)
    
    def start_step(self, index: int, tool: str, description: str) -> None:
        """Mark a step as started."""
        self.current_step_index = index
        step = StepProgress(
            index=index,
            tool=tool,
            description=description,
            status="running",
            started_at=datetime.utcnow().isoformat(),
        )
        self.add_step_progress(step)
        if tool not in self.tools_used:
            self.tools_used.append(tool)
    
    def complete_step(
        self,
        index: int,
        summary: str,
        duration_ms: int,
        error: Optional[str] = None,
    ) -> None:
        """Mark a step as completed."""
        for step in self.step_progress:
            if step.index == index:
                step.status = "failed" if error else "completed"
                step.completed_at = datetime.utcnow().isoformat()
                step.duration_ms = duration_ms
                step.summary = summary
                step.error = error
                return
    
    def add_artifact(self, artifact: Dict[str, Any]) -> None:
        """Add an artifact and categorize it."""
        self.artifacts.append(artifact)
        
        # Categorize
        category = artifact.get("category", "file")
        if category not in self.artifacts_by_category:
            self.artifacts_by_category[category] = []
        self.artifacts_by_category[category].append(artifact)
        
        # Track files
        filename = artifact.get("filename", "")
        if filename:
            self.files_created.append(filename)
            
            # Track charts
            if artifact.get("display_type") == "image":
                self.charts_generated.append(filename)
    
    def add_dataset(self, dataset: DatasetMetadata) -> None:
        """Add dataset metadata."""
        self.datasets.append(dataset)
    
    def add_model(self, model: ModelMetadata) -> None:
        """Add trained model metadata."""
        self.models.append(model)
    
    def record_error(
        self,
        step_index: int,
        error_type: str,
        error_message: str,
        code_snippet: str = "",
    ) -> None:
        """Record an execution error."""
        error = ErrorRecord(
            step_index=step_index,
            error_type=error_type,
            error_message=error_message,
            code_snippet=code_snippet,
            timestamp=datetime.utcnow().isoformat(),
        )
        self.errors.append(error)
        
        # Create error hash for duplicate detection
        import hashlib
        error_hash = hashlib.md5(
            f"{error_type}:{error_message}".encode()
        ).hexdigest()[:16]
        
        if error_hash == self.last_error_hash:
            # Same error repeated — increment retry but don't reset
            pass
        else:
            self.last_error_hash = error_hash
    
    def is_error_repeated(self) -> bool:
        """Check if the same error has occurred twice (for stopping retries)."""
        if len(self.errors) < 2:
            return False
        
        last_two = self.errors[-2:]
        return (
            last_two[0].error_type == last_two[1].error_type and
            last_two[0].error_message == last_two[1].error_message
        )
    
    def can_retry(self) -> bool:
        """Check if we can attempt another retry."""
        if self.retry_count >= self.max_retries:
            return False
        if self.is_error_repeated():
            return False
        return True
    
    def add_generated_code(self, step: int, code: str, language: str = "python") -> None:
        """Track generated code for technical details."""
        self.generated_code.append({
            "step": step,
            "code": code,
            "language": language,
        })
    
    def add_execution_log(self, log: str) -> None:
        """Add an execution log entry."""
        timestamp = datetime.utcnow().isoformat()
        self.execution_logs.append(f"[{timestamp}] {log}")
    
    def get_context_summary(self) -> str:
        """Get a summary of current context for LLM prompts."""
        parts = []
        
        if self.datasets:
            ds_info = []
            for ds in self.datasets:
                ds_info.append(f"- {ds.name}: {ds.rows} rows, {ds.columns} columns")
            parts.append(f"Loaded datasets:\n" + "\n".join(ds_info))
        
        if self.models:
            model_info = []
            for m in self.models:
                model_info.append(f"- {m.name} ({m.model_type}): accuracy {m.accuracy:.2%}")
            parts.append(f"Trained models:\n" + "\n".join(model_info))
        
        if self.charts_generated:
            parts.append(f"Charts generated: {', '.join(self.charts_generated)}")
        
        return "\n\n".join(parts) if parts else "No prior context."
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize state to dictionary."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "notebook_id": self.notebook_id,
            "user_query": self.user_query,
            "detected_intent": self.detected_intent,
            "intent_confidence": self.intent_confidence,
            "phase": self.phase.value,
            "current_step_index": self.current_step_index,
            "iteration": self.iteration,
            "total_tokens": self.total_tokens,
            "execution_plan": self.execution_plan,
            "tools_used": self.tools_used,
            "artifacts": self.artifacts,
            "artifacts_by_category": self.artifacts_by_category,
            "datasets": [ds.to_dict() for ds in self.datasets],
            "models": [m.to_dict() for m in self.models],
            "charts_generated": self.charts_generated,
            "files_created": self.files_created,
            "errors": [
                {
                    "step_index": e.step_index,
                    "error_type": e.error_type,
                    "error_message": e.error_message,
                    "timestamp": e.timestamp,
                }
                for e in self.errors
            ],
            "retry_count": self.retry_count,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "elapsed_seconds": self.elapsed_seconds,
        }
    
    def to_json(self) -> str:
        """Serialize state to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


# Factory function for creating agent state
def create_agent_state(
    session_id: str,
    user_id: str,
    notebook_id: str,
    user_query: str,
    work_dir: str,
    max_iterations: int = 10,
    max_retries: int = 3,
) -> AgentExecutionState:
    """Create a new agent execution state."""
    return AgentExecutionState(
        session_id=session_id,
        user_id=user_id,
        notebook_id=notebook_id,
        user_query=user_query,
        work_dir=work_dir,
        max_iterations=max_iterations,
        max_retries=max_retries,
    )
