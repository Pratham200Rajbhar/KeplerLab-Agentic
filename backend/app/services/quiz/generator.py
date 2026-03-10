from app.services.llm_service.structured_invoker import invoke_structured
from app.services.llm_service.llm_schemas import QuizOutput
from app.prompts import get_quiz_prompt
import logging

logger = logging.getLogger(__name__)

def generate_quiz(material_text: str, mcq_count: int = None, difficulty: str = "Medium", instructions: str = None) -> dict:
    prompt = get_quiz_prompt(material_text, mcq_count, difficulty, instructions)
    result = invoke_structured(prompt, QuizOutput, max_retries=2)
    return result.model_dump()
