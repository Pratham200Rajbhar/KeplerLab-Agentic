from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
import warnings

import requests
from langchain_core.language_models.llms import LLM
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_ollama import ChatOllama

from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

warnings.simplefilter("ignore", UserWarning)

_PROVIDERS: Dict[str, Any] = {}

_llm_cache: Dict[tuple, Any] = {}
_LLM_CACHE_MAX = 16

def _register_providers():
    if _PROVIDERS:
        return

    _PROVIDERS["OLLAMA"] = _build_ollama
    _PROVIDERS["GOOGLE"] = _build_google
    _PROVIDERS["NVIDIA"] = _build_nvidia
    _PROVIDERS["MYOPENLM"] = _build_openlm

def _common_kwargs(
    temperature: float,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
    **extra_kwargs
) -> dict:
    kwargs = {
        "temperature": temperature,
    }
    if settings.LLM_TIMEOUT is not None:
        kwargs["timeout"] = settings.LLM_TIMEOUT
    
    if max_tokens:
        kwargs["max_tokens"] = max_tokens
    
    if top_p is not None:
        kwargs["top_p"] = top_p
    
    kwargs.update(extra_kwargs)
    return kwargs

def _build_ollama(
    temperature: float = None,
    top_p: float = None,
    max_tokens: int = None,
    **extra_kwargs
):
    temp = temperature if temperature is not None else settings.LLM_TEMPERATURE_CHAT
    kw = _common_kwargs(temp, top_p, max_tokens, **extra_kwargs)
    kw["model"] = settings.OLLAMA_MODEL
    
    if "top_k" in extra_kwargs:
        kw["top_k"] = extra_kwargs["top_k"]
    
    return ChatOllama(**kw)

def _build_google(
    temperature: float = None,
    top_p: float = None,
    max_tokens: int = None,
    **extra_kwargs
):
    temp = temperature if temperature is not None else settings.LLM_TEMPERATURE_CHAT
    tokens = max_tokens if max_tokens is not None else settings.LLM_MAX_TOKENS_CHAT
    
    return VertexGCPChat(
        model_name=settings.GOOGLE_MODEL,
        temperature=temp,
        max_tokens=tokens,
    )

def _build_nvidia(
    temperature: float = None,
    top_p: float = None,
    max_tokens: int = None,
    **extra_kwargs
):
    temp = temperature if temperature is not None else settings.LLM_TEMPERATURE_CHAT
    kw = _common_kwargs(temp, top_p, max_tokens, **extra_kwargs)
    kw.update(
        model=settings.NVIDIA_MODEL,
        api_key=settings.NVIDIA_API_KEY,
        streaming=True,
        model_kwargs={"chat_template_kwargs": {"thinking": False}}
    )
    
    return ChatNVIDIA(**kw)

def _build_openlm(
    temperature: float = None,
    top_p: float = None,
    max_tokens: int = None,
    **extra_kwargs
):
    return MyOpenLM(
        temperature=temperature or settings.LLM_TEMPERATURE_CHAT,
        max_tokens=max_tokens or settings.LLM_MAX_TOKENS_CHAT,
    )

def get_llm(
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
    provider: Optional[str] = None,
    mode: str = "chat",
    **kwargs
):
    _register_providers()
    
    _TEMP_MAP = {
        "chat": settings.LLM_TEMPERATURE_CHAT,
        "creative": settings.LLM_TEMPERATURE_CREATIVE,
        "structured": settings.LLM_TEMPERATURE_STRUCTURED,
        "code": settings.LLM_TEMPERATURE_CODE,
    }
    
    temp = temperature if temperature is not None else _TEMP_MAP.get(mode, settings.LLM_TEMPERATURE_CHAT)
    p = top_p if top_p is not None else settings.LLM_TOP_P_CHAT
    tokens = max_tokens if max_tokens is not None else settings.LLM_MAX_TOKENS_CHAT
    
    active_provider = provider if provider else settings.LLM_PROVIDER

    builder = _PROVIDERS.get(active_provider)
    if builder is None:
        logger.warning(f"Unknown LLM_PROVIDER '{active_provider}', falling back to OLLAMA")
        builder = _PROVIDERS["OLLAMA"]
    
    cache_key = ("llm", active_provider, temp, p, tokens, tuple(sorted(kwargs.items())))
    cached = _llm_cache.get(cache_key)
    if cached is not None:
        return cached
    
    instance = builder(temperature=temp, top_p=p, max_tokens=tokens, **kwargs)
    if len(_llm_cache) >= _LLM_CACHE_MAX:
        _llm_cache.pop(next(iter(_llm_cache)))
    _llm_cache[cache_key] = instance
    return instance

