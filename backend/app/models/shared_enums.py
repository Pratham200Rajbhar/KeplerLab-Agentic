"""Shared enumerations used across multiple route modules."""

from enum import Enum


class DifficultyLevel(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class IntentOverride(str, Enum):
    """Explicit intent set by frontend slash commands.

    The backend NEVER calls an LLM to guess intent — it is always
    set by the frontend via this enum.
    """
    AGENT = "AGENT"
    WEB_RESEARCH = "WEB_RESEARCH"
    CODE_EXECUTION = "CODE_EXECUTION"
    WEB_SEARCH = "WEB_SEARCH"
