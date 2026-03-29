"""
Skill Compiler — uses LLM to expand vague skill steps into a concrete execution plan.

Takes a parsed SkillDefinition + user-supplied variables and produces
an optimized plan with tool assignments.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.services.skills.markdown_parser import SkillDefinition, skill_to_json
from app.services.skills.tool_mapper import map_steps_to_tools

logger = logging.getLogger(__name__)

COMPILER_SYSTEM_PROMPT = """You are a skill execution planner.
Given a user's skill definition (parsed from Markdown), produce a concrete step-by-step execution plan.

For each step, output a JSON object with:
- "index": step number (int)
- "instruction": clear, actionable instruction text
- "tool_hint": one of "rag", "web_search", "research", "python_auto", "llm" (which tool to use)
- "query": the specific query or instruction to pass to the tool

Rules:
1. Expand vague steps into specific, actionable instructions
2. Substitute all {variable} placeholders with their actual values
3. Keep steps focused — each should map to exactly ONE tool
4. If a step involves creating files/visualizations, use "python_auto"
5. If a step involves querying uploaded documents, use "rag"
6. If a step is pure text synthesis/summarization, use "llm"
7. Preserve the original step order
8. Do NOT add steps that weren't implied by the original

Reply with ONLY a JSON array of step objects. No markdown, no explanation."""

COMPILER_USER_TEMPLATE = """Skill: {title}
Description: {description}

Variables:
{variables_text}

Original Steps:
{steps_text}

Expected Outputs:
{outputs_text}

Rules/Constraints:
{rules_text}

Produce the optimized execution plan as a JSON array."""


async def compile_skill(
    definition: SkillDefinition,
    variables: Dict[str, str],
    has_materials: bool = False,
) -> List[Dict[str, Any]]:
    """
    Compile a skill definition into an optimized execution plan.

    Uses LLM to expand and clarify steps, then maps each to a tool.

    Falls back to direct tool mapping from parser hints if LLM fails.
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
        })

    # Try LLM compilation
    try:
        compiled = await _llm_compile(definition, variables, substituted_steps)
        if compiled and len(compiled) > 0:
            shaped = _enforce_plan_shape(compiled, substituted_steps)
            if shaped:
                # Map tools using our tool mapper
                return map_steps_to_tools(shaped, has_materials)
            logger.warning(
                "LLM compiler returned invalid shape for skill '%s' (expected %d steps, got %d). Falling back.",
                definition.title,
                len(substituted_steps),
                len(compiled),
            )
    except Exception as e:
        logger.warning("LLM compilation failed, falling back to direct mapping: %s", e)

    # Fallback: use substituted steps with tool mapper
    logger.info("Using fallback direct tool mapping for skill '%s'", definition.title)
    return map_steps_to_tools(substituted_steps, has_materials)


def _enforce_plan_shape(
    compiled_steps: List[Dict[str, Any]],
    source_steps: List[Dict[str, Any]],
) -> Optional[List[Dict[str, Any]]]:
    """Ensure compiled plan preserves source step count/order/indexes."""
    if len(compiled_steps) != len(source_steps):
        return None

    compiled_by_index: Dict[int, Dict[str, Any]] = {}
    for step in compiled_steps:
        try:
            idx = int(step.get("index"))
        except (TypeError, ValueError):
            return None
        if idx in compiled_by_index:
            return None
        compiled_by_index[idx] = step

    normalized: List[Dict[str, Any]] = []
    for source in source_steps:
        src_idx = int(source.get("index", 0))
        compiled = compiled_by_index.get(src_idx)
        if not compiled:
            return None

        instruction = (compiled.get("instruction") or source.get("instruction") or "").strip()
        if not instruction:
            return None

        query = (compiled.get("query") or instruction).strip()
        tool_hint = compiled.get("tool_hint") or compiled.get("tool") or source.get("tool_hint")
        condition = compiled.get("condition")
        if condition is None:
            condition = source.get("condition")

        normalized.append({
            "index": src_idx,
            "instruction": instruction,
            "tool_hint": tool_hint,
            "query": query,
            "condition": condition,
        })

    return normalized


async def _llm_compile(
    definition: SkillDefinition,
    variables: Dict[str, str],
    substituted_steps: List[dict],
) -> Optional[List[dict]]:
    """Use LLM to compile skill steps into an optimized plan."""
    from app.services.llm_service.llm import get_llm, extract_chunk_content

    skill_json = skill_to_json(definition)

    variables_text = "\n".join(
        f"  {k} = {v}" for k, v in variables.items()
    ) or "  (none)"

    steps_text = "\n".join(
        f"  {s['index']}. {s['instruction']}"
        + (f" [IF: {s['condition']}]" if s.get('condition') else "")
        for s in substituted_steps
    )

    outputs_text = "\n".join(f"  - {o}" for o in definition.outputs) or "  (unspecified)"
    rules_text = "\n".join(f"  - {r}" for r in definition.rules) or "  (none)"

    user_prompt = COMPILER_USER_TEMPLATE.format(
        title=definition.title,
        description=definition.description or "N/A",
        variables_text=variables_text,
        steps_text=steps_text,
        outputs_text=outputs_text,
        rules_text=rules_text,
    )

    llm = get_llm(temperature=0.1, max_tokens=2000, mode="structured")
    full_prompt = f"{COMPILER_SYSTEM_PROMPT}\n\n{user_prompt}"

    # Use ainvoke for a single response
    result = await llm.ainvoke(full_prompt)
    response = extract_chunk_content(result)

    if not response:
        return None

    # Parse JSON from response
    try:
        # Try to extract JSON array
        text = response.strip()
        # Remove markdown code fences if present
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
        steps = json.loads(text)
        if isinstance(steps, list):
            # Validate structure
            valid_steps = []
            for s in steps:
                if isinstance(s, dict) and "instruction" in s:
                    valid_steps.append({
                        "index": s.get("index", len(valid_steps) + 1),
                        "instruction": s["instruction"],
                        "tool_hint": s.get("tool_hint") or s.get("tool"),
                        "query": s.get("query", s.get("instruction")),
                        "condition": s.get("condition"),
                    })
            if valid_steps:
                logger.info("LLM compiled %d steps for skill '%s'",
                           len(valid_steps), definition.title)
                return valid_steps
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse LLM compilation output as JSON: %s", e)

    return None
