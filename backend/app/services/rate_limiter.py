from __future__ import annotations

import logging
from typing import Dict
from fastapi import Request

logger = logging.getLogger(__name__)

async def check_rate_limit(user_id: str, endpoint_type: str) -> None:
    return

async def rate_limit_middleware(request: Request, call_next):
    return await call_next(request)
