from __future__ import annotations

import asyncio
import logging
import time
import jwt
from collections import deque
from typing import Dict, Optional
from fastapi import Request, HTTPException
from app.core.config import settings

logger = logging.getLogger(__name__)

# Sliding window rate limiter: user_id -> deque of timestamps
_buckets: Dict[str, deque] = {}
_locks: Dict[str, asyncio.Lock] = {}
_lock_for_buckets = asyncio.Lock()

# Limits config
GENERAL_LIMIT = 60
LLM_HEAVY_LIMIT = 20
WINDOW_SECONDS = 60
CLEANUP_INTERVAL_SECONDS = 300
BUCKET_TTL_SECONDS = 300

LLM_HEAVY_ENDPOINTS = {"/chat", "/flashcard", "/quiz", "/ppt"}

def _get_user_id(request: Request) -> Optional[str]:
    # 1. Check x-user-id header
    user_id = request.headers.get("x-user-id")
    if user_id:
        return user_id

    # 2. Check Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        try:
            token = auth_header[7:]
            # Decode without verification as per requirements
            payload = jwt.decode(token, options={"verify_signature": False})
            return payload.get("sub") or payload.get("user_id")
        except Exception:
            pass
    return None

async def _get_lock(user_id: str) -> asyncio.Lock:
    async with _lock_for_buckets:
        if user_id not in _locks:
            _locks[user_id] = asyncio.Lock()
        return _locks[user_id]

async def check_rate_limit(user_id: str, endpoint_path: str) -> None:
    limit = GENERAL_LIMIT
    for path in LLM_HEAVY_ENDPOINTS:
        if endpoint_path.startswith(path):
            limit = LLM_HEAVY_LIMIT
            break

    lock = await _get_lock(user_id)
    async with lock:
        now = time.time()
        if user_id not in _buckets:
            _buckets[user_id] = deque()
        
        bucket = _buckets[user_id]
        
        # Remove old timestamps
        while bucket and bucket[0] < now - WINDOW_SECONDS:
            bucket.popleft()
            
        if len(bucket) >= limit:
            logger.warning("Rate limit exceeded for user %s on %s", user_id, endpoint_path)
            raise HTTPException(
                status_code=429, 
                detail="Rate limit exceeded. Try again later."
            )
            
        bucket.append(now)

async def rate_limit_middleware(request: Request, call_next):
    user_id = _get_user_id(request)
    if not user_id:
        # If no user_id, we can't rate limit per user, or we could use IP.
        # Requirements say per user_id, so we skip if not found or use "anonymous".
        user_id = "anonymous_" + (request.client.host if request.client else "unknown")

    try:
        await check_rate_limit(user_id, request.url.path)
    except HTTPException as exc:
        if exc.status_code == 429:
            return await _create_429_response(exc.detail)
        raise

    return await call_next(request)

async def _create_429_response(detail: str):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=429,
        content={"detail": detail}
    )

async def cleanup_buckets_task():
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
        async with _lock_for_buckets:
            now = time.time()
            to_remove = []
            for user_id, bucket in _buckets.items():
                # If bucket is empty or last request was long ago
                if not bucket or bucket[-1] < now - BUCKET_TTL_SECONDS:
                    to_remove.append(user_id)
            
            for user_id in to_remove:
                _buckets.pop(user_id, None)
                _locks.pop(user_id, None)
            
            if to_remove:
                logger.info("Cleaned up %d inactive rate limit buckets", len(to_remove))

# Start cleanup task in background when module is imported? 
# Better to do it in lifespan, but requirements just say implement it.
# We'll expect main.py to integrate it if needed, but for now we have the logic.
