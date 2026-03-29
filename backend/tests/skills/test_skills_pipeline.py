#!/usr/bin/env python3
"""
Full Agent Skills Pipeline Test Suite
======================================

Tests every layer of the skills system:
  Layer 1 — Markdown Parser (parse_skill_markdown, validate_skill_markdown)
  Layer 2 — Tool Mapper (map_step_to_tool, map_steps_to_tools)
  Layer 3 — Skill Compiler (compile_skill, fallback path)
  Layer 4 — Skill Executor (SSE format, event structure)
  Layer 5 — Skill Service CRUD (create, read, update, delete via Prisma)
  Layer 6 — Skill Service Run Orchestration (full pipeline)
  Layer 7 — E2E: 10 test-case skill definitions parsed + compiled + executed

Results and logs are written to  tests/skills/output/

Usage:
    cd backend
    python tests/skills/test_skills_pipeline.py
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
import time
import traceback
from dataclasses import asdict, is_dataclass
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Paths ──────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent.parent          # backend/
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Ensure backend is on sys.path
sys.path.insert(0, str(BACKEND_DIR))

# ── Logging ────────────────────────────────────────────────

LOG_FILE = OUTPUT_DIR / "test_run.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("skills_test")

# ── Result accumulator ─────────────────────────────────────

class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error: Optional[str] = None
        self.output: Any = None
        self.elapsed: float = 0.0

    def to_dict(self):
        return {
            "name": self.name,
            "passed": self.passed,
            "error": self.error,
            "elapsed_seconds": round(self.elapsed, 3),
            "output_preview": str(self.output)[:500] if self.output else None,
        }

ALL_RESULTS: List[TestResult] = []


def _run_test(name: str):
    """Decorator that catches exceptions and records results."""
    def decorator(fn):
        async def wrapper(*args, **kwargs):
            result = TestResult(name)
            t0 = time.time()
            try:
                output = await fn(*args, **kwargs)
                result.passed = True
                result.output = output
            except Exception as exc:
                result.error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
                logger.error("FAIL  %s — %s", name, exc)
            result.elapsed = time.time() - t0
            ALL_RESULTS.append(result)
            status = "PASS" if result.passed else "FAIL"
            logger.info("%s  %s  (%.2fs)", status, name, result.elapsed)
            return result
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════
#  TEST CASE SKILL DEFINITIONS  (from skiils/test_case.md)
# ═══════════════════════════════════════════════════════════

TEST_SKILLS: List[Dict[str, Any]] = [
    {
        "id": 1,
        "title": "Study Pack Generator",
        "markdown": """# Skill: Study Pack Generator

## Input
topic: {user_input}

## Steps
1. Search uploaded documents for material about {topic}
2. Summarize the key concepts into a concise study guide
3. Generate flashcards in Q&A format from the summary
4. Create a 10-question quiz with multiple-choice answers
5. Export the study pack as a formatted PDF file

## Output
- Study summary
- Flashcards
- Quiz
- PDF file

## Rules
- Keep flashcards under 50 words each
- Quiz must have 4 options per question
""",
        "variables": {"topic": "Machine Learning Basics", "user_input": "Machine Learning Basics"},
        "expected_tools": ["rag", "llm", "llm", "llm", "python_auto"],
    },
    {
        "id": 2,
        "title": "Data Analysis Pipeline",
        "markdown": """# Skill: Data Analysis Pipeline

## Input
objective: {user_input}

## Steps
1. Search uploaded documents to understand the dataset structure
2. Generate Python code to compute descriptive statistics using pandas
3. Create visualizations: bar chart, histogram, and scatter plot
4. Summarize key insights and patterns found

## Output
- Statistical summary
- Charts and visualizations
- Key insights report

## Rules
- Use pandas and matplotlib
- Include data quality checks
- Generate at least 3 visualizations
""",
        "variables": {"objective": "Analyze sales trends", "user_input": "Analyze sales trends"},
        "expected_tools": ["rag", "python_auto", "python_auto", "llm"],
    },
    {
        "id": 3,
        "title": "Video Summary Generator",
        "markdown": """# Skill: Video Summary Generator

## Input
topic: {user_input}

## Steps
1. Search uploaded documents for content about {topic}
2. Summarize the document into a narrated script with sections
3. Generate Python code to create a presentation with visuals
4. Export the presentation as a downloadable file

## Output
- Narrated script
- Presentation file

