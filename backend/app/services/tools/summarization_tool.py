from __future__ import annotations

import re

from pydantic import BaseModel, Field


class SummarizationInput(BaseModel):
    text: str = Field(min_length=1)
    max_sentences: int = Field(default=5, ge=1, le=20)


class SummarizationOutput(BaseModel):
    summary: str
    sentence_count: int


def execute_summarization(payload: SummarizationInput) -> SummarizationOutput:
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", payload.text) if p.strip()]
    selected = parts[: payload.max_sentences] if parts else [payload.text[:500]]
    summary = " ".join(selected).strip()
    return SummarizationOutput(summary=summary, sentence_count=len(selected))
