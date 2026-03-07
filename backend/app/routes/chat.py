"""Chat route — Re-exports the chat_v2 router.

The new modular chat pipeline lives in app/services/chat_v2/.
This file provides backward-compatible import for app/main.py.
"""

from app.services.chat_v2.router import router

__all__ = ["router"]