## Rules
- Script should be 3-5 minutes when read aloud
- Include visual cues in the script
""",
        "variables": {"topic": "Climate Change", "user_input": "Climate Change"},
        "expected_tools": ["rag", "llm", "python_auto", "python_auto"],
    },
    {
        "id": 4,
        "title": "Website Builder",
        "markdown": """# Skill: Website Builder

## Input
topic: {user_input}
style: {style}

## Steps
1. Search the web for best practices and examples about {topic}
2. Draft the HTML structure with semantic tags and content about {topic}
3. Generate CSS styles for a modern, responsive {style} design
4. Generate Python code to save index.html and styles.css files

## Output
- index.html file
- styles.css file

## Rules
- Use semantic HTML5 tags
- Make it responsive
- Ensure the design is modern and clean
""",
        "variables": {"topic": "AI Startups", "style": "dark mode", "user_input": "AI Startups"},
        "expected_tools": ["web_search", "llm", "llm", "python_auto"],
    },
    {
        "id": 5,
        "title": "Python Automation Script",
        "markdown": """# Skill: Python Automation Script

## Input
task: {user_input}

## Steps
1. Search the web for best approaches to automate {task}
2. Generate Python code for the automation script with error handling
3. Execute the code to validate it runs without errors
4. Export the final script as a downloadable .py file

## Output
- Working Python script
- Validation results

## Rules
- Include comprehensive error handling
- Add docstrings and comments
- Follow PEP 8 standards
""",
        "variables": {"task": "file renaming by date", "user_input": "file renaming by date"},
        "expected_tools": ["web_search", "python_auto", "python_auto", "python_auto"],
    },
    {
        "id": 6,
        "title": "Research Report",
        "markdown": """# Skill: Research Report

## Input
topic: {user_input}

## Steps
1. Search uploaded documents for existing research about {topic}
2. Search the web for recent developments about {topic}
3. Research the topic comprehensively across multiple sources
4. Synthesize all findings into a structured report with introduction, findings, analysis, and conclusion

## Output
- Comprehensive research report
- Source citations

## Rules
- Use formal academic tone
- Cross-reference multiple sources
- Include at least 5 citations
""",
        "variables": {"topic": "Quantum Computing Applications", "user_input": "Quantum Computing Applications"},
        "expected_tools": ["rag", "web_search", "research", "llm"],
    },
    {
        "id": 7,
        "title": "Conditional Analysis",
        "markdown": """# Skill: Conditional Analysis

## Input
topic: {user_input}

## Steps
1. Search uploaded documents to check for dataset availability about {topic}
2. IF dataset found: Generate Python code for data analysis with statistics
3. IF no dataset: Summarize all relevant documents about {topic}
4. Generate a final report combining the analysis results

## Output
- Analysis report or Document summary

## Rules
- Clearly state which branch was taken
- Be thorough in analysis
""",
        "variables": {"topic": "Revenue Analysis", "user_input": "Revenue Analysis"},
        "expected_tools": ["rag", "python_auto", "llm", "llm"],
    },
    {
        "id": 8,
        "title": "Multi-Step Study Pipeline",
        "markdown": """# Skill: Multi-Step Study Pipeline

## Input
topic: {user_input}

## Steps
1. Search uploaded documents for material about {topic}
2. Summarize the content into structured study notes
3. Generate Python code to create a presentation from the notes
4. Export the presentation as a downloadable PDF

## Output
- Study notes
- Presentation slides
- PDF export

## Rules
- Presentation should have 8-12 slides
- Include visual elements
""",
        "variables": {"topic": "Neural Networks", "user_input": "Neural Networks"},
        "expected_tools": ["rag", "llm", "python_auto", "python_auto"],
    },
    {
        "id": 9,
        "title": "Dynamic Report Generator",
        "markdown": """# Skill: Dynamic Report Generator

## Input
topic: {user_input}
format: {format}

## Steps
1. Search the web for current information about {topic}
2. Search uploaded documents for additional context about {topic}
3. Synthesize findings into a {format} report with clear sections
4. Generate an executive summary with key takeaways

## Output
- Full report in requested format
- Executive summary

## Rules
- Adapt tone to match {format} style
- Include data-backed conclusions
- Highlight actionable insights
""",
        "variables": {"topic": "Electric Vehicle Market", "format": "executive briefing", "user_input": "Electric Vehicle Market"},
        "expected_tools": ["web_search", "rag", "llm", "llm"],
    },
    {
        "id": 10,
        "title": "Python Game Creator",
        "markdown": """# Skill: Python Game Creator

## Input
game_type: {user_input}

## Steps
1. Search the web for examples and tutorials about {game_type} in Python
2. Generate Python code for the complete game with comments
3. Execute the code to validate it compiles and runs correctly
4. Export the final game script as a downloadable .py file

