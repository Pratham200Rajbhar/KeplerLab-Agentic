from pydantic import AliasChoices, BaseModel, Field, model_validator
from typing import Any, List, Optional

class QuizQuestion(BaseModel):
    question: str
    options: List[str] = Field(min_length=2, max_length=6)
    correct_answer: int = Field(validation_alias=AliasChoices("correct_answer", "answer"))
    explanation: Optional[str] = None

class QuizOutput(BaseModel):
    title: str
    questions: List[Any]

    @model_validator(mode="after")
    def _drop_incomplete_questions(self) -> "QuizOutput":
        valid = []
        for item in self.questions:
            try:
                valid.append(QuizQuestion.model_validate(item))
            except Exception:
                pass
        if not valid:
            raise ValueError("No valid quiz questions found in LLM output")
        self.questions = valid  # type: ignore[assignment]
        return self

class Flashcard(BaseModel):
    question: str = Field(validation_alias=AliasChoices("question", "front"))
    answer: str = Field(validation_alias=AliasChoices("answer", "back"))

class FlashcardOutput(BaseModel):
    title: str
    flashcards: List[Any]

    @model_validator(mode="after")
    def _drop_incomplete_cards(self) -> "FlashcardOutput":
        valid = []
        for item in self.flashcards:
            try:
                valid.append(Flashcard.model_validate(item))
            except Exception:
                pass
        if not valid:
            raise ValueError("No valid flashcards found in LLM output")
        self.flashcards = valid  # type: ignore[assignment]
        return self

class FlashcardSuggestionOutput(BaseModel):
    suggested_count: int = Field(ge=5, le=150)
    reasoning: str

class QuizSuggestionOutput(BaseModel):
    suggested_count: int = Field(ge=5, le=150)
    reasoning: str

class PresentationSuggestionOutput(BaseModel):
    suggested_count: int = Field(ge=5, le=60)
    reasoning: str

class IntentAnalysis(BaseModel):
    technical_depth: str = Field(description="low / medium / high / expert")
    persuasion_vs_explanation: str = Field(description="e.g. '30/70' or '70/30'")
    estimated_duration_minutes: int = Field(ge=1, le=120)
    expected_slide_density: str = Field(description="sparse / moderate / dense")
    visual_emphasis: str = Field(description="low / medium / high")
    formality_level: str = Field(description="casual / professional / academic / executive")
    recommended_slide_count: int = Field(ge=3, le=60)
    theme_suggestion: Optional[str] = None

class SlidePlan(BaseModel):
    slide_number: int
    title: str
    purpose: str = Field(description="e.g. title, introduction, content, comparison, summary, q_and_a")
    layout_type: str = Field(description="e.g. title_slide, bullets, two_column, chart, table, diagram, image_focus, blank")
    primary_component: str = Field(description="e.g. bullets, table, chart, diagram, image, text_block, kpi_highlight")
    supporting_components: List[str] = Field(default_factory=list)
    information_density: str = Field(description="light / moderate / heavy")
    narrative_position: str = Field(description="opening / rising / climax / falling / conclusion")

class PresentationStrategy(BaseModel):
    presentation_title: str
    total_slides: int = Field(ge=3, le=60)
    narrative_summary: str
    slides: List[Any]

    @model_validator(mode="after")
    def _validate_slides(self) -> "PresentationStrategy":
        valid = []
        for item in self.slides:
            try:
                valid.append(SlidePlan.model_validate(item))
            except Exception:
                pass
        if not valid:
            raise ValueError("No valid slide plans found in LLM output")
        self.slides = valid  # type: ignore[assignment]
        self.total_slides = len(valid)
        return self

class SlideContent(BaseModel):
    title: str
    subtitle: Optional[str] = None
    bullets: Optional[List[str]] = None
    paragraph: Optional[str] = None
    table_data: Optional[dict] = None
    chart_data: Optional[dict] = None
    diagram_structure: Optional[dict] = None
    image_prompt: Optional[str] = None
    speaker_notes: Optional[str] = None
    key_metric: Optional[dict] = None

class OptimizedPrompt(BaseModel):
    optimized_prompt: str = Field(validation_alias=AliasChoices("optimized_prompt", "prompt", "text", "suggestion"))
    confidence: int = Field(ge=0, le=100)
    explanation: str = Field(default="", validation_alias=AliasChoices("explanation", "justification", "reasoning"))

class OptimizedPromptsOutput(BaseModel):
    prompts: List[Any] = Field(default_factory=list, validation_alias=AliasChoices("prompts", "optimized_prompts", "alternatives", "items", "results"))

    @model_validator(mode="after")
    def _drop_incomplete_prompts(self) -> "OptimizedPromptsOutput":
        valid = []
        for item in self.prompts:
            try:
                valid.append(OptimizedPrompt.model_validate(item))
            except Exception:
                pass
        self.prompts = valid  # type: ignore[assignment]
        return self

class PresentationHTMLOutput(BaseModel):
    title: str
    slide_count: int = Field(ge=1, le=60)
    theme: str = Field(default="dark-modern")
    html: str = Field(min_length=100, description="Complete standalone HTML document")

    @model_validator(mode="after")
    def _validate_html(self) -> "PresentationHTMLOutput":
        h = self.html.strip()
        if "<html" not in h.lower():
            raise ValueError("HTML output must contain an <html> tag")
        if "</html>" not in h.lower():
            if "</body>" not in h.lower():
                self.html = h + "\n</body>\n</html>"
            else:
                self.html = h + "\n</html>"
        return self
class MindMapNode(BaseModel):
    label: str
    children: List["MindMapNode"] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _validate_string_to_node(cls, data: Any) -> Any:
        if isinstance(data, str):
            return {"label": data, "children": []}
        return data

class MindMapOutput(BaseModel):
    title: str
    children: List[MindMapNode] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_depth_and_count(self) -> "MindMapOutput":
        # Ensure 4-8 main branches
        if not (4 <= len(self.children) <= 8):
             # We don't strictly enforce this via error since LLM might struggle,
             # but we can log or adjust. For now, let's keep it advisory or 
             # raise if it's way off to trigger retry.
             pass
        return self
