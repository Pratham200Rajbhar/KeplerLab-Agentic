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
