from __future__ import annotations

from pydantic import BaseModel, Field

from app.services.tools.secure_code_interpreter import (
    SecureCodeInterpreterInput,
    SecureCodeInterpreterOutput,
    execute_secure_code_interpreter,
)


class WorkflowStep(BaseModel):
    name: str = Field(min_length=1)
    python_code: str = Field(min_length=1)
    timeout_seconds: int = Field(default=20, ge=1, le=180)
    retries: int = Field(default=0, ge=0, le=2)


class WorkflowInput(BaseModel):
    steps: list[WorkflowStep] = Field(min_length=1)


class WorkflowStepResult(BaseModel):
    name: str
    success: bool
    stdout: str
    stderr: str
    files: list[str]


class WorkflowOutput(BaseModel):
    success: bool
    steps: list[WorkflowStepResult]


async def execute_workflow(payload: WorkflowInput) -> WorkflowOutput:
    step_results: list[WorkflowStepResult] = []

    for step in payload.steps:
        attempt = 0
        last: SecureCodeInterpreterOutput | None = None
        while attempt <= step.retries:
            last = await execute_secure_code_interpreter(
                SecureCodeInterpreterInput(
                    code=step.python_code,
                    timeout_seconds=step.timeout_seconds,
                )
            )
            if last.exit_code == 0 and not last.timed_out:
                break
            attempt += 1

        assert last is not None
        ok = last.exit_code == 0 and not last.timed_out
        step_results.append(
            WorkflowStepResult(
                name=step.name,
                success=ok,
                stdout=last.stdout,
                stderr=last.stderr,
                files=last.files,
            )
        )
        if not ok:
            return WorkflowOutput(success=False, steps=step_results)

    return WorkflowOutput(success=True, steps=step_results)
