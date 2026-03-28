from __future__ import annotations

from pydantic import BaseModel, Field

from app.services.code_execution.sandbox import run_in_sandbox
from app.services.code_execution.security import sanitize_code, validate_code


class SecureCodeInterpreterInput(BaseModel):
    code: str = Field(min_length=1, max_length=100000)
    timeout_seconds: int = Field(default=15, ge=1, le=120)


class SecureCodeInterpreterOutput(BaseModel):
    stdout: str
    stderr: str
    files: list[str]
    exit_code: int
    timed_out: bool


async def execute_secure_code_interpreter(
    payload: SecureCodeInterpreterInput,
) -> SecureCodeInterpreterOutput:
    validation = validate_code(payload.code)
    if not validation.is_safe:
        return SecureCodeInterpreterOutput(
            stdout="",
            stderr="; ".join(validation.violations),
            files=[],
            exit_code=1,
            timed_out=False,
        )

    code = sanitize_code(payload.code, ensure_file_output=True)
    result = await run_in_sandbox(code, timeout=payload.timeout_seconds, language="python")
    return SecureCodeInterpreterOutput(
        stdout=result.stdout,
        stderr=result.stderr,
        files=list(result.output_files or []),
        exit_code=result.exit_code,
        timed_out=result.timed_out,
    )
