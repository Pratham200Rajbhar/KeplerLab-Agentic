"""Execution Engine — Handles tool execution with enhanced error handling.

Provides:
- Unified tool execution interface
- Error detection and repair
- Output parsing for datasets and models
- Artifact extraction
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.core.config import settings
from app.services.agent.state import (
    AgentExecutionState,
    DatasetMetadata,
    ModelMetadata,
)
from app.services.agent.tools import (
    TOOL_REGISTRY,
    AgentContext,
    ToolOutput,
)

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of a tool execution."""
    success: bool
    summary: str
    code: Optional[str] = None
    artifacts: List[Dict[str, Any]] = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    duration_ms: int = 0
    output_data: Dict[str, Any] = None
    dataset_metadata: Optional[DatasetMetadata] = None
    model_metadata: Optional[ModelMetadata] = None
    raw_output: str = ""
    
    def __post_init__(self):
        if self.artifacts is None:
            self.artifacts = []
        if self.output_data is None:
            self.output_data = {}


class ExecutionEngine:
    """Engine for executing agent tools with enhanced features."""
    
    def __init__(self, state: AgentExecutionState, ctx: AgentContext):
        self.state = state
        self.ctx = ctx
        self.event_callback: Optional[Callable] = None
    
    def set_event_callback(self, callback: Callable) -> None:
        """Set callback for emitting events during execution."""
        self.event_callback = callback
    
    async def _emit_event(self, event: str, data: Dict[str, Any]) -> None:
        """Emit an event if callback is set."""
        if self.event_callback:
            await self.event_callback(event, data)
    
    async def execute_step(
        self,
        step_index: int,
        tool: str,
        description: str,
        inputs: Dict[str, Any],
    ) -> ExecutionResult:
        """Execute a single step with full error handling.
        
        Args:
            step_index: Index of this step in the plan
            tool: Name of the tool to execute
            description: Human-readable step description
            inputs: Tool inputs
            
        Returns:
            ExecutionResult with success status and outputs
        """
        start_time = time.time()
        
        # Update state
        self.state.start_step(step_index, tool, description)
        await self._emit_event("step", {
            "status": "started",
            "step": step_index,
            "tool": tool,
            "description": description,
        })
        
        try:
            # Get tool function
            tool_fn = TOOL_REGISTRY.get(tool)
            if not tool_fn:
                raise ValueError(f"Unknown tool: {tool}")
            
            # Enrich inputs with context
            enriched_inputs = self._enrich_inputs(inputs, tool)
            
            # Execute tool
            if tool == "python_tool":
                result = await self._execute_python_tool(
                    enriched_inputs, step_index
                )
            else:
                output = await tool_fn(enriched_inputs, self.ctx)
                result = self._process_tool_output(output, tool)
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            result.duration_ms = duration_ms
            
            # Update state
            self.state.complete_step(
                step_index,
                result.summary,
                duration_ms,
                error=result.error,
            )
            
            # Process artifacts
            for artifact in result.artifacts:
                self.state.add_artifact(artifact)
                await self._emit_event("artifact", artifact)
            
            # Process metadata
            if result.dataset_metadata:
                self.state.add_dataset(result.dataset_metadata)
            if result.model_metadata:
                self.state.add_model(result.model_metadata)
            
            # Add generated code
            if result.code:
                self.state.add_generated_code(step_index, result.code)
            
            await self._emit_event("step", {
                "status": "completed" if result.success else "failed",
                "step": step_index,
                "summary": result.summary,
                "duration_ms": duration_ms,
            })
            
            return result
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_msg = str(e)
            
            self.state.record_error(
                step_index=step_index,
                error_type=type(e).__name__,
                error_message=error_msg,
            )
            
            self.state.complete_step(
                step_index,
                f"Step failed: {error_msg}",
                duration_ms,
                error=error_msg,
            )
            
            await self._emit_event("step", {
                "status": "failed",
                "step": step_index,
                "error": error_msg,
                "duration_ms": duration_ms,
            })
            
            return ExecutionResult(
                success=False,
                summary=f"Execution failed: {error_msg}",
                error=error_msg,
                error_type=type(e).__name__,
                duration_ms=duration_ms,
            )
    
    def _enrich_inputs(self, inputs: Dict[str, Any], tool: str) -> Dict[str, Any]:
        """Enrich tool inputs with context from state."""
        enriched = dict(inputs)
        
        # Add context from previous tool outputs
        if tool == "python_tool":
            # Add dataset info if available
            if self.state.datasets and "context" not in enriched:
                ds_context = []
                for ds in self.state.datasets:
                    ds_context.append(
                        f"Dataset '{ds.name}': {ds.rows} rows, columns: {', '.join(ds.column_names[:10])}"
                    )
                enriched["context"] = "\n".join(ds_context)
            
            # Add RAG context if available
            for output in self.state.tool_outputs:
                if output.get("tool") == "rag_tool" and output.get("context"):
                    if "context" in enriched:
                        enriched["context"] += f"\n\nFrom documents:\n{output['context']}"
                    else:
                        enriched["context"] = output["context"]
        
        return enriched
    
    async def _execute_python_tool(
        self,
        inputs: Dict[str, Any],
        step_index: int,
    ) -> ExecutionResult:
        """Execute Python tool with enhanced handling."""
        from app.services.llm_service.llm import get_llm
        from app.services.code_execution.security import validate_code, sanitize_code
        from app.services.code_execution.sandbox import run_in_sandbox
        from app.prompts import get_code_generation_prompt
        
        task = inputs.get("task", "")
        context = inputs.get("context", "")
        
        # Step 1: Generate code
        await self._emit_event("step_detail", {
            "step": step_index,
            "action": "Generating code",
        })
        
        llm = get_llm(temperature=settings.LLM_TEMPERATURE_CODE)
        prompt_text = get_code_generation_prompt(task)
        
        # Add data analysis instructions
        prompt_text += """

Important instructions:
1. If working with data, always print a summary of the dataset (shape, columns, types)
2. Save all charts/figures to files (use plt.savefig('chart_name.png'))
3. Save any generated models using joblib or pickle
4. Print key results and metrics clearly
5. If training a model, print accuracy/performance metrics
6. Save any generated data to CSV files
"""
        
        if context:
            prompt_text = f"{prompt_text}\n\nAvailable context:\n{context}"
        
        code_response = await llm.ainvoke(prompt_text)
        code = getattr(code_response, "content", str(code_response)).strip()
        
        # Strip markdown fences
        code = self._strip_code_fences(code)
        
        # Emit code generated event
        await self._emit_event("code_generated", {
            "step": step_index,
            "code": code,
            "language": "python",
        })
        
        # Step 2: Validate code
        await self._emit_event("step_detail", {
            "step": step_index,
            "action": "Validating code",
        })
        
        validation = validate_code(code)
        if not validation.is_safe:
            return ExecutionResult(
                success=False,
                summary=f"Code blocked: {'; '.join(validation.violations)}",
                code=code,
                error="Security violation",
                error_type="SecurityError",
            )
        
        code = sanitize_code(code)
        
        # Step 3: Execute with repair loop
        await self._emit_event("step_detail", {
            "step": step_index,
            "action": "Executing code",
        })
        
        max_repairs = settings.MAX_CODE_REPAIR_ATTEMPTS
        attempt = 0
        last_error = None
        
        while attempt <= max_repairs:
            exec_result = await run_in_sandbox(
                code,
                work_dir=self.ctx.work_dir,
                timeout=settings.CODE_EXECUTION_TIMEOUT,
            )
            
            if exec_result.exit_code == 0:
                # Success - detect artifacts and metadata
                return await self._process_successful_execution(
                    code, exec_result, step_index
                )
            
            # Handle ImportError - auto-install
            if exec_result.stderr and "ModuleNotFoundError" in exec_result.stderr:
                module = self._extract_missing_module(exec_result.stderr)
                if module and module in settings.APPROVED_ON_DEMAND:
                    await self._emit_event("step_detail", {
                        "step": step_index,
                        "action": f"Installing {module}",
                    })
                    try:
                        from app.services.code_execution.sandbox_env import install_package_if_missing_async
                        await install_package_if_missing_async(module)
                        continue  # Retry without incrementing attempt
                    except Exception:
                        pass
            
            # Attempt repair
            last_error = exec_result.stderr or exec_result.error
            attempt += 1
            
            if attempt > max_repairs:
                break
            
            # Check if error is repeated
            self.state.record_error(
                step_index=step_index,
                error_type="ExecutionError",
                error_message=last_error or "Unknown error",
                code_snippet=code[:500],
            )
            
            if self.state.is_error_repeated():
                logger.warning("Same error repeated, stopping repair attempts")
                break
            
            self.state.retry_count += 1
            
            await self._emit_event("step_detail", {
                "step": step_index,
                "action": f"Repairing code (attempt {attempt}/{max_repairs})",
            })
            
            # Generate repair
            code = await self._repair_code(code, last_error, llm)
            if not code:
                break
        
        # All attempts failed
        return ExecutionResult(
            success=False,
            summary=f"Code execution failed after {attempt} attempts",
            code=code,
            error=last_error,
            error_type="ExecutionError",
            raw_output=exec_result.stdout,
        )
    
    async def _process_successful_execution(
        self,
        code: str,
        exec_result: Any,
        step_index: int,
    ) -> ExecutionResult:
        """Process successful code execution, extracting artifacts and metadata."""
        from app.services.agent.artifact_detector import ArtifactDetector
        
        # Detect artifacts
        detector = ArtifactDetector(self.ctx.work_dir)
        artifacts = detector.detect_all()
        
        # Parse output for metadata
        dataset_meta = None
        model_meta = None
        
        if exec_result.stdout:
            dataset_meta = self._parse_dataset_metadata(exec_result.stdout)
            model_meta = self._parse_model_metadata(exec_result.stdout)
        
        # Build summary
        summary_parts = ["Code executed successfully"]
        
        if dataset_meta:
            summary_parts.append(
                f"Analyzed dataset: {dataset_meta.rows} rows, {dataset_meta.columns} columns"
            )
        
        if model_meta:
            summary_parts.append(
                f"Trained {model_meta.model_type} model with {model_meta.accuracy:.1%} accuracy"
            )
        
        if artifacts:
            summary_parts.append(f"{len(artifacts)} file(s) generated")
        
        return ExecutionResult(
            success=True,
            summary=". ".join(summary_parts),
            code=code,
            artifacts=artifacts,
            dataset_metadata=dataset_meta,
            model_metadata=model_meta,
            raw_output=exec_result.stdout,
            output_data={
                "exit_code": 0,
                "stdout": exec_result.stdout,
            },
        )
    
    async def _repair_code(
        self,
        code: str,
        error: str,
        llm: Any,
    ) -> Optional[str]:
        """Attempt to repair failed code."""
        from app.services.code_execution.security import validate_code, sanitize_code
        from app.prompts import get_code_repair_prompt
        
        try:
            repair_prompt = get_code_repair_prompt(code, error)
            repair_response = await llm.ainvoke(repair_prompt)
            repaired = getattr(repair_response, "content", str(repair_response)).strip()
            
            repaired = self._strip_code_fences(repaired)
            
            # Validate repaired code
            validation = validate_code(repaired)
            if not validation.is_safe:
                return None
            
            return sanitize_code(repaired)
            
        except Exception as e:
            logger.error("Code repair failed: %s", e)
            return None
    
    def _process_tool_output(self, output: ToolOutput, tool: str) -> ExecutionResult:
        """Process output from non-Python tools."""
        # Store output in state
        self.state.tool_outputs.append({
            "tool": tool,
            "summary": output.summary,
            "data": output.data,
            "context": output.data.get("context", ""),
        })
        
        return ExecutionResult(
            success=output.error is None,
            summary=output.summary,
            code=output.code,
            artifacts=output.artifacts,
            error=output.error,
            output_data=output.data,
        )
    
    def _strip_code_fences(self, code: str) -> str:
        """Remove markdown code fences from code."""
        if code.startswith("```python"):
            code = code[len("```python"):].strip()
        if code.startswith("```"):
            code = code[3:].strip()
        if code.endswith("```"):
            code = code[:-3].strip()
        return code
    
    def _extract_missing_module(self, stderr: str) -> Optional[str]:
        """Extract module name from ModuleNotFoundError."""
        match = re.search(r"No module named '(\w+)'", stderr)
        return match.group(1) if match else None
    
    def _parse_dataset_metadata(self, output: str) -> Optional[DatasetMetadata]:
        """Parse dataset metadata from execution output."""
        # Look for common patterns in pandas output
        metadata = DatasetMetadata(name="dataset")
        
        # Parse shape
        shape_match = re.search(r"(\d+)\s*rows?\s*[x×,]\s*(\d+)\s*columns?", output, re.I)
        if not shape_match:
            shape_match = re.search(r"shape[:\s]+\(?(\d+)[,\s]+(\d+)\)?", output, re.I)
        
        if shape_match:
            metadata.rows = int(shape_match.group(1))
            metadata.columns = int(shape_match.group(2))
            metadata.loaded_at = datetime.utcnow().isoformat()
            return metadata
        
        return None
    
    def _parse_model_metadata(self, output: str) -> Optional[ModelMetadata]:
        """Parse model training metadata from execution output."""
        metadata = ModelMetadata(name="model")
        
        # Parse accuracy
        acc_match = re.search(
            r"(?:accuracy|acc)[:\s]+([0-9.]+)%?",
            output,
            re.I
        )
        if acc_match:
            acc = float(acc_match.group(1))
            metadata.accuracy = acc / 100 if acc > 1 else acc
        
        # Parse model type
        model_types = [
            "RandomForest", "XGBoost", "LogisticRegression",
            "DecisionTree", "GradientBoosting", "SVM", "KNN",
            "NeuralNetwork", "LinearRegression"
        ]
        for mt in model_types:
            if mt.lower() in output.lower():
                metadata.model_type = mt
                break
        
        # Parse metrics
        for metric in ["precision", "recall", "f1", "f1_score", "auc", "roc_auc"]:
            match = re.search(f"{metric}[:\\s]+([0-9.]+)", output, re.I)
            if match:
                metadata.metrics[metric] = float(match.group(1))
        
        if metadata.accuracy > 0 or metadata.model_type:
            metadata.trained_at = datetime.utcnow().isoformat()
            return metadata
        
        return None


async def execute_tool_step(
    state: AgentExecutionState,
    ctx: AgentContext,
    step_index: int,
    tool: str,
    description: str,
    inputs: Dict[str, Any],
    event_callback: Optional[Callable] = None,
) -> ExecutionResult:
    """Convenience function to execute a single tool step."""
    engine = ExecutionEngine(state, ctx)
    if event_callback:
        engine.set_event_callback(event_callback)
    
    return await engine.execute_step(step_index, tool, description, inputs)
