from app.services.llm_service.structured_invoker import invoke_structured
from app.services.llm_service.llm_schemas import FlashcardOutput
from app.prompts import get_flashcard_prompt
import logging

logger = logging.getLogger(__name__)

def generate_flashcards(material_text: str, card_count: int = None, difficulty: str = "Medium", instructions: str = None) -> dict:
    prompt = get_flashcard_prompt(material_text, card_count, difficulty, instructions)
    result = invoke_structured(prompt, FlashcardOutput, max_retries=2)
    return result.model_dump()
