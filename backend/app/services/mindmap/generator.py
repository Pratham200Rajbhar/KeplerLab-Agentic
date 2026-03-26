from app.services.llm_service.structured_invoker import invoke_structured
from app.services.llm_service.llm_schemas import MindMapOutput
from app.prompts import get_mindmap_prompt
import logging

logger = logging.getLogger(__name__)

def generate_mindmap(material_text: str, focus_topic: str | None = None, instructions: str | None = None) -> dict:
    """
    Generates a mind map from the provided material text.
    """
    logger.info("Generating mind map | focus_topic=%s", focus_topic)
    prompt = get_mindmap_prompt(material_text, focus_topic, instructions)
    
    # Use the structured invoker to get a validated MindMapOutput
    result = invoke_structured(prompt, MindMapOutput, max_retries=2)
    
    return result.model_dump()