## Output
- Working Python game file
- Code documentation

## Rules
- Use standard library only (no external deps)
- Include a game loop
- Add clear instructions for the player
""",
        "variables": {"game_type": "text-based adventure", "user_input": "text-based adventure"},
        "expected_tools": ["web_search", "python_auto", "python_auto", "python_auto"],
    },
]


# ═══════════════════════════════════════════════════════════
#  LAYER 1 — Markdown Parser Tests
# ═══════════════════════════════════════════════════════════

@_run_test("L1.1 — parse all 10 test-case skills")
async def test_parse_all_skills():
    from app.services.skills.markdown_parser import parse_skill_markdown

    results = []
    for skill in TEST_SKILLS:
        defn = parse_skill_markdown(skill["markdown"])
        info = {
            "id": skill["id"],
            "title": defn.title,
            "inputs_count": len(defn.inputs),
            "steps_count": len(defn.steps),
            "outputs_count": len(defn.outputs),
            "rules_count": len(defn.rules),
            "variables": defn.all_variables,
            "step_details": [
                {
                    "index": s.index,
                    "instruction": s.instruction[:80],
                    "tool_hint": s.tool_hint,
                    "variables_used": s.variables_used,
                    "condition": s.condition,
                }
                for s in defn.steps
            ],
        }
        results.append(info)

        assert defn.title == skill["title"], f"Title mismatch: got '{defn.title}', expected '{skill['title']}'"
        assert len(defn.steps) > 0, f"Skill {skill['id']} has no steps"

    return results


@_run_test("L1.2 — validate_skill_markdown (valid)")
async def test_validate_valid():
    from app.services.skills.markdown_parser import validate_skill_markdown

    for skill in TEST_SKILLS:
        is_valid, error = validate_skill_markdown(skill["markdown"])
        assert is_valid, f"Skill {skill['id']} validation failed: {error}"
    return "All 10 skills validated successfully"


@_run_test("L1.3 — validate_skill_markdown (invalid inputs)")
async def test_validate_invalid():
    from app.services.skills.markdown_parser import validate_skill_markdown

    bad_inputs = [
        ("", "empty string"),
        ("Hello world", "no sections"),
        ("# Skill: Test\n## Input\nfoo: bar\n", "no steps section"),
        ("# Skill: Test\n## Steps\n  - no numbered steps", "non-numbered steps"),
    ]
    results = []
    for md, label in bad_inputs:
        is_valid, error = validate_skill_markdown(md)
        results.append({"label": label, "valid": is_valid, "error": error})
        assert not is_valid, f"Expected invalid for '{label}', but was valid"
    return results


@_run_test("L1.4 — variable extraction depth")
async def test_variable_extraction():
    from app.services.skills.markdown_parser import parse_skill_markdown

    md = """# Skill: Multi-Variable