def get_llm_structured(
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
    provider: Optional[str] = None,
    **kwargs
):
    _register_providers()
    
    temp = temperature if temperature is not None else settings.LLM_TEMPERATURE_STRUCTURED
    p = top_p if top_p is not None else settings.LLM_TOP_P_STRUCTURED
    tokens = max_tokens if max_tokens is not None else settings.LLM_MAX_TOKENS
    
    active_provider = provider if provider else settings.LLM_PROVIDER
    if "top_k" not in kwargs and active_provider in ("GOOGLE", "OLLAMA"):
        kwargs["top_k"] = settings.LLM_TOP_K
    
    builder = _PROVIDERS.get(active_provider)
    if builder is None:
        logger.warning(f"Unknown LLM_PROVIDER '{active_provider}', falling back to OLLAMA")
        builder = _PROVIDERS["OLLAMA"]
    
    cache_key = ("structured", active_provider, temp, p, tokens, tuple(sorted(kwargs.items())))
    cached = _llm_cache.get(cache_key)
    if cached is not None:
        return cached
    
    instance = builder(temperature=temp, top_p=p, max_tokens=tokens, **kwargs)
    if len(_llm_cache) >= _LLM_CACHE_MAX:
        _llm_cache.pop(next(iter(_llm_cache)))
    _llm_cache[cache_key] = instance
    return instance

def extract_chunk_content(chunk) -> str:
    raw = getattr(chunk, "content", None)
    if isinstance(raw, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in raw
            if not (isinstance(part, dict) and part.get("type") == "thinking")
        )
    if isinstance(raw, str):
        return raw
    if raw is None:
        return ""
    return str(raw)

