from app.services.llm_service.structured_invoker import invoke_structured, async_invoke_structured
from app.services.llm_service.llm_schemas import FlashcardOutput, FlashcardSuggestionOutput
from app.prompts import get_flashcard_prompt, get_flashcard_suggestion_prompt
import logging

logger = logging.getLogger(__name__)

def generate_flashcards(material_text: str, card_count: int | None = None, difficulty: str = "Medium", instructions: str | None = None) -> dict:
    prompt = get_flashcard_prompt(material_text, card_count, difficulty, instructions)
    result = invoke_structured(prompt, FlashcardOutput, max_retries=2)
    return result.model_dump()

async def suggest_flashcard_count(material_text: str) -> dict:
    prompt = get_flashcard_suggestion_prompt(material_text)
    result = await async_invoke_structured(prompt, FlashcardSuggestionOutput, max_retries=1)
    return result.model_dump()
