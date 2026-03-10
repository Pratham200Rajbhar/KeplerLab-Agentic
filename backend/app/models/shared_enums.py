from enum import Enum

class DifficultyLevel(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"

class IntentOverride(str, Enum):
    AGENT = "AGENT"
    WEB_RESEARCH = "WEB_RESEARCH"
    CODE_EXECUTION = "CODE_EXECUTION"
    WEB_SEARCH = "WEB_SEARCH"
