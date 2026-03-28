from __future__ import annotations

from pydantic import BaseModel, Field

from app.services.tools.file_generator_tool import FileGeneratorInput, execute_file_generator


class ChartGeneratorInput(BaseModel):
    python_code: str = Field(min_length=1, description="Python code that generates chart files")
    timeout_seconds: int = Field(default=20, ge=1, le=180)


class ChartGeneratorOutput(BaseModel):
    files: list[str]
    stdout: str
    stderr: str
    success: bool


async def execute_chart_generator(payload: ChartGeneratorInput) -> ChartGeneratorOutput:
    out = await execute_file_generator(
        FileGeneratorInput(
            python_code=payload.python_code,
            timeout_seconds=payload.timeout_seconds,
        )
    )
    chart_files = [f for f in out.files if f.lower().endswith((".png", ".jpg", ".jpeg", ".svg", ".html"))]
    return ChartGeneratorOutput(
        files=chart_files,
        stdout=out.stdout,
        stderr=out.stderr,
        success=out.success and bool(chart_files),
    )
