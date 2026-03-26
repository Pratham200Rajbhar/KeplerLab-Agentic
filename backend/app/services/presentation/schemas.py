from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


ElementType = Literal[
    "title",
    "subtitle",
    "bullet",
    "paragraph",
    "table",
    "image",
    "numbered_list",
    "quote",
    "code",
    "callout",
    "divider",
]


class SlideElement(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: ElementType
    text: Optional[str] = None
    items: list[Any] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)
    prompt: Optional[str] = None
    source: Optional[str] = None
    caption: Optional[str] = None


class ThemeTokens(BaseModel):
    bg: str = Field(default="#f1f5f9", description="Background hex color")
    card: str = Field(default="#ffffff", description="Slide card hex color")
    text: str = Field(default="#0f172a", description="Main text hex color")
    muted: str = Field(default="#334155", description="Muted/secondary text hex color")
    accent: str = Field(default="#0f766e", description="Accent hex color (for highlights, borders, titles)")
    border: str = Field(default="#d1d5db", description="Border/divisor hex color")
    header_font: str = Field(default="'Inter', sans-serif", description="Font family for headers")
    body_font: str = Field(default="'Inter', sans-serif", description="Font family for body text")


class Slide(BaseModel):
    layout: str = "title_content"
    title: str = ""
    elements: list[SlideElement] = Field(default_factory=list)


class PresentationData(BaseModel):
    theme_tokens: ThemeTokens = Field(default_factory=ThemeTokens)
    slides: list[Slide] = Field(default_factory=list)


class GeneratePresentationRequest(BaseModel):
    notebook_id: str
    material_ids: list[str] = Field(..., min_length=1)
    title: Optional[str] = Field(default=None, max_length=255)
    instruction: Optional[str] = Field(default=None, max_length=2000)
    theme: Optional[str] = Field(default="modern", max_length=100)
    max_slides: Optional[int] = Field(default=None, ge=1)


class SuggestPresentationRequest(BaseModel):
    material_ids: list[str] = Field(..., min_length=1)


class SuggestPresentationResponse(BaseModel):
    suggested_count: int = Field(..., ge=1)
    reasoning: str


class UpdatePresentationRequest(BaseModel):
    presentation_id: str
    instruction: str = Field(..., min_length=1, max_length=4000)
    active_slide_index: Optional[int] = Field(default=None, ge=0)


class PresentationResponse(BaseModel):
    id: str
    notebook_id: str
    user_id: str
    content_type: str
    title: Optional[str] = None
    data: Optional[dict[str, Any]] = None
    html_path: Optional[str] = None
    ppt_path: Optional[str] = None
    material_ids: list[str] = Field(default_factory=list)
    created_at: Optional[str] = None


class PresentationPayload(BaseModel):
    theme_tokens: ThemeTokens = Field(default_factory=ThemeTokens)
    slides: list[Slide] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_slides(self) -> "PresentationPayload":
        if not self.slides:
            raise ValueError("Presentation must include at least one slide")
        return self