## Input
name: {user_input}
depth: {depth_level}
format: {output_format}
## Steps
1. Search documents for {name} at {depth_level} depth
2. Export result in {output_format} with {name} header
## Output
- Report
"""
    defn = parse_skill_markdown(md)
    expected_vars = {"user_input", "depth_level", "output_format", "name"}
    actual_vars = set(defn.all_variables)
    assert expected_vars == actual_vars, f"Variable mismatch: expected {expected_vars}, got {actual_vars}"
    return {"variables": defn.all_variables, "inputs": [v.name for v in defn.inputs]}


@_run_test("L1.5 — skill_to_json round-trip")
async def test_skill_to_json():
    from app.services.skills.markdown_parser import parse_skill_markdown, skill_to_json

    defn = parse_skill_markdown(TEST_SKILLS[0]["markdown"])
    j = skill_to_json(defn)
    assert j["title"] == defn.title
    assert len(j["steps"]) == len(defn.steps)
    assert isinstance(j["inputs"], list)
    assert isinstance(j["all_variables"], list)
    return j


@_run_test("L1.6 — conditional step parsing")
async def test_conditional_steps():
    from app.services.skills.markdown_parser import parse_skill_markdown

    defn = parse_skill_markdown(TEST_SKILLS[6]["markdown"])  # Conditional Analysis
    # Check IF conditions are detected in instruction text
    conditions_found = [s for s in defn.steps if s.condition or "IF" in s.instruction.upper()]
    return {
        "steps": [{"index": s.index, "instruction": s.instruction, "condition": s.condition} for s in defn.steps],
        "conditions_found": len(conditions_found),
    }


# ═══════════════════════════════════════════════════════════
#  LAYER 2 — Tool Mapper Tests
# ═══════════════════════════════════════════════════════════

@_run_test("L2.1 — tool mapping for all 10 skills (with materials)")
async def test_tool_mapping_with_materials():
    from app.services.skills.markdown_parser import parse_skill_markdown
    from app.services.skills.tool_mapper import map_steps_to_tools

    results = []
    for skill in TEST_SKILLS:
        defn = parse_skill_markdown(skill["markdown"])
        steps = [
            {
                "index": s.index,
                "instruction": s.instruction,
                "tool_hint": s.tool_hint,
            }
            for s in defn.steps
        ]
        mapped = map_steps_to_tools(steps, has_materials=True)
        tools = [s["tool"] for s in mapped]
        results.append({
            "id": skill["id"],
            "title": skill["title"],
            "mapped_tools": tools,
            "expected_tools": skill["expected_tools"],
            "match": tools == skill["expected_tools"],
        })
    return results


@_run_test("L2.2 — tool mapping (no materials — RAG fallback)")
async def test_tool_mapping_no_materials():
    from app.services.skills.tool_mapper import map_step_to_tool

    # RAG keyword should fallback to web_search when no materials
    tool = map_step_to_tool("Search uploaded documents for topic", has_materials=False)
    assert tool == "web_search", f"Expected web_search, got {tool}"

    # Explicit tool_hint=rag should also fallback
    tool2 = map_step_to_tool("Find info", tool_hint="rag", has_materials=False)
    assert tool2 == "web_search", f"Expected web_search, got {tool2}"

    # web_search stays web_search
    tool3 = map_step_to_tool("Search the web for info", has_materials=False)
    assert tool3 == "web_search", f"Expected web_search, got {tool3}"

    return {"rag_fallback": "web_search", "explicit_rag_fallback": "web_search", "web_stable": "web_search"}


@_run_test("L2.3 — tool mapping keyword coverage")
async def test_tool_keyword_coverage():
    from app.services.skills.tool_mapper import map_step_to_tool

    cases = [
        ("Search uploaded documents for AI papers", "rag"),
        ("Search the web for latest news", "web_search"),
        ("Find online resources about Python", "web_search"),
        ("Generate Python code to create a bar chart", "python_auto"),
        ("Compute statistics using pandas", "python_auto"),
        ("Create a scatter plot from the data", "python_auto"),
        ("Summarize the findings", "llm"),
        ("Synthesize all research into a report", "llm"),
        ("Research the topic comprehensively", "research"),
        ("Explain the concept in simple terms", "llm"),
        ("Export the results as a CSV file", "python_auto"),
        ("Just do something vague", "llm"),  # default
    ]
    results = []
    for instruction, expected in cases:
        actual = map_step_to_tool(instruction, has_materials=True)
        results.append({
            "instruction": instruction[:60],
            "expected": expected,
            "actual": actual,
            "match": actual == expected,
        })
        assert actual == expected, f"Mismatch for '{instruction[:40]}': expected {expected}, got {actual}"
    return results


# ═══════════════════════════════════════════════════════════
#  LAYER 3 — Skill Compiler Tests
# ═══════════════════════════════════════════════════════════

@_run_test("L3.1 — variable substitution in compiler")
async def test_variable_substitution():
    from app.services.skills.markdown_parser import parse_skill_markdown
    from app.services.skills.skill_compiler import compile_skill

    defn = parse_skill_markdown(TEST_SKILLS[0]["markdown"])
    variables = {"topic": "Quantum Computing", "user_input": "Quantum Computing"}

    plan = await compile_skill(defn, variables, has_materials=True)

    assert len(plan) > 0, "Compiled plan is empty"

    # Every step should have tool assigned
    for step in plan:
        assert "tool" in step, f"Step {step.get('index')} missing 'tool' key"
        assert step["tool"] in ("rag", "web_search", "research", "python_auto", "llm"), \
            f"Invalid tool '{step['tool']}' in step {step.get('index')}"

    # Check variable substitution happened
    instructions = " ".join(s.get("instruction", "") + " " + s.get("query", "") for s in plan)
    assert "Quantum Computing" in instructions or "{topic}" not in instructions, \
        "Variable {topic} was not substituted"

    return {"plan_length": len(plan), "steps": plan}


@_run_test("L3.2 — compiler fallback (direct tool mapping)")
async def test_compiler_fallback():
    """Ensure the fallback path works when LLM compilation isn't available."""
    from app.services.skills.markdown_parser import parse_skill_markdown
    from app.services.skills.tool_mapper import map_steps_to_tools

    # Directly test the fallback path
    defn = parse_skill_markdown(TEST_SKILLS[5]["markdown"])  # Research Report
    variables = {"topic": "AI Safety", "user_input": "AI Safety"}

    # Simulate fallback: substitute variables + map tools directly
    substituted_steps = []
    for step in defn.steps:
        instruction = step.instruction
        for var_name, var_value in variables.items():
            instruction = instruction.replace(f"{{{var_name}}}", str(var_value))
        substituted_steps.append({
            "index": step.index,
            "instruction": instruction,
            "tool_hint": step.tool_hint,
        })

    mapped = map_steps_to_tools(substituted_steps, has_materials=True)
    assert len(mapped) == len(defn.steps), "Fallback mapping should preserve step count"

    for step in mapped:
        assert "tool" in step, f"Fallback step {step['index']} missing tool"

    return {"fallback_steps": mapped}


