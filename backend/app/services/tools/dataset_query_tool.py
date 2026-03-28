from __future__ import annotations

from pydantic import BaseModel, Field

from app.services.tools.secure_code_interpreter import (
    SecureCodeInterpreterInput,
    SecureCodeInterpreterOutput,
    execute_secure_code_interpreter,
)


class DatasetQueryInput(BaseModel):
    python_code: str = Field(min_length=1, description="Python code to query/transform dataset files")
    timeout_seconds: int = Field(default=25, ge=1, le=180)


class DatasetQueryOutput(BaseModel):
    stdout: str
    stderr: str
    files: list[str]
    success: bool


async def execute_dataset_query(payload: DatasetQueryInput) -> DatasetQueryOutput:
    out: SecureCodeInterpreterOutput = await execute_secure_code_interpreter(
        SecureCodeInterpreterInput(
            code=payload.python_code,
            timeout_seconds=payload.timeout_seconds,
        )
    )
    return DatasetQueryOutput(
        stdout=out.stdout,
        stderr=out.stderr,
        files=out.files,
        success=(out.exit_code == 0 and not out.timed_out),
    )
