"""Rate limiting middleware — DISABLED (no limits applied)."""

from __future__ import annotations

import logging
from typing import Dict
from fastapi import Request

logger = logging.getLogger(__name__)


async def check_rate_limit(user_id: str, endpoint_type: str) -> None:
    """Rate limiting is disabled — always allows requests."""
    return


async def get_rate_limit_info(user_id: str, endpoint_type: str) -> Dict[str, int]:
    """Rate limiting is disabled — returns unlimited info."""
    return {"limit": -1, "remaining": -1, "reset_in": 0}


async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting is disabled — passes all requests through."""
    return await call_next(request)