# ═══════════════════════════════════════════════════════════
#  LAYER 4 — Executor SSE Format Tests
# ═══════════════════════════════════════════════════════════

@_run_test("L4.1 — SSE event format validation")
async def test_sse_format():
    from app.services.skills.skill_executor import _sse

    event = _sse("skill_status", {"status": "running", "total_steps": 3})
    assert event.startswith("event: skill_status"), f"Bad event prefix: {event[:30]}"
    assert "data: " in event, "Missing data: prefix"
    assert event.endswith("\n\n"), "SSE must end with double newline"

    # Parse the data back
    data_line = event.split("data: ", 1)[1].split("\n")[0]
    parsed = json.loads(data_line)
    assert parsed["status"] == "running"
    assert parsed["total_steps"] == 3

    return {"event_sample": event[:100]}


@_run_test("L4.2 — SSE event types coverage")
async def test_sse_event_types():
    from app.services.skills.skill_executor import _sse

    event_types = [
        ("skill_status", {"status": "running"}),
        ("skill_step_start", {"step_index": 1, "tool": "rag"}),
        ("skill_step_result", {"step_index": 1, "content": "test"}),
        ("skill_step_error", {"step_index": 1, "error": "oops"}),
        ("skill_artifact", {"filename": "report.pdf"}),
        ("skill_done", {"status": "completed"}),
    ]

    results = []
    for evt_type, data in event_types:
        sse = _sse(evt_type, data)
        assert f"event: {evt_type}" in sse
        parsed_data = json.loads(sse.split("data: ", 1)[1].split("\n")[0])
        results.append({"event": evt_type, "parsed_ok": True})
    return results


@_run_test("L4.3 — conditional execution runtime")
async def test_conditional_execution_runtime():
    from app.services.skills import skill_executor as executor

    original_llm_step = executor._execute_llm_step

    async def fake_llm_step(query, context="", rules=None):
        if "check dataset" in query.lower():
            return "No dataset found in uploaded materials.", []
        return f"handled: {query}", []

    executor._execute_llm_step = fake_llm_step

    plan = [
        {
            "index": 1,
            "instruction": "Check dataset",
            "tool": "llm",
            "query": "check dataset availability",
        },
        {
            "index": 2,
            "instruction": "Run analysis branch",
            "tool": "llm",
            "condition": "dataset found",
            "query": "run dataset analysis",
        },
        {
            "index": 3,
            "instruction": "Run summary branch",
            "tool": "llm",
            "condition": "no dataset",
            "query": "summarize documents",
        },
    ]

    starts: List[int] = []
    skipped: List[int] = []
    completed: List[int] = []

    try:
        async for evt in executor.execute_skill(
            plan=plan,
            user_id="test-user",
            notebook_id="test-notebook",
            session_id="test-session",
            material_ids=[],
            variables={"dataset_found": "false"},
            rules=[],
        ):
            if not evt.startswith("event: "):
                continue
            event_name = evt.split("\n", 1)[0].replace("event: ", "").strip()
            payload = json.loads(evt.split("data: ", 1)[1].split("\n", 1)[0])
            if event_name == "skill_step_start":
                starts.append(payload.get("step_index"))
            elif event_name == "skill_step_skipped":
                skipped.append(payload.get("step_index"))
            elif event_name == "skill_step_result":
                completed.append(payload.get("step_index"))
    finally:
        executor._execute_llm_step = original_llm_step

    assert 1 in starts, "Step 1 should start"
    assert 2 in skipped, "Step 2 should be skipped (dataset found condition false)"
    assert 3 in completed, "Step 3 should execute (no dataset condition true)"
    assert 2 not in completed, "Step 2 must not execute when skipped"

    return {
        "step_starts": starts,
        "step_skipped": skipped,
        "step_completed": completed,
    }


