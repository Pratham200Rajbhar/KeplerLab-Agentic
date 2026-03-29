"""
Markdown DSL Parser for Agent Skills.

Parses structured markdown skill definitions into SkillDefinition objects.

Expected format:
    # Skill: <name>
    ## Input
    variable_name: {user_input}
    ## Steps
    1. Do something with {variable_name}
    2. Analyze the results
    ## Output
    - Summary report
    ## Rules
    - Use formal tone
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Section header patterns ────────────────────────────────

_SKILL_TITLE_RE = re.compile(r"^#\s+Skill:\s*(.+)", re.IGNORECASE)
_SECTION_RE = re.compile(r"^##\s+(.+)", re.IGNORECASE)
_VARIABLE_RE = re.compile(r"\{(\w+)\}")
_STEP_RE = re.compile(r"^\s*(\d+)\.\s+(.+)")
_LIST_ITEM_RE = re.compile(r"^\s*[-*]\s+(.+)")
_INPUT_VAR_RE = re.compile(r"^\s*(\w+)\s*:\s*(.+)")


@dataclass
class SkillVariable:
    """A variable defined in the Input section."""
    name: str
    default_value: Optional[str] = None
    description: Optional[str] = None
    options: List[str] = field(default_factory=list)
    input_type: str = "text"


@dataclass
class SkillStep:
    """A single step in the skill workflow."""
    index: int
    instruction: str
    tool_hint: Optional[str] = None  # e.g. "rag", "web_search", "python_auto"
    variables_used: List[str] = field(default_factory=list)
    condition: Optional[str] = None  # IF/ELSE condition text


@dataclass
class SkillDefinition:
    """Complete parsed skill definition."""
    title: str
    description: Optional[str] = None
    inputs: List[SkillVariable] = field(default_factory=list)
    steps: List[SkillStep] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    rules: List[str] = field(default_factory=list)
    all_variables: List[str] = field(default_factory=list)
    raw_markdown: str = ""


# ── Tool hint detection ────────────────────────────────────

_TOOL_HINTS = {
    "rag": re.compile(
        r"\b(search documents?|search uploaded|find in documents?|retrieve|look up in|"
        r"query documents?|search materials?|from uploaded|search notes?)\b",
        re.IGNORECASE,
    ),
    "web_search": re.compile(
        r"\b(search the web|search online|web search|google|find online|"
        r"latest news|current events|look up online|search internet)\b",
        re.IGNORECASE,
    ),
    "research": re.compile(
        r"\b(deep research|research .{0,30}comprehensively|multi-source research|"
        r"in-depth analysis|thorough investigation|comprehensive report)\b",
        re.IGNORECASE,
    ),
    "python_auto": re.compile(
        r"\b(generate code|run code|execute|python|create .{0,20}(chart|graph|plot|pdf|csv|file)|"
        r"data analysis|visuali[sz]e|calculate|compute|process data|"
        r"train model|statistics|export .{0,20}(pdf|csv|xlsx|docx))\b",
        re.IGNORECASE,
    ),
    "llm": re.compile(
        r"\b(summari[sz]e|synthesize|rewrite|transform|convert|translate|"
        r"compose|draft|outline|explain|analyze text|extract key|format)\b",
        re.IGNORECASE,
    ),
}


def _detect_tool_hint(text: str) -> Optional[str]:
    """Detect which tool a step likely maps to based on keywords."""
    for tool_name, pattern in _TOOL_HINTS.items():
        if pattern.search(text):
            return tool_name
    return None


def _extract_variables(text: str) -> List[str]:
    """Extract all {variable_name} references from text."""
    return list(set(_VARIABLE_RE.findall(text)))


def _parse_condition(text: str) -> tuple[Optional[str], str]:
    """Extract IF/ELSE condition from step text if present."""
    cond_match = re.match(r"^\s*(?:IF|WHEN)\s+(.+?):\s*(.+)", text, re.IGNORECASE)
    if cond_match:
        return cond_match.group(1).strip(), cond_match.group(2).strip()
    return None, text


# ── Main Parser ────────────────────────────────────────────

class MarkdownParseError(Exception):
    """Raised when skill markdown is structurally invalid."""
    pass


def parse_skill_markdown(markdown: str) -> SkillDefinition:
    """
    Parse a skill markdown document into a SkillDefinition.

    Raises MarkdownParseError if the markdown is structurally invalid.
    """
    if not markdown or not markdown.strip():
        raise MarkdownParseError("Skill markdown is empty")

    lines = markdown.strip().split("\n")
    title: Optional[str] = None
    description_lines: List[str] = []
    current_section: Optional[str] = None
    sections: Dict[str, List[str]] = {}

    # First pass: extract title and split into sections
    for line in lines:
        title_match = _SKILL_TITLE_RE.match(line)
        if title_match:
            title = title_match.group(1).strip()
            current_section = "__header__"
            continue

        section_match = _SECTION_RE.match(line)
        if section_match:
            current_section = section_match.group(1).strip().lower()
            sections.setdefault(current_section, [])
            continue

        if current_section == "__header__":
            stripped = line.strip()
            if stripped:
                description_lines.append(stripped)
        elif current_section and current_section in sections:
            sections[current_section].append(line)

    # Fallback title
    if not title:
        # Try to find any h1
        for line in lines:
            h1_match = re.match(r"^#\s+(.+)", line)
            if h1_match:
                title = h1_match.group(1).strip()
                break
    if not title:
        title = "Untitled Skill"

    # Parse Input section
    inputs: List[SkillVariable] = []
    for line in sections.get("input", sections.get("inputs", [])):
        var_match = _INPUT_VAR_RE.match(line)
        if var_match:
            var_name = var_match.group(1).strip()
            rest = var_match.group(2).strip()
            
            options_match = re.search(r"\[(.*?)\]", rest)
            type_match = re.search(r"\((.*?)\)", rest)
            
            options = []
            if options_match:
                options = [o.strip() for o in options_match.group(1).split(",") if o.strip()]
            
            input_type = "text"
            if type_match:
                input_type = type_match.group(1).strip()

            ref_match = _VARIABLE_RE.match(rest)
            default = None if ref_match else rest
            inputs.append(SkillVariable(
                name=var_name,
                default_value=default,
                description=rest,
                options=options,
                input_type=input_type,
            ))

    # Parse Steps section
    steps: List[SkillStep] = []
    step_lines = sections.get("steps", sections.get("workflow", []))
    for line in step_lines:
        step_match = _STEP_RE.match(line)
        if step_match:
            idx = int(step_match.group(1))
            raw_instruction = step_match.group(2).strip()
            condition, instruction = _parse_condition(raw_instruction)
            tool_hint = _detect_tool_hint(instruction)
            variables_used = _extract_variables(instruction)

            steps.append(SkillStep(
                index=idx,
                instruction=instruction,
                tool_hint=tool_hint,
                variables_used=variables_used,
                condition=condition,
            ))

    if not steps:
        raise MarkdownParseError(
            "Skill must have at least one numbered step in the ## Steps section. "
            "Format: '1. Do something'"
        )

    # Parse Output section
    outputs: List[str] = []
    for line in sections.get("output", sections.get("outputs", [])):
        item_match = _LIST_ITEM_RE.match(line)
        if item_match:
            outputs.append(item_match.group(1).strip())

    # Parse Rules section
    rules: List[str] = []
    for line in sections.get("rules", sections.get("constraints", [])):
        item_match = _LIST_ITEM_RE.match(line)
        if item_match:
            rules.append(item_match.group(1).strip())

    # Collect all variables across the entire markdown
    all_variables = list(set(_extract_variables(markdown)))

    definition = SkillDefinition(
        title=title,
        description=" ".join(description_lines) if description_lines else None,
        inputs=inputs,
        steps=steps,
        outputs=outputs,
        rules=rules,
        all_variables=all_variables,
        raw_markdown=markdown,
    )

    logger.info(
        "Parsed skill '%s': %d inputs, %d steps, %d outputs, %d rules, variables=%s",
        title, len(inputs), len(steps), len(outputs), len(rules), all_variables,
    )
    return definition


def skill_to_json(definition: SkillDefinition) -> Dict[str, Any]:
    """Convert a SkillDefinition to a serializable JSON dict."""
    return {
        "title": definition.title,
        "description": definition.description,
        "inputs": [
            {
                "name": v.name, 
                "default_value": v.default_value, 
                "description": v.description,
                "options": v.options,
                "input_type": v.input_type
            }
            for v in definition.inputs
        ],
        "steps": [
            {
                "index": s.index,
                "instruction": s.instruction,
                "tool_hint": s.tool_hint,
                "variables_used": s.variables_used,
                "condition": s.condition,
            }
            for s in definition.steps
        ],
        "outputs": definition.outputs,
        "rules": definition.rules,
        "all_variables": definition.all_variables,
    }


def validate_skill_markdown(markdown: str) -> tuple[bool, Optional[str]]:
    """Validate skill markdown without fully parsing. Returns (is_valid, error_message)."""
    try:
        parse_skill_markdown(markdown)
        return True, None
    except MarkdownParseError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error parsing skill: {e}"
