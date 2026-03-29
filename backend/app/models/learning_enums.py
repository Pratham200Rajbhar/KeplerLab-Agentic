from enum import Enum


class LearningLevel(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class LearningGoalType(str, Enum):
    exam_prep = "exam_prep"
    career_switch = "career_switch"
    project_build = "project_build"
    concept_mastery = "concept_mastery"


class LearningPathStatus(str, Enum):
    active = "active"
    paused = "paused"
    completed = "completed"
    archived = "archived"


class LearningDayStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"


class LearningSessionStage(str, Enum):
    LESSON = "LESSON"
    INTERACTION = "INTERACTION"
    TASK = "TASK"
    QUIZ = "QUIZ"
    GAME = "GAME"
    COMPLETE = "COMPLETE"