# ═══════════════════════════════════════════════════════════
#  LAYER 5 — Skill Service CRUD Tests (via Prisma)
# ═══════════════════════════════════════════════════════════

@_run_test("L5.1 — slugify helper")
async def test_slugify():
    # Import the private helper
    from app.services.skills.skill_service import _slugify

    cases = [
        ("Research Summary", "research-summary"),
        ("Data Analysis Pipeline", "data-analysis-pipeline"),
        ("Hello World!!! @#$%", "hello-world"),
        ("  spaces  and  tabs  ", "spaces-and-tabs"),
        ("Already-Slugged", "already-slugged"),
        ("", "untitled"),
    ]
    results = []
    for title, expected in cases:
        actual = _slugify(title)
        results.append({"title": title, "expected": expected, "actual": actual, "match": actual == expected})
        assert actual == expected, f"Slugify '{title}': expected '{expected}', got '{actual}'"
    return results


@_run_test("L5.2 — built-in templates loading")
async def test_templates():
    from app.services.skills.skill_service import get_templates

    templates = await get_templates()
    assert len(templates) == 14, f"Expected 14 templates, got {len(templates)}"

    for tmpl in templates:
        assert "slug" in tmpl, f"Template missing slug"
        assert "title" in tmpl, f"Template missing title"
        assert "markdown" in tmpl, f"Template missing markdown"
        assert tmpl["steps_count"] > 0, f"Template {tmpl['slug']} has 0 steps"

    return [{"slug": t["slug"], "title": t["title"], "steps": t["steps_count"]} for t in templates]


@_run_test("L5.3 — CRUD: create, read, update, delete skill via Prisma")
async def test_crud_lifecycle():
    from app.db.prisma_client import prisma, connect_db, disconnect_db

    if not prisma.is_connected():
        await connect_db()

    from app.services.skills.skill_service import create_skill, get_skill, update_skill, delete_skill

    # Fetch a real user
    user = await prisma.user.find_first()
    assert user, "No user found in database — cannot test CRUD"
    user_id = user.id

    markdown = TEST_SKILLS[0]["markdown"]

    # CREATE
    skill = await create_skill(user_id=user_id, markdown=markdown, is_global=True, tags=["test", "pipeline"])
    assert skill["id"], "Created skill has no ID"
    assert skill["title"] == "Study Pack Generator"
    assert skill["is_global"] is True
    assert "test" in skill["tags"]
    skill_id = skill["id"]

    # READ
    fetched = await get_skill(skill_id, user_id)
    assert fetched is not None, "Failed to read created skill"
    assert fetched["title"] == skill["title"]
    assert fetched["parsed"] is not None, "Parsed info should be populated"
    assert fetched["parsed"]["steps_count"] > 0

    # UPDATE
    updated_md = markdown.replace("Study Pack Generator", "Enhanced Study Pack Generator")
    updated = await update_skill(skill_id, user_id, markdown=updated_md, tags=["test", "updated"])
    assert updated["title"] == "Enhanced Study Pack Generator"
    assert updated["version"] == 2
    assert "updated" in updated["tags"]

    # DELETE
    deleted = await delete_skill(skill_id, user_id)
    assert deleted is True, "Delete returned False"

    # Verify deletion
    gone = await get_skill(skill_id, user_id)
    assert gone is None, "Skill should be None after deletion"

    return {
        "created_id": skill_id,
        "created_title": skill["title"],
        "updated_title": updated["title"],
        "deleted": True,
    }


# ═══════════════════════════════════════════════════════════
#  LAYER 6 — Full Compile Pipeline for All 10 Skills
# ═══════════════════════════════════════════════════════════

@_run_test("L6.1 — compile all 10 test-case skills")
async def test_compile_all_skills():
    from app.services.skills.markdown_parser import parse_skill_markdown
    from app.services.skills.skill_compiler import compile_skill

    results = []
    for skill in TEST_SKILLS:
        defn = parse_skill_markdown(skill["markdown"])
        plan = await compile_skill(defn, skill["variables"], has_materials=True)

        assert len(plan) > 0, f"Skill {skill['id']} compiled to empty plan"

        # Every step must have required fields
        for step in plan:
            assert "index" in step, f"Skill {skill['id']} step missing index"
            assert "instruction" in step, f"Skill {skill['id']} step missing instruction"
            assert "tool" in step, f"Skill {skill['id']} step missing tool"
            assert step["tool"] in ("rag", "web_search", "research", "python_auto", "llm"), \
                f"Skill {skill['id']} step has invalid tool: {step['tool']}"

        tools = [s["tool"] for s in plan]
        results.append({
            "id": skill["id"],
            "title": skill["title"],
            "steps_compiled": len(plan),
            "tools": tools,
        })

    return results


