from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from app.services.llm_service.llm import get_llm_structured

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_CODE_FENCE_RE = re.compile(r"```(?:json|JSON)?\s*\n?|```\s*", re.DOTALL)
_THINK_TAG_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

def _clean_json_text(text: str) -> str:
    text = _THINK_TAG_RE.sub("", text).strip()
    
    text = _CODE_FENCE_RE.sub("", text).strip()
    
    text = re.sub(r"^(Here's|Here is|The JSON|Output:|Response:)\s*:?\s*", "", text, flags=re.IGNORECASE)
    
    return text.strip()

def _extract_json_block(text: str) -> str:
    start_brace = text.find("{")
    start_bracket = text.find("[")
    
    if start_brace == -1 and start_bracket == -1:
        raise ValueError("No JSON block found")
    
    if start_bracket == -1 or (start_brace != -1 and start_brace < start_bracket):
        start = start_brace
        end = text.rfind("}")
        if end > start:
            return text[start:end + 1]
    else:
        start = start_bracket
        end = text.rfind("]")
        if end > start:
            return text[start:end + 1]
    
    raise ValueError("Could not extract complete JSON block")

def _repair_json(text: str) -> str:
    text = re.sub(r"'([^']*)'(?=\s*[:,\}\]])", r'"\1"', text)
    
    text = re.sub(r'"\s*\n\s*"', '",\n"', text)
    
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    
    text = text.replace('\\"', '"').replace('\\n', '\n')
    
    return text

def parse_json_robust(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    cleaned = _clean_json_text(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    
    try:
        extracted = _extract_json_block(cleaned)
        return json.loads(extracted)
    except (ValueError, json.JSONDecodeError):
        pass
    
    try:
        repaired = _repair_json(extracted if 'extracted' in locals() else cleaned)
        return json.loads(repaired)
    except (json.JSONDecodeError, NameError):
        pass
    
    try:
        import json_repair
        return json_repair.loads(cleaned)
    except Exception as e:
        logger.error(f"All JSON parsing attempts failed: {e}")
        raise ValueError(
            f"Cannot extract valid JSON from LLM response. "
            f"First 500 chars: {text[:500]}"
        )

def invoke_structured(
    prompt: str,
    schema: Type[T],
    max_retries: int = 2,
    timeout: Optional[int] = None,
) -> T:
    llm = get_llm_structured()
    
    last_error: Optional[Exception] = None
    last_response: str = ""
    
    for attempt in range(1 + max_retries):
        try:
            if attempt > 0:
                effective_prompt = _build_retry_prompt(prompt, last_response, last_error)
                logger.info(f"Retry attempt {attempt}/{max_retries} for structured output")
            else:
                effective_prompt = prompt
            
            logger.debug(f"Invoking LLM (attempt {attempt + 1})")
            response = llm.invoke(effective_prompt)
            
            text = getattr(response, "content", str(response)).strip()
            last_response = text
            
            logger.debug("Parsing JSON from LLM response")
            data = parse_json_robust(text)
            
            logger.debug(f"Validating against schema: {schema.__name__}")
            validated = schema.model_validate(data)
            
            logger.info(f"Structured output validated successfully (attempt {attempt + 1})")
            return validated
        
        except (json.JSONDecodeError, ValueError, ValidationError) as exc:
            last_error = exc
            logger.warning(
                f"Structured output failed (attempt {attempt + 1}/{max_retries + 1}): "
                f"{type(exc).__name__}: {str(exc)[:200]}"
            )
            
            if attempt == max_retries:
                logger.error(
                    f"Final attempt failed. Raw response: {last_response[:1000]}"
                )
    
    error_msg = (
        f"Failed to produce valid structured output after {max_retries + 1} attempts. "
        f"Last error: {type(last_error).__name__}: {str(last_error)}"
    )
    logger.error(error_msg)
    raise ValueError(error_msg)

def invoke_structured_safe(
    prompt: str,
    schema: Type[T],
    max_retries: int = 2,
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    try:
        result = invoke_structured(prompt, schema, max_retries, timeout)
        return {
            "success": True,
            "data": result.model_dump()
        }
    
    except TimeoutError as e:
        logger.error(f"LLM timeout: {e}")
        return {
            "success": False,
            "error": "LLM_TIMEOUT",
            "details": str(e)
        }
    
    except ValueError as e:
        logger.error(f"LLM output invalid: {e}")
        return {
            "success": False,
            "error": "LLM_OUTPUT_INVALID",
            "details": str(e)
        }
    
    except Exception as e:
        logger.error(f"Unexpected error in structured invocation: {e}", exc_info=True)
        return {
            "success": False,
            "error": "LLM_INVOCATION_ERROR",
            "details": str(e)
        }

async def async_invoke_structured(
    prompt: str,
    schema: Type[T],
    max_retries: int = 2,
    timeout: Optional[int] = None,
) -> T:
    llm = get_llm_structured()
    
    last_error: Optional[Exception] = None
    last_response: str = ""
    
    for attempt in range(1 + max_retries):
        try:
            if attempt > 0:
                effective_prompt = _build_retry_prompt(prompt, last_response, last_error)
                logger.info(f"Async retry attempt {attempt}/{max_retries}")
            else:
                effective_prompt = prompt
            
            logger.debug(f"Async invoking LLM (attempt {attempt + 1})")
            response = await llm.ainvoke(effective_prompt)
            
            text = getattr(response, "content", str(response)).strip()
            last_response = text
            
            data = parse_json_robust(text)
            validated = schema.model_validate(data)
            
            logger.info(f"Async structured output validated (attempt {attempt + 1})")
            return validated
        
        except (json.JSONDecodeError, ValueError, ValidationError) as exc:
            last_error = exc
            logger.warning(
                f"Async structured output failed (attempt {attempt + 1}): "
                f"{type(exc).__name__}: {str(exc)[:200]}"
            )
    
    error_msg = f"Async failed after {max_retries + 1} attempts. Last error: {last_error}"
    logger.error(error_msg)
    raise ValueError(error_msg)

async def async_invoke_structured_safe(
    prompt: str,
    schema: Type[T],
    max_retries: int = 2,
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    try:
        result = await async_invoke_structured(prompt, schema, max_retries, timeout)
        return {"success": True, "data": result.model_dump()}
    
    except TimeoutError as e:
        return {"success": False, "error": "LLM_TIMEOUT", "details": str(e)}
    
    except ValueError as e:
        return {"success": False, "error": "LLM_OUTPUT_INVALID", "details": str(e)}
    
    except Exception as e:
        logger.error(f"Async unexpected error: {e}", exc_info=True)
        return {"success": False, "error": "LLM_INVOCATION_ERROR", "details": str(e)}

def _build_retry_prompt(
    original_prompt: str,
    previous_response: str,
    error: Optional[Exception],
) -> str:
    error_desc = f"{type(error).__name__}: {str(error)[:200]}" if error else "invalid format"

    return f"""The following JSON output is invalid or truncated. Fix ONLY the JSON — do not change values or structure, just repair syntax issues.

Error: {error_desc}

Broken JSON:
```
{previous_response[:2000]}
```

Rules:
- Return ONLY valid JSON — no markdown fences, no explanatory text
- Complete all fields in the schema
- Ensure proper JSON syntax (commas, quotes, brackets)
- Keep output compact to avoid truncation

YOUR FIXED JSON OUTPUT:
"""
