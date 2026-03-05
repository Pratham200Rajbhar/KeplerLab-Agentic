"""Result Validator & Summary Generator — Validates execution results and generates summaries.

Provides:
- Validation of execution results
- Summary generation from tool outputs
- Result formatting for frontend
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.services.agent.state import AgentExecutionState

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of execution validation."""
    is_valid: bool
    issues: List[str]
    warnings: List[str]
    suggestions: List[str]


@dataclass
class ExecutionSummary:
    """Structured summary of agent execution."""
    title: str
    description: str
    key_results: List[str]
    metrics: Dict[str, Any]
    artifacts_summary: Dict[str, int]
    errors_summary: Optional[str]
    recommendations: List[str]


class ResultValidator:
    """Validates agent execution results."""
    
    def __init__(self, state: AgentExecutionState):
        self.state = state
    
    def validate(self) -> ValidationResult:
        """Validate the current execution state.
        
        Checks:
        - All planned steps executed
        - No critical errors
        - At least some output produced
        - Artifacts are accessible
        
        Returns:
            ValidationResult with issues and suggestions
        """
        issues = []
        warnings = []
        suggestions = []
        
        # Check if any steps were executed
        if not self.state.step_progress:
            issues.append("No execution steps were performed")
        
        # Check for failed steps
        failed_steps = [
            s for s in self.state.step_progress
            if s.status == "failed"
        ]
        if failed_steps:
            warnings.append(f"{len(failed_steps)} step(s) failed during execution")
        
        # Check for critical errors
        critical_errors = [
            e for e in self.state.errors
            if e.error_type in ("SecurityError", "FatalError")
        ]
        if critical_errors:
            issues.append(f"{len(critical_errors)} critical error(s) encountered")
        
        # Check if any output was produced
        has_output = (
            bool(self.state.artifacts) or
            bool(self.state.tool_outputs) or
            bool(self.state.datasets) or
            bool(self.state.models)
        )
        if not has_output:
            warnings.append("No output artifacts or results were generated")
            suggestions.append("Try rephrasing your request or providing more context")
        
        # Check artifact file existence
        missing_artifacts = []
        import os
        for artifact in self.state.artifacts:
            path = artifact.get("path", "")
            if path and not os.path.exists(path):
                missing_artifacts.append(artifact.get("filename", "unknown"))
        
        if missing_artifacts:
            warnings.append(f"Some artifacts may be unavailable: {', '.join(missing_artifacts)}")
        
        # Check for excessive retries
        if self.state.retry_count >= self.state.max_retries:
            warnings.append("Maximum repair attempts were exhausted")
            suggestions.append("The request may need to be simplified")
        
        is_valid = len(issues) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            warnings=warnings,
            suggestions=suggestions,
        )


