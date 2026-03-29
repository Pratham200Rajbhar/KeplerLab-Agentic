from __future__ import annotations

from typing import Dict, List


_DAY_TEMPLATES = [
    "Core Concepts of {topic}",
    "Hands-On Basics in {topic}",
    "Common Patterns in {topic}",
    "Applied Practice for {topic}",
    "Problem Solving with {topic}",
    "Real-World Use Cases of {topic}",
    "Intermediate Workflows in {topic}",
    "Performance and Optimization in {topic}",
    "Debugging and Pitfalls in {topic}",
    "Advanced Strategies in {topic}",
    "Build and Iterate with {topic}",
]

_LEVEL_DESCRIPTIONS = {
    "beginner": "Beginner-friendly, step-by-step learning.",
    "intermediate": "Intermediate progression with practical depth.",
    "advanced": "Advanced depth with project-oriented rigor.",
}

_GOAL_DESCRIPTIONS = {
    "exam_prep": "Optimized for exam-style practice and recall.",
    "career_switch": "Optimized for job-ready practical outcomes.",
    "project_build": "Optimized for project execution and delivery.",
    "concept_mastery": "Optimized for conceptual depth and retention.",
}


def generate_curriculum(
    topic: str,
    duration_days: int,
    level: str,
    goal_type: str,
) -> List[Dict[str, str]]:
    """Generate deterministic day metadata for a learning path."""
    cleaned_topic = (topic or "Topic").strip()
    level_hint = _LEVEL_DESCRIPTIONS.get(level, _LEVEL_DESCRIPTIONS["beginner"])
    goal_hint = _GOAL_DESCRIPTIONS.get(goal_type, _GOAL_DESCRIPTIONS["concept_mastery"])

    curriculum: List[Dict[str, str]] = []
    for day in range(1, duration_days + 1):
        if day == 1:
            title = f"Introduction to {cleaned_topic}"
            description = (
                f"Set foundations, vocabulary, and mental models for {cleaned_topic}. "
                f"{level_hint}"
            )
        elif day == duration_days:
            title = f"Capstone Project: Build with {cleaned_topic}"
            description = (
                f"Integrate everything into a project-based final delivery. {goal_hint}"
            )
        else:
            template = _DAY_TEMPLATES[(day - 2) % len(_DAY_TEMPLATES)]
            title = template.format(topic=cleaned_topic)
            description = (
                f"Day {day} focuses on progressive learning outcomes for {cleaned_topic}. "
                f"{goal_hint}"
            )

        curriculum.append(
            {
                "day_number": day,
                "title": title,
                "description": description,
            }
        )

    return curriculum