# ═══════════════════════════════════════════════════════════
#  LAYER 7 — End-to-End CRUD + Execute Test
# ═══════════════════════════════════════════════════════════

@_run_test("L7.1 — E2E: create skill, compile, execute one step via LLM")
async def test_e2e_single_skill():
    from app.db.prisma_client import prisma, connect_db
    if not prisma.is_connected():
        await connect_db()

    from app.services.skills.skill_service import create_skill, run_skill, delete_skill

    user = await prisma.user.find_first()
    assert user, "No user in DB"
    user_id = user.id

    # Use skill #9 (Dynamic Report) — it has a web search + llm pattern
    # For isolated testing, create a simple LLM-only skill
    simple_md = """# Skill: Quick Summary Test

## Input
topic: {user_input}

## Steps
1. Summarize the key concepts of {topic} in 3 bullet points

## Output
- Summary bullet points

## Rules
- Keep it under 100 words
"""

    skill = await create_skill(user_id=user_id, markdown=simple_md, is_global=True, tags=["e2e-test"])
    skill_id = skill["id"]

    events_collected: List[str] = []
    try:
        async for event in run_skill(
            skill_id=skill_id,
            user_id=user_id,
            variables={"topic": "Artificial Intelligence", "user_input": "Artificial Intelligence"},
        ):
            events_collected.append(event)
    except Exception as exc:
        # Still check partial events
        events_collected.append(f"ERROR: {exc}")

    # Parse events
    event_types = []
    for evt in events_collected:
        if evt.startswith("event: "):
            evt_type = evt.split("\n")[0].replace("event: ", "").strip()
            event_types.append(evt_type)

    # Cleanup
    await delete_skill(skill_id, user_id)

    return {
        "skill_id": skill_id,
        "events_count": len(events_collected),
        "event_types": event_types,
        "has_status": "skill_status" in event_types,
        "has_done": "skill_done" in event_types,
    }


@_run_test("L7.2 — route handler import validation")
async def test_route_imports():
    from app.routes.skills import router

    paths = [r.path for r in router.routes if hasattr(r, "path")]
    methods_map: Dict[str, set] = {}
    for r in router.routes:
        if hasattr(r, "methods") and hasattr(r, "path"):
            methods_map.setdefault(r.path, set()).update(set(r.methods or []))

    expected_methods = {
        "/skills": {"GET", "POST"},
        "/skills/templates": {"GET"},
        "/skills/validate": {"POST"},
        "/skills/runs": {"GET"},
        "/skills/runs/{run_id}": {"GET"},
        "/skills/{skill_id}": {"GET", "PUT", "DELETE"},
        "/skills/{skill_id}/run": {"POST"},
    }

    for path, required_methods in expected_methods.items():
        assert path in paths, f"Missing route path: {path}"
        actual_methods = methods_map.get(path, set())
        missing = required_methods - actual_methods
        assert not missing, f"Route {path} missing methods: {sorted(missing)}"

    return {
        "registered_paths": {k: sorted(list(v)) for k, v in methods_map.items()},
        "expected_found": len(expected_methods),
    }


@_run_test("L7.3 — chat routing: /skills command detection")
async def test_chat_routing():
    from app.services.chat_v2.router_logic import route_capability
    from app.services.chat_v2.schemas import Capability

    # Test /skills command detection
    cap = route_capability("/skills research-summary topic=AI", material_ids=[], intent_override=None)
    assert cap == Capability.SKILL_EXECUTION, f"Expected SKILL_EXECUTION, got {cap}"

    # Ensure normal messages don't trigger skills
    cap2 = route_capability("What is machine learning?", material_ids=[], intent_override=None)
    assert cap2 != Capability.SKILL_EXECUTION, f"Normal message routed to skills"

    return {"skills_command": str(cap), "normal_message": str(cap2)}