class SummaryGenerator:
    """Generates execution summaries."""
    
    def __init__(self, state: AgentExecutionState):
        self.state = state
    
    def generate_summary(self) -> ExecutionSummary:
        """Generate a structured summary of execution.
        
        Returns:
            ExecutionSummary with all relevant information
        """
        # Build title
        title = self._generate_title()
        
        # Build description
        description = self._generate_description()
        
        # Extract key results
        key_results = self._extract_key_results()
        
        # Gather metrics
        metrics = self._gather_metrics()
        
        # Summarize artifacts
        artifacts_summary = self._summarize_artifacts()
        
        # Summarize errors
        errors_summary = self._summarize_errors()
        
        # Generate recommendations
        recommendations = self._generate_recommendations()
        
        return ExecutionSummary(
            title=title,
            description=description,
            key_results=key_results,
            metrics=metrics,
            artifacts_summary=artifacts_summary,
            errors_summary=errors_summary,
            recommendations=recommendations,
        )
    
    def _generate_title(self) -> str:
        """Generate a concise title for the execution."""
        if self.state.models:
            model = self.state.models[0]
            return f"{model.model_type or 'ML'} Model Training Complete"
        
        if self.state.datasets:
            return "Dataset Analysis Complete"
        
        if self.state.charts_generated:
            return "Visualization Generated"
        
        if self.state.artifacts:
            return "Task Execution Complete"
        
        return "Execution Complete"
    
    def _generate_description(self) -> str:
        """Generate a human-readable description."""
        parts = []
        
        # Data analysis
        if self.state.datasets:
            ds = self.state.datasets[0]
            parts.append(f"Analyzed dataset with {ds.rows:,} rows and {ds.columns} columns")
        
        # Model training
        if self.state.models:
            model = self.state.models[0]
            acc_str = f"{model.accuracy:.1%}" if model.accuracy else "N/A"
            parts.append(f"Trained {model.model_type or 'ML'} model with accuracy: {acc_str}")
        
        # Charts
        if self.state.charts_generated:
            parts.append(f"Generated {len(self.state.charts_generated)} visualization(s)")
        
        # Files
        if self.state.files_created:
            parts.append(f"Created {len(self.state.files_created)} output file(s)")
        
        if not parts:
            parts.append("Processed your request")
        
        return ". ".join(parts) + "."
    
    def _extract_key_results(self) -> List[str]:
        """Extract key results from execution."""
        results = []
        
        # Dataset insights
        for ds in self.state.datasets:
            if ds.summary_stats:
                results.append(f"Dataset has {ds.rows:,} records across {ds.columns} features")
        
        # Model metrics
        for model in self.state.models:
            if model.accuracy:
                results.append(f"Model accuracy: {model.accuracy:.1%}")
            for metric, value in model.metrics.items():
                if isinstance(value, (int, float)):
                    results.append(f"{metric.replace('_', ' ').title()}: {value:.3f}")
        
        # Tool summaries
        for output in self.state.tool_outputs:
            summary = output.get("summary", "")
            if summary and len(summary) < 200:
                results.append(summary)
        
        return results[:10]  # Limit to 10 key results
    
    def _gather_metrics(self) -> Dict[str, Any]:
        """Gather all metrics from execution."""
        metrics = {
            "steps_executed": len(self.state.step_progress),
            "tools_used": self.state.tools_used,
            "artifacts_generated": len(self.state.artifacts),
            "elapsed_seconds": self.state.elapsed_seconds,
            "retry_count": self.state.retry_count,
        }
        
        # Add model metrics
        if self.state.models:
            for model in self.state.models:
                if model.accuracy:
                    metrics["model_accuracy"] = model.accuracy
                metrics.update(model.metrics)
        
        # Add dataset metrics
        if self.state.datasets:
            ds = self.state.datasets[0]
            metrics["dataset_rows"] = ds.rows
            metrics["dataset_columns"] = ds.columns
        
        return metrics
    
    def _summarize_artifacts(self) -> Dict[str, int]:
        """Summarize artifacts by category."""
        summary = {}
        
        for artifact in self.state.artifacts:
            category = artifact.get("category", "file")
            summary[category] = summary.get(category, 0) + 1
        
        return summary
    
    def _summarize_errors(self) -> Optional[str]:
        """Summarize errors if any occurred."""
        if not self.state.errors:
            return None
        
        error_types = {}
        for error in self.state.errors:
            et = error.error_type
            error_types[et] = error_types.get(et, 0) + 1
        
        parts = []
        for et, count in error_types.items():
            parts.append(f"{count} {et}")
        
        return f"Encountered: {', '.join(parts)}"
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on execution."""
        recommendations = []
        
        # If model accuracy is low
        for model in self.state.models:
            if model.accuracy and model.accuracy < 0.7:
                recommendations.append("Consider feature engineering or trying different algorithms to improve model accuracy")
        
        # If there were errors
        if self.state.errors:
            recommendations.append("Review the technical details for error information")
        
        # If no visualizations were created
        if self.state.datasets and not self.state.charts_generated:
            recommendations.append("Consider generating visualizations to better understand the data")
        
        return recommendations


def generate_result_text(state: AgentExecutionState) -> str:
    """Generate human-readable result text for LLM synthesis.
    
    This creates a context string that can be used by the LLM
    to generate a natural language response.
    """
    parts = []
    
    # User query
    parts.append(f"User asked: {state.user_query}")
    parts.append("")
    
    # Execution results
    parts.append("Execution results:")
    
    # Dataset analysis
    for ds in state.datasets:
        parts.append(f"- Analyzed dataset '{ds.name}' with {ds.rows:,} rows and {ds.columns} columns")
        if ds.column_names:
            cols = ", ".join(ds.column_names[:10])
            if len(ds.column_names) > 10:
                cols += f" and {len(ds.column_names) - 10} more"
            parts.append(f"  Columns: {cols}")
    
    # Model training
    for model in state.models:
        parts.append(f"- Trained {model.model_type or 'ML'} model")
        if model.accuracy:
            parts.append(f"  Accuracy: {model.accuracy:.2%}")
        for metric, value in model.metrics.items():
            if isinstance(value, (int, float)):
                parts.append(f"  {metric}: {value:.4f}")
    
    # Tool outputs
    for output in state.tool_outputs:
        tool = output.get("tool", "unknown")
        summary = output.get("summary", "")
        if summary:
            parts.append(f"- [{tool}] {summary}")
    
    # Artifacts
    if state.artifacts:
        parts.append("")
        parts.append("Generated artifacts:")
        for artifact in state.artifacts:
            filename = artifact.get("filename", "unknown")
            category = artifact.get("category", "file")
            parts.append(f"- {filename} ({category})")
    
    # Errors
    if state.errors:
        parts.append("")
        parts.append("Notes:")
        for error in state.errors[-3:]:  # Last 3 errors
            parts.append(f"- {error.error_type}: {error.error_message[:100]}")
    
    return "\n".join(parts)


def format_artifacts_for_response(state: AgentExecutionState) -> Dict[str, Any]:
    """Format artifacts grouped by category for frontend response."""
    grouped = {}
    
    for artifact in state.artifacts:
        category = artifact.get("category", "file")
        if category not in grouped:
            grouped[category] = []
        
        grouped[category].append({
            "filename": artifact.get("filename"),
            "mime": artifact.get("mime"),
            "display_type": artifact.get("display_type"),
            "url": artifact.get("url", ""),
            "size": artifact.get("size", 0),
        })
    
    return {
        "artifacts_by_category": grouped,
        "total_count": len(state.artifacts),
        "charts": state.charts_generated,
        "files": state.files_created,
    }
