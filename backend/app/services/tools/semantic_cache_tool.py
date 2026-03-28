from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass

from pydantic import BaseModel, Field


@dataclass
class _CacheEntry:
    value: str
    expires_at: float


_CACHE: dict[str, _CacheEntry] = {}


class SemanticCachePutInput(BaseModel):
    key_text: str = Field(min_length=1)
    value: str = Field(min_length=1)
    ttl_seconds: int = Field(default=600, ge=10, le=86400)


class SemanticCacheGetInput(BaseModel):
    key_text: str = Field(min_length=1)


class SemanticCacheGetOutput(BaseModel):
    hit: bool
    value: str | None = None


def _cache_key(text: str) -> str:
    normalized = " ".join(text.lower().split())
    return hashlib.sha1(normalized.encode("utf-8", errors="ignore")).hexdigest()


def cache_put(payload: SemanticCachePutInput) -> None:
    key = _cache_key(payload.key_text)
    _CACHE[key] = _CacheEntry(value=payload.value, expires_at=time.time() + payload.ttl_seconds)


def cache_get(payload: SemanticCacheGetInput) -> SemanticCacheGetOutput:
    key = _cache_key(payload.key_text)
    entry = _CACHE.get(key)
    if not entry:
        return SemanticCacheGetOutput(hit=False)
    if entry.expires_at < time.time():
        _CACHE.pop(key, None)
        return SemanticCacheGetOutput(hit=False)
    return SemanticCacheGetOutput(hit=True, value=entry.value)
