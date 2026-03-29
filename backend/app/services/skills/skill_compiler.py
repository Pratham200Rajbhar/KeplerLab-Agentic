"""
Skill Compiler — deterministically maps skill steps to an execution plan.

Takes a parsed SkillDefinition + user-supplied variables and produces
an optimized plan with tool assignments and variable substitutions.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.services.skills.markdown_parser import SkillDefinition
from app.services.skills.tool_mapper import map_steps_to_tools

logger = logging.getLogger(__name__)


async def compile_skill(
    definition: SkillDefinition,
    variables: Dict[str, str],
    has_materials: bool = False,
) -> List[Dict[str, Any]]:
    """
    Compile a skill definition into an execution plan.

    Deterministically substitutes variables and maps tools without an LLM
    to ensure instant compilation and robust execution.
    """
    # Substitute variables in the skill definition
    substituted_steps = []
    for step in definition.steps:
        instruction = step.instruction
        condition = step.condition
        for var_name, var_value in variables.items():
            instruction = instruction.replace(f"{{{var_name}}}", str(var_value))
            if condition:
                condition = condition.replace(f"{{{var_name}}}", str(var_value))
        
        substituted_steps.append({
            "index": step.index,
            "instruction": instruction,
            "tool_hint": step.tool_hint,
            "condition": condition,
            "query": instruction,  # Instruct executor to use substituted instruction directly
        })

    logger.info("Deterministically mapped %d steps for skill '%s'", len(substituted_steps), definition.title)
    
    # Map steps to tools
    return map_steps_to_tools(substituted_steps, has_materials)