@_run_test("L7.4 — failed skill emits terminal event")
async def test_failed_skill_terminal_event():
    from app.db.prisma_client import prisma, connect_db
    from app.services.skills.skill_service import run_skill

    if not prisma.is_connected():
        await connect_db()

    user = await prisma.user.find_first()
    assert user, "No user found in database"

    missing_skill_id = "00000000-0000-0000-0000-000000000000"
    event_types = []
    done_payload = None

    async for event in run_skill(skill_id=missing_skill_id, user_id=user.id):
        if event.startswith("event: "):
            evt_name = event.split("\n", 1)[0].replace("event: ", "").strip()
            event_types.append(evt_name)
            if evt_name == "skill_done":
                done_payload = json.loads(event.split("data: ", 1)[1].split("\n", 1)[0])

    assert "skill_status" in event_types, "Expected failure status event"
    assert "skill_done" in event_types, "Expected terminal skill_done event"
    assert done_payload and done_payload.get("status") == "failed", "Expected failed terminal payload"

    return {"event_types": event_types, "done": done_payload}


# ═══════════════════════════════════════════════════════════
#  RUNNER
# ═══════════════════════════════════════════════════════════

async def main():
    logger.info("=" * 70)
    logger.info("  AGENT SKILLS PIPELINE — FULL TEST SUITE")
    logger.info("  %s", datetime.now().isoformat())
    logger.info("=" * 70)

    # Connect to database
    from app.db.prisma_client import connect_db, disconnect_db, prisma
    try:
        await connect_db()
        logger.info("Database connected")
    except Exception as e:
        logger.error("Database connection failed: %s", e)
        logger.info("CRUD / E2E tests will be skipped")

    # Layer 1: Parser
    logger.info("\n── LAYER 1: Markdown Parser ───────────────")
    await test_parse_all_skills()
    await test_validate_valid()
    await test_validate_invalid()
    await test_variable_extraction()
    await test_skill_to_json()
    await test_conditional_steps()

    # Layer 2: Tool Mapper
    logger.info("\n── LAYER 2: Tool Mapper ───────────────────")
    await test_tool_mapping_with_materials()
    await test_tool_mapping_no_materials()
    await test_tool_keyword_coverage()

    # Layer 3: Compiler
    logger.info("\n── LAYER 3: Skill Compiler ────────────────")
    await test_variable_substitution()
    await test_compiler_fallback()

    # Layer 4: Executor SSE
    logger.info("\n── LAYER 4: Executor SSE Format ───────────")
    await test_sse_format()
    await test_sse_event_types()
    await test_conditional_execution_runtime()

    # Layer 5: CRUD
    logger.info("\n── LAYER 5: Skill Service CRUD ────────────")
    await test_slugify()
    await test_templates()
    if prisma.is_connected():
        await test_crud_lifecycle()
    else:
        logger.warning("SKIP L5.3 — no DB connection")

    # Layer 6: Full compilation
    logger.info("\n── LAYER 6: Full Compilation Pipeline ─────")
    await test_compile_all_skills()

    # Layer 7: E2E
    logger.info("\n── LAYER 7: End-to-End ────────────────────")
    if prisma.is_connected():
        await test_e2e_single_skill()
    else:
        logger.warning("SKIP L7.1 — no DB connection")
    await test_route_imports()
    await test_chat_routing()
    if prisma.is_connected():
        await test_failed_skill_terminal_event()
    else:
        logger.warning("SKIP L7.4 — no DB connection")

    # ── Summary ────────────────────────────────────────────
    passed = sum(1 for r in ALL_RESULTS if r.passed)
    failed = sum(1 for r in ALL_RESULTS if not r.passed)
    total = len(ALL_RESULTS)

    logger.info("\n" + "=" * 70)
    logger.info("  RESULTS: %d/%d passed, %d failed", passed, total, failed)
    logger.info("=" * 70)

    for r in ALL_RESULTS:
        status = "✅ PASS" if r.passed else "❌ FAIL"
        logger.info("  %s  %s  (%.2fs)", status, r.name, r.elapsed)
        if r.error:
            for line in r.error.strip().split("\n")[:5]:
                logger.info("         %s", line)

    # ── Save outputs ───────────────────────────────────────
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total": total,
        "passed": passed,
        "failed": failed,
        "results": [r.to_dict() for r in ALL_RESULTS],
    }

    summary_file = OUTPUT_DIR / "test_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    logger.info("Summary saved to %s", summary_file)

    # Save detailed results per layer
    for r in ALL_RESULTS:
        safe_name = re.sub(r"[^a-zA-Z0-9_.-]", "_", r.name)
        detail_file = OUTPUT_DIR / f"{safe_name}.json"
        with open(detail_file, "w") as f:
            json.dump(r.to_dict(), f, indent=2, default=str)

    # Disconnect
    try:
        await disconnect_db()
    except Exception:
        pass

    if failed > 0:
        logger.error("\n⚠  %d test(s) FAILED — see details above", failed)
        sys.exit(1)
    else:
        logger.info("\n🎉  All %d tests PASSED", passed)
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