class MyOpenLM(LLM):

    api_url: str = settings.MYOPENLM_API_URL
    model_name: str = settings.MYOPENLM_MODEL
    temperature: float = 0.2
    max_tokens: int = 3000

    _RETRYABLE_CODES = {429, 500, 502, 503, 504}
    _MAX_RETRIES = 3

    @property
    def _llm_type(self) -> str:
        return "my_lm"

    def _build_payload(self, prompt: str) -> dict:
        return {
            "message": prompt,
            "model": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

    def _call(
        self, prompt: str, stop: Optional[List[str]] = None, *args: Any, **kwargs: Any
    ) -> str:
        last_exc: Optional[Exception] = None

        for attempt in range(self._MAX_RETRIES):
            try:
                resp = requests.post(
                    self.api_url,
                    json=self._build_payload(prompt),
                    headers={"Content-Type": "application/json"},
                    timeout=settings.LLM_TIMEOUT,
                )
                resp.raise_for_status()
                return resp.json()["data"]["response"]

            except requests.exceptions.HTTPError as exc:
                last_exc = exc
                if resp.status_code in self._RETRYABLE_CODES:
                    delay = 2 ** attempt
                    logger.warning("LLM %d — retry %d/%d in %ds", resp.status_code, attempt + 1, self._MAX_RETRIES, delay)
                    time.sleep(delay)
                    continue
                raise

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
                last_exc = exc
                delay = 2 ** attempt
                logger.warning("LLM connection error — retry %d/%d in %ds: %s", attempt + 1, self._MAX_RETRIES, delay, exc)
                time.sleep(delay)
                continue

            except Exception as exc:
                logger.error("LLM call error: %s", exc)
                raise

        raise last_exc or Exception("LLM call failed after all retries")

    async def _acall(
        self, prompt: str, stop: Optional[List[str]] = None, *args: Any, **kwargs: Any
    ) -> str:
        import httpx
        import asyncio

        last_exc: Optional[Exception] = None

        for attempt in range(self._MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT) as client:
                    resp = await client.post(
                        self.api_url,
                        json=self._build_payload(prompt),
                        headers={"Content-Type": "application/json"},
                    )
                    resp.raise_for_status()
                    return resp.json()["data"]["response"]

            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code in self._RETRYABLE_CODES:
                    delay = 2 ** attempt
                    logger.warning("LLM %d — retry %d/%d in %ds", exc.response.status_code, attempt + 1, self._MAX_RETRIES, delay)
                    await asyncio.sleep(delay)
                    continue
                raise

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                last_exc = exc
                delay = 2 ** attempt
                logger.warning("LLM connection error — retry %d/%d in %ds: %s", attempt + 1, self._MAX_RETRIES, delay, exc)
                await asyncio.sleep(delay)
                continue

            except Exception as exc:
                logger.error("LLM call error: %s", exc)
                raise

        raise last_exc or Exception("LLM call failed after all retries")

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langchain_core.outputs import ChatResult, ChatGeneration

class VertexGCPChat(BaseChatModel):
    model_name: str = "gemini-2.5-flash"
    temperature: float = 0.2
    max_tokens: int = 1000

    @property
    def _llm_type(self) -> str:
        return "vertex_chat"

    def _convert_messages(self, messages: List[BaseMessage]) -> dict:
        contents = []
        for m in messages:
            if isinstance(m, HumanMessage):
                role = "user"
                parts = []
                if isinstance(m.content, str):
                    parts.append({"text": m.content})
                elif isinstance(m.content, list):
                    for p in m.content:
                        if p.get("type") == "text":
                            parts.append({"text": p["text"]})
                        elif p.get("type") == "image_url":
                            img_str = p.get("image_url", "")
                            if isinstance(img_str, dict):
                                img_str = img_str.get("url", "")
                            if img_str.startswith("data:"):
                                header, b64 = img_str.split(",", 1)
                                mime = header.split(":", 1)[1].split(";")[0]
                                parts.append({"inlineData": {"mimeType": mime, "data": b64}})
                contents.append({"role": role, "parts": parts})
            elif isinstance(m, AIMessage):
                contents.append({"role": "model", "parts": [{"text": str(m.content)}]})
            else:
                contents.append({"role": "user", "parts": [{"text": str(m.content)}]})
        return {
            "contents": contents,
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
            }
        }

    def _generate(
        self, messages: List[BaseMessage], stop: Optional[List[str]] = None, **kwargs: Any
    ) -> ChatResult:
        import requests
        from app.services.image_generation.gemini_service import _get_access_token, _get_project_id
        
        location = settings.VERTEX_LOCATION or "us-central1"
        url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{_get_project_id()}/locations/{location}/publishers/google/models/{self.model_name.split('/')[-1]}:generateContent"
        headers = {"Authorization": f"Bearer {_get_access_token()}", "Content-Type": "application/json"}
        payload = self._convert_messages(messages)
        
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])
        
    async def _agenerate(
        self, messages: List[BaseMessage], stop: Optional[List[str]] = None, **kwargs: Any
    ) -> ChatResult:
        import httpx
        from app.services.image_generation.gemini_service import _get_access_token, _get_project_id
        
        location = settings.VERTEX_LOCATION or "us-central1"
        url = f"https://{location}-aiplatform.googleapis.com/v1/projects/{_get_project_id()}/locations/{location}/publishers/google/models/{self.model_name.split('/')[-1]}:generateContent"
        headers = {"Authorization": f"Bearer {_get_access_token()}", "Content-Type": "application/json"}
        payload = self._convert_messages(messages)
        
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            
            parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts)
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])
