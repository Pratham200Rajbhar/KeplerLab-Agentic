from app.services.llm_service.structured_invoker import invoke_structured, async_invoke_structured
from app.services.llm_service.llm_schemas import QuizOutput, QuizSuggestionOutput
from app.prompts import get_quiz_prompt, get_quiz_suggestion_prompt
import logging

logger = logging.getLogger(__name__)

def generate_quiz(material_text: str, mcq_count: int | None = None, difficulty: str = "Medium", instructions: str | None = None) -> dict:
    prompt = get_quiz_prompt(material_text, mcq_count, difficulty, instructions)
    result = invoke_structured(prompt, QuizOutput, max_retries=2)
    return result.model_dump()

async def suggest_quiz_count(material_text: str) -> dict:
    prompt = get_quiz_suggestion_prompt(material_text)
    result = await async_invoke_structured(prompt, QuizSuggestionOutput, max_retries=1)
    return result.model_dump()
