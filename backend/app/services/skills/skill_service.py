"""
Skill Service — CRUD operations and run orchestration for Agent Skills.

Coordinates:  parse → resolve → compile → execute → persist results
"""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional, Set, Tuple

from prisma import Json

from app.db.prisma_client import prisma
from app.services.llm_service.llm import extract_chunk_content, get_llm
from app.services.llm_service.structured_invoker import parse_json_robust
from app.services.skills.markdown_parser import (
    MarkdownParseError,
    parse_skill_markdown,
    skill_to_json,
    validate_skill_markdown,
)
from app.services.skills.skill_compiler import compile_skill
from app.services.skills.skill_executor import execute_skill, _sse
from app.services.skills.skill_resolver import resolve_skill, resolve_skill_by_id
from app.services.skills.tool_mapper import map_steps_to_tools

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────

def _slugify(title: str) -> str:
    """Convert a title to a URL-safe slug."""
    slug = re.sub(r"[^\w\s-]", "", title.lower().strip())
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:100] or "untitled"


def _to_json_compatible(value: Any) -> Any:
    """Convert arbitrary data into JSON-compatible Python types."""
    try:
        converted = json.loads(json.dumps(value, default=str))
    except Exception:
        return {"value": str(value)}

    if isinstance(converted, (dict, list, str, int, float, bool)) or converted is None:
        return converted
    return {"value": str(converted)}


def _coerce_json_field(value: Any, default: Any) -> Any:
    """Parse Prisma Json fields that may be dict/list already or JSON strings."""
    if value is None:
        return default
    if isinstance(value, (dict, list, int, float, bool)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return default
    return default


def _parse_sse_event(event_str: str) -> Tuple[Optional[str], Optional[Any]]:
    """Extract (event_name, parsed_data) from a single SSE frame."""
    if not event_str:
        return None, None

    event_name: Optional[str] = None
    data_text: Optional[str] = None
    for line in event_str.splitlines():
        if line.startswith("event: "):
            event_name = line[len("event: "):].strip()
        elif line.startswith("data: "):
            data_text = line[len("data: "):].strip()

    if data_text is None:
        return event_name, None

    try:
        return event_name, json.loads(data_text)
    except Exception:
        return event_name, data_text


def _validate_variables_defined(definition) -> None:
    """Ensure every {variable} used in markdown is declared in ## Input or reserved."""
    declared = {inp.name for inp in definition.inputs}
    declared.add("user_input")
    undefined = sorted(v for v in definition.all_variables if v not in declared)
    if undefined:
        raise ValueError(
            "Undefined variables in skill markdown: "
            + ", ".join(undefined)
            + ". Define them in the ## Input section."
        )


def _derive_persisted_status(executor_status: Optional[str], step_logs: List[Dict[str, Any]]) -> str:
    """Map executor status and step logs to DB enum values (completed|failed)."""
    if (executor_status or "").lower() in {"failed", "completed_with_errors"}:
        return "failed"

    for log in step_logs:
        if isinstance(log, dict) and log.get("success") is False:
            return "failed"

    return "completed"


def _strip_markdown_fences(text: str) -> str:
    """Remove optional markdown fences if model wraps output in code blocks."""
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _normalize_tag(tag: str) -> Optional[str]:
    """Normalize a free-form label into a compact, URL-safe tag."""
    cleaned = re.sub(r"[^a-z0-9\s-]", "", (tag or "").lower()).strip()
    cleaned = re.sub(r"\s+", "-", cleaned)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    if len(cleaned) < 2:
        return None
    return cleaned[:24]


def _fallback_skill_tags(definition: Optional[Any], max_tags: int = 6) -> List[str]:
    """Derive stable fallback tags without relying on model output."""
    stopwords: Set[str] = {
        "about", "from", "with", "into", "that", "this", "your", "the",
        "and", "for", "are", "using", "then", "step", "steps", "output",
        "rules", "summary", "report", "generate", "create", "analyze",
    }
    tags: List[str] = []
    seen: Set[str] = set()

    def _push(candidate: str) -> None:
        normalized = _normalize_tag(candidate)
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        tags.append(normalized)

    if definition:
        for word in re.findall(r"[A-Za-z][A-Za-z0-9]{2,}", definition.title or ""):
            if word.lower() not in stopwords:
                _push(word)
            if len(tags) >= max_tags:
                return tags

        for step in getattr(definition, "steps", []) or []:
            if getattr(step, "tool_hint", None):
                _push(step.tool_hint.replace("_", "-"))
            if len(tags) >= max_tags:
                return tags

        text_pool = " ".join([
            definition.description or "",
            *getattr(definition, "outputs", []),
            *getattr(definition, "rules", []),
        ])
        for word in re.findall(r"[A-Za-z][A-Za-z0-9]{3,}", text_pool):
            if word.lower() in stopwords:
                continue
            _push(word)
            if len(tags) >= max_tags:
                return tags

    if not tags:
        tags = ["workflow", "automation", "assistant"]
    return tags[:max_tags]


async def suggest_skill_tags(markdown: str, max_tags: int = 6) -> List[str]:
    """Suggest concise skill tags from markdown using LLM + deterministic fallback."""
    max_tags = max(3, min(max_tags, 10))

    definition = None
    try:
        definition = parse_skill_markdown(markdown)
    except Exception:
        definition = None

    fallback = _fallback_skill_tags(definition, max_tags=max_tags)

    if definition:
        summary_block = (
            f"Title: {definition.title}\n"
            f"Description: {definition.description or ''}\n"
            f"Inputs: {', '.join(v.name for v in definition.inputs) or 'none'}\n"
            f"Steps: {' | '.join(s.instruction for s in definition.steps[:6])}\n"
            f"Outputs: {' | '.join(definition.outputs[:4]) or 'none'}\n"
        )
    else:
        summary_block = f"Markdown:\n{markdown[:3000]}"

    prompt = (
        "Generate short tags for an AI workflow skill.\n"
        "Requirements:\n"
        "- Return strictly JSON.\n"
        "- Output shape: {\"tags\": [\"tag1\", \"tag2\"]}.\n"
        f"- Return {max_tags} tags maximum.\n"
        "- Tags should be lowercase, specific, and reusable.\n"
        "- Avoid duplicates, generic filler, and long phrases.\n\n"
        f"Skill details:\n{summary_block}"
    )

    try:
        llm = get_llm(mode="structured", temperature=0.15, max_tokens=220)
        response = await llm.ainvoke(prompt)
        raw = extract_chunk_content(response)
        parsed = parse_json_robust(raw)

        candidates = []
        if isinstance(parsed, dict):
            tags_data = parsed.get("tags")
            if isinstance(tags_data, list):
                candidates = tags_data
        elif isinstance(parsed, list):
            candidates = parsed

        normalized: List[str] = []
        seen: Set[str] = set()
        for item in candidates:
            tag = _normalize_tag(str(item))
            if not tag or tag in seen:
                continue
            seen.add(tag)
            normalized.append(tag)
            if len(normalized) >= max_tags:
                break

        if normalized:
            return normalized
    except Exception as exc:
        logger.warning("Tag suggestion failed; using fallback tags: %s", exc)

    return fallback[:max_tags]


async def generate_skill_draft(
    user_prompt: str,
) -> Dict[str, Any]:
    """Generate a valid skill markdown draft from a natural-language prompt."""
    prompt = (user_prompt or "").strip()
    if len(prompt) < 6:
        raise ValueError("Please provide a clearer prompt to generate a skill")

    generation_prompt = (
        "You are an expert workflow designer for AI skills. "
        "Generate a complete markdown skill definition.\n\n"
        "Strict format:\n"
        "# Skill: <concise title>\n"
        "## Input\n"
        "<name>: {user_input}\n"
        "## Steps\n"
        "1. ...\n"
        "2. ...\n"
        "## Output\n"
        "- ...\n"
        "## Rules\n"
        "- ...\n\n"
        "Constraints:\n"
        "- Decide the most appropriate number of steps for the user's goal\n"
        "- Keep the workflow concise and practical\n"
        "- Prefer practical, execution-ready steps\n"
        "- Include meaningful variable names in Input\n"
        "- Ensure all {variables} used in steps are declared in Input\n"
        "- Do not add explanations outside markdown\n\n"
        f"User intent:\n{prompt}"
    )

    llm = get_llm(mode="creative", temperature=0.25, max_tokens=1200)
    response = await llm.ainvoke(generation_prompt)
    generated = _strip_markdown_fences(extract_chunk_content(response))

    definition = None
    try:
        definition = parse_skill_markdown(generated)
        _validate_variables_defined(definition)
    except Exception:
        # Deterministic fallback to guarantee usable output even when model drifts.
        title = f"{prompt[:48].strip().rstrip('.')} Skill".strip()
        safe_title = re.sub(r"\s+", " ", title)
        generated = (
            f"# Skill: {safe_title}\n\n"
            "## Input\n"
            "topic: {user_input}\n\n"
            "## Steps\n"
            "1. Search uploaded documents for information about {topic}\n"
            "2. If needed, search the web for recent updates about {topic}\n"
            "3. Synthesize findings into a structured response with actionable points\n"
            "4. Generate a concise final summary\n\n"
            "## Output\n"
            "- Structured summary\n"
            "- Key takeaways\n"
            "- Source references\n\n"
            "## Rules\n"
            "- Be accurate and concise\n"
            "- Highlight uncertainty when evidence is weak\n"
        )
        definition = parse_skill_markdown(generated)
        _validate_variables_defined(definition)

    tags = await suggest_skill_tags(generated, max_tags=6)
    return {
        "markdown": generated,
        "parsed": skill_to_json(definition),
        "tags": tags,
    }


# ── Built-in Skill Templates ──────────────────────────────

BUILT_IN_TEMPLATES = [
    {
        "slug": "research-summary",
        "title": "Research Summary",
        "description": "Search documents and web for a topic, then synthesize a structured summary",
        "tags": ["research", "summary", "rag"],
        "markdown": """# Skill: Research Summary

## Input
topic: {user_input}

## Steps
1. Search uploaded documents for information about {topic}
2. Search the web for recent developments about {topic}
3. Synthesize findings into a structured summary with key points, organized by theme
4. Generate a concise executive summary with bullet points

## Output
- Structured research summary with sections
- Key findings list
- Source citations

## Rules
- Use academic tone
- Include at least 5 key findings
- Cite all sources
""",
    },
    {
        "slug": "data-analysis",
        "title": "Data Analysis Pipeline",
        "description": "Analyze uploaded data files with statistics, visualizations, and insights",
        "tags": ["data", "analysis", "python", "charts"],
        "markdown": """# Skill: Data Analysis Pipeline

## Input
objective: {user_input}

## Steps
1. Search uploaded documents to understand the dataset structure and columns
2. Generate Python code to load the data and compute descriptive statistics
3. Create visualizations (bar charts, histograms, scatter plots) relevant to {objective}
4. Summarize the key insights and patterns found

## Output
- Statistical summary
- Charts and visualizations
- Key insights report

## Rules
- Use pandas and matplotlib/seaborn
- Always include data quality checks
- Generate at least 3 visualizations
""",
    },
    {
        "slug": "web-research-report",
        "title": "Web Research Report",
        "description": "Comprehensive web research with multi-source analysis and structured report",
        "tags": ["web", "research", "report"],
        "markdown": """# Skill: Web Research Report

## Input
question: {user_input}

## Steps
1. Search the web for authoritative information about {question}
2. Research the topic comprehensively across multiple sources
3. Synthesize all findings into a structured report with introduction, findings, analysis, and conclusion
4. Generate an executive summary with actionable recommendations

## Output
- Comprehensive research report
- Executive summary
- Source list

## Rules
- Use formal academic tone
- Cross-reference multiple sources
- Flag any conflicting information
- Include publication dates for time-sensitive topics
""",
    },
    {
        "slug": "content-transformer",
        "title": "Content Transformer",
        "description": "Transform and reformat content from uploaded documents",
        "tags": ["transform", "rewrite", "format"],
        "markdown": """# Skill: Content Transformer

## Input
format: {user_input}
style: {style}

## Steps
1. Search uploaded documents to extract the full content
2. Analyze the content structure and key messages
3. Transform the content into {format} format with {style} style
4. Review and polish the transformed output

## Output
- Transformed content in requested format

## Rules
- Preserve all key information from the original
- Adapt tone to match requested style
- Maintain logical flow and coherence
""",
    },
    {
        "slug": "lecture-notes-to-summary",
        "title": "Lecture Notes to Summary",
        "description": "Turn class notes into concise study notes and key takeaways",
        "tags": ["student", "notes", "summary"],
        "markdown": """# Skill: Lecture Notes to Summary

## Input
course_topic: {user_input}

## Steps
1. Search uploaded documents for lecture notes and class material about {course_topic}
2. Extract core concepts, definitions, and examples from the notes
3. Summarize the material into a structured set of study notes
4. Generate a short revision checklist for quick review

## Output
- Structured study notes
- Revision checklist

## Rules
- Keep language clear and student-friendly
- Highlight important formulas or definitions
- Limit final summary to practical exam-focused points
""",
    },
    {
        "slug": "exam-revision-planner",
        "title": "Exam Revision Planner",
        "description": "Create a practical day-by-day revision plan from syllabus content",
        "tags": ["student", "exam", "planning"],
        "markdown": """# Skill: Exam Revision Planner

## Input
exam_name: {user_input}
days_left: {days_left}

## Steps
1. Search uploaded documents for syllabus, topics, and previous notes for {exam_name}
2. Prioritize topics by difficulty and importance
3. Create a day-by-day revision schedule for {days_left} days
4. Generate a final-week high-impact revision checklist

## Output
- Daily revision plan
- Priority topic list
- Final-week checklist

## Rules
- Balance difficult and easy topics each day
- Include one mock-test or practice block regularly
- Keep the plan realistic for daily execution
""",
    },
    {
        "slug": "paper-reading-workflow",
        "title": "Paper Reading Workflow",
        "description": "Read and break down research papers into quick actionable notes",
        "tags": ["research", "papers", "analysis"],
        "markdown": """# Skill: Paper Reading Workflow

## Input
paper_topic: {user_input}

## Steps
1. Search uploaded documents for papers and references about {paper_topic}
2. Extract problem statement, method, dataset, and main results from each paper
3. Compare strengths, limitations, and assumptions across papers
4. Generate a concise reading summary with next papers to read

## Output
- Paper-by-paper summary table
- Comparative analysis
- Next-reading recommendations

## Rules
- Keep summaries evidence-based
- Clearly separate claims vs. observed results
- Mention unresolved questions for future reading
""",
    },
    {
        "slug": "literature-review-drafter",
        "title": "Literature Review Drafter",
        "description": "Draft a structured literature review section with thematic grouping",
        "tags": ["research", "writing", "literature-review"],
        "markdown": """# Skill: Literature Review Drafter

## Input
research_question: {user_input}

## Steps
1. Search uploaded papers and notes relevant to {research_question}
2. Search the web for recent publications and authoritative references
3. Group findings by themes, methods, and outcomes
4. Draft a literature review with gap analysis and transition to proposed work

## Output
- Structured literature review draft
- Research gaps list
- Citation list

## Rules
- Use formal academic tone
- Avoid unsupported claims
- Keep citation placeholders where exact formatting is required
""",
    },
    {
        "slug": "assignment-first-draft",
        "title": "Assignment First Draft",
        "description": "Generate a clear first draft for assignments from notes and references",
        "tags": ["student", "assignment", "writing"],
        "markdown": """# Skill: Assignment First Draft

## Input
assignment_topic: {user_input}
word_limit: {word_limit}

## Steps
1. Search uploaded material for content relevant to {assignment_topic}
2. Build an outline with introduction, key arguments, and conclusion
3. Draft the assignment within {word_limit} words using evidence from sources
4. Generate an improvement checklist for clarity, structure, and citations

## Output
- Assignment first draft
- Structured outline
- Editing checklist

## Rules
- Keep arguments logically sequenced
- Use academically appropriate tone
- Ensure each section supports the main thesis
""",
    },
    {
        "slug": "citation-fact-checker",
        "title": "Citation and Fact Checker",
        "description": "Verify factual statements and improve source reliability before submission",
        "tags": ["research", "quality", "citations"],
        "markdown": """# Skill: Citation and Fact Checker

## Input
document_topic: {user_input}

## Steps
1. Search uploaded draft documents related to {document_topic}
2. Extract factual claims and key statistics from the draft
3. Search the web for authoritative corroborating sources
4. Produce a verification report with supported, weak, and unsupported claims

## Output
- Fact-check report
- Source reliability notes
- Suggested citation improvements

## Rules
- Prefer peer-reviewed or authoritative institutional sources
- Flag uncertain claims explicitly
- Separate verified facts from opinions
""",
    },
    {
        "slug": "daily-learning-recap",
        "title": "Daily Learning Recap",
        "description": "Create a daily recap and next-day plan from study activity",
        "tags": ["student", "daily", "productivity"],
        "markdown": """# Skill: Daily Learning Recap

## Input
today_focus: {user_input}

## Steps
1. Search uploaded notes and materials related to {today_focus}
2. Summarize what was learned today into key points and examples
3. Identify unresolved doubts and weak areas
4. Generate a focused plan for tomorrow's learning session

## Output
- Daily learning recap
- Doubts and weak areas list
- Next-day action plan

## Rules
- Keep recap short and actionable
- Prioritize unresolved doubts for tomorrow
- Include one measurable goal for the next day
""",
    },
    {
        "slug": "dataset-eda-report",
        "title": "Dataset EDA Report",
        "description": "Produce a practical exploratory data analysis report for research datasets",
        "tags": ["research", "data", "eda"],
        "markdown": """# Skill: Dataset EDA Report

## Input
dataset_goal: {user_input}

## Steps
1. Search uploaded documents to identify dataset files and schema for {dataset_goal}
2. Generate Python code to compute summary statistics and data quality checks
3. Create visualizations for distributions, correlations, and anomalies
4. Summarize findings and recommend next analytical steps

## Output
- EDA summary
- Charts and diagnostics
- Recommended next steps

## Rules
- Use pandas and matplotlib/seaborn
- Include missing-value and outlier analysis
- Keep insights decision-oriented
""",
    },
    {
        "slug": "methodology-comparator",
        "title": "Methodology Comparator",
        "description": "Compare approaches/methods and recommend the best fit for a project",
        "tags": ["research", "methodology", "decision"],
        "markdown": """# Skill: Methodology Comparator

## Input
project_goal: {user_input}

## Steps
1. Search uploaded material for candidate methods relevant to {project_goal}
2. Search the web for benchmark studies and practical comparisons
3. Compare methods by assumptions, data needs, complexity, and expected outcomes
4. Recommend the most suitable approach with trade-offs

## Output
- Method comparison matrix
- Recommended approach
- Trade-off summary

## Rules
- Make criteria explicit and consistent
- Avoid one-size-fits-all recommendations
- Include risks and mitigation notes
""",
    },
    {
        "slug": "presentation-from-notes",
        "title": "Presentation from Notes",
        "description": "Convert notes into a clear presentation outline and downloadable slides",
        "tags": ["student", "research", "presentation"],
        "markdown": """# Skill: Presentation from Notes

## Input
presentation_topic: {user_input}

## Steps
1. Search uploaded notes and references about {presentation_topic}
2. Create a slide-by-slide outline with key points and supporting evidence
3. Generate concise speaker notes for each slide
4. Generate Python code to export slides as a presentation file

## Output
- Slide outline
- Speaker notes
- Downloadable presentation file

## Rules
- Keep each slide focused on one core message
- Use concise bullets, not dense paragraphs
- Ensure flow from problem to conclusion
""",
    },
]


# ── CRUD Operations ────────────────────────────────────────

async def create_skill(
    user_id: str,
    markdown: str,
    notebook_id: Optional[str] = None,
    is_global: bool = False,
    tags: Optional[List[str]] = None,
) -> dict:
    """Create a new skill from markdown."""
    # Validate and parse
    definition = parse_skill_markdown(markdown)
    _validate_variables_defined(definition)

    slug = _slugify(definition.title)

    # Check for slug collision
    existing = await prisma.skill.find_first(
        where={
            "slug": slug,
            "userId": user_id,
            "notebookId": notebook_id if not is_global else None,
        }
    )
    if existing:
        # Append number suffix
        count = await prisma.skill.count(
            where={"userId": user_id, "slug": {"startswith": slug}}
        )
        slug = f"{slug}-{count + 1}"

    skill = await prisma.skill.create(
        data={
            "userId": user_id,
            "notebookId": notebook_id if not is_global else None,
            "slug": slug,
            "title": definition.title,
            "description": definition.description or "",
            "markdown": markdown,
            "isGlobal": is_global,
            "tags": tags or [],
        }
    )

    logger.info("Created skill '%s' (id=%s, slug=%s)", definition.title, skill.id, slug)
    return _skill_to_dict(skill, definition)


async def update_skill(
    skill_id: str,
    user_id: str,
    markdown: str,
    tags: Optional[List[str]] = None,
) -> dict:
    """Update an existing skill."""
    skill = await resolve_skill_by_id(skill_id, user_id)
    if not skill:
        raise ValueError("Skill not found")

    definition = parse_skill_markdown(markdown)
    _validate_variables_defined(definition)

    update_data: Dict[str, Any] = {
        "markdown": markdown,
        "title": definition.title,
        "description": definition.description or "",
        "version": skill.version + 1,
    }
    if tags is not None:
        update_data["tags"] = tags

    updated = await prisma.skill.update(
        where={"id": skill_id},
        data=update_data,
    )

    logger.info("Updated skill '%s' (id=%s, v%d)", definition.title, skill_id, updated.version)
    return _skill_to_dict(updated, definition)


async def delete_skill(skill_id: str, user_id: str) -> bool:
    """Delete a skill."""
    skill = await resolve_skill_by_id(skill_id, user_id)
    if not skill:
        return False
    await prisma.skill.delete(where={"id": skill_id})
    logger.info("Deleted skill id=%s", skill_id)
    return True


async def get_skill(skill_id: str, user_id: str) -> Optional[dict]:
    """Get a single skill by ID."""
    skill = await resolve_skill_by_id(skill_id, user_id)
    if not skill:
        return None
    try:
        definition = parse_skill_markdown(skill.markdown)
    except MarkdownParseError:
        definition = None
    return _skill_to_dict(skill, definition)


async def list_skills(
    user_id: str,
    notebook_id: Optional[str] = None,
    include_global: bool = True,
) -> List[dict]:
    """List skills available to a user in a notebook context."""
    conditions = []

    if notebook_id:
        conditions.append({
            "userId": user_id,
            "notebookId": notebook_id,
        })

    if include_global:
        conditions.append({
            "userId": user_id,
            "isGlobal": True,
        })

    if not conditions:
        conditions.append({"userId": user_id})

    skills = await prisma.skill.find_many(
        where={"OR": conditions} if len(conditions) > 1 else conditions[0],
        order={"updatedAt": "desc"},
    )

    result = []
    for skill in skills:
        try:
            definition = parse_skill_markdown(skill.markdown)
        except MarkdownParseError:
            definition = None
        result.append(_skill_to_dict(skill, definition))

    return result


async def get_templates() -> List[dict]:
    """Get built-in skill templates."""
    templates = []
    for tmpl in BUILT_IN_TEMPLATES:
        try:
            definition = parse_skill_markdown(tmpl["markdown"])
            templates.append({
                "slug": tmpl["slug"],
                "title": tmpl["title"],
                "description": tmpl["description"],
                "tags": tmpl["tags"],
                "markdown": tmpl["markdown"],
                "inputs": [
                    {"name": v.name, "description": v.description}
                    for v in definition.inputs
                ],
                "steps_count": len(definition.steps),
            })
        except MarkdownParseError:
            pass
    return templates


# ── Run Orchestration ──────────────────────────────────────

async def run_skill(
    skill_id: str,
    user_id: str,
    notebook_id: Optional[str] = None,
    session_id: Optional[str] = None,
    material_ids: Optional[List[str]] = None,
    variables: Optional[Dict[str, str]] = None,
) -> AsyncIterator[str]:
    """
    Full skill execution pipeline: resolve → parse → compile → execute.

    Yields SSE events for real-time streaming.
    """
    variables = variables or {}
    material_ids = material_ids or []

    # 1. Resolve skill
    skill = await resolve_skill_by_id(skill_id, user_id)
    if not skill:
        error = "Skill not found"
        yield _sse("skill_status", {"status": "failed", "error": error})
        yield _sse("skill_done", {
            "status": "failed",
            "total_steps": 0,
            "successful_steps": 0,
            "failed_steps": 0,
            "artifacts_count": 0,
            "elapsed_seconds": 0.0,
            "final_output": "",
            "step_logs": [],
            "artifacts": [],
            "error": error,
        })
        return

    effective_notebook_id = notebook_id or getattr(skill, "notebookId", None)

    # 2. Parse markdown
    try:
        definition = parse_skill_markdown(skill.markdown)
    except MarkdownParseError as e:
        error = f"Parse error: {e}"
        yield _sse("skill_status", {"status": "failed", "error": error})
        yield _sse("skill_done", {
            "status": "failed",
            "total_steps": 0,
            "successful_steps": 0,
            "failed_steps": 0,
            "artifacts_count": 0,
            "elapsed_seconds": 0.0,
            "final_output": "",
            "step_logs": [],
            "artifacts": [],
            "error": error,
        })
        return

    try:
        _validate_variables_defined(definition)
    except ValueError as e:
        error = str(e)
        yield _sse("skill_status", {"status": "failed", "error": error})
        yield _sse("skill_done", {
            "status": "failed",
            "total_steps": 0,
            "successful_steps": 0,
            "failed_steps": 0,
            "artifacts_count": 0,
            "elapsed_seconds": 0.0,
            "final_output": "",
            "step_logs": [],
            "artifacts": [],
            "error": error,
        })
        return

    # 3. Populate default variables
    for inp in definition.inputs:
        if inp.name not in variables and inp.default_value:
            variables[inp.name] = inp.default_value

    # Auto-map 'user_input' to 'topic' or first input key if needed
    if "user_input" in variables:
        for inp in definition.inputs:
            if inp.name != "user_input" and inp.name not in variables:
                variables[inp.name] = variables["user_input"]

    # 4. Create run record
    run = await prisma.skillrun.create(
        data={
            "skillId": skill.id,
            "userId": user_id,
            "notebookId": effective_notebook_id,
            "status": "running",
            "variables": Json(_to_json_compatible(variables)),
            "startedAt": datetime.now(timezone.utc),
        }
    )

    yield _sse("skill_status", {
        "status": "compiling",
        "run_id": run.id,
        "skill_title": definition.title,
        "message": f"Compiling skill '{definition.title}'...",
    })

    # 5. Compile
    try:
        has_materials = bool(material_ids)
        plan = await compile_skill(definition, variables, has_materials)
    except Exception as e:
        await prisma.skillrun.update(
            where={"id": run.id},
            data={
                "status": "failed",
                "error": f"Compilation failed: {e}",
                "completedAt": datetime.now(timezone.utc),
            },
        )
        error = f"Compilation failed: {e}"
        yield _sse("skill_status", {"status": "failed", "error": error})
        yield _sse("skill_done", {
            "status": "failed",
            "run_id": run.id,
            "total_steps": 0,
            "successful_steps": 0,
            "failed_steps": 0,
            "artifacts_count": 0,
            "elapsed_seconds": 0.0,
            "final_output": "",
            "step_logs": [],
            "artifacts": [],
            "error": error,
        })
        return

    yield _sse("skill_status", {
        "status": "running",
        "message": f"Executing {len(plan)} steps...",
        "plan": [{"index": s.get("index"), "instruction": s.get("instruction", "")[:100], "tool": s.get("tool", "llm")} for s in plan],
    })

    # 6. Execute
    step_logs: List[Dict[str, Any]] = []
    all_artifacts: List[Dict[str, Any]] = []
    done_payload: Optional[Dict[str, Any]] = None
    start_time = time.time()

    async for event_str in execute_skill(
        plan=plan,
        user_id=user_id,
        notebook_id=effective_notebook_id or "",
        session_id=session_id or "",
        material_ids=material_ids,
        variables=variables,
        rules=definition.rules,
    ):
        yield event_str

        event_name, event_data = _parse_sse_event(event_str)
        if event_name == "skill_done" and isinstance(event_data, dict):
            done_payload = event_data
        elif event_name in {"skill_step_result", "skill_step_error", "skill_step_skipped"} and isinstance(event_data, dict):
            step_logs.append(event_data)
        elif event_name == "skill_artifact" and isinstance(event_data, dict):
            all_artifacts.append(event_data)

    total_elapsed = time.time() - start_time
    if done_payload:
        done_logs = done_payload.get("step_logs")
        done_artifacts = done_payload.get("artifacts")
        if isinstance(done_logs, list):
            step_logs = done_logs
        if isinstance(done_artifacts, list):
            all_artifacts = done_artifacts
        executor_status = str(done_payload.get("status") or "")
        final_output = str(done_payload.get("final_output") or "")
    else:
        executor_status = ""
        final_output = ""

    persisted_status = _derive_persisted_status(executor_status, step_logs)
    first_error = next(
        (
            str(log.get("error"))
            for log in step_logs
            if isinstance(log, dict) and log.get("success") is False and log.get("error")
        ),
        None,
    )

    # 7. Persist run results
    try:
        update_data = {
            "status": persisted_status,
            "stepLogs": Json(_to_json_compatible(step_logs)),
            "result": Json(_to_json_compatible({
                "status": executor_status or persisted_status,
                "steps": len(step_logs),
                "output": final_output,
            })),
            "completedAt": datetime.now(timezone.utc),
            "elapsedTime": round(total_elapsed, 2),
            "error": first_error if persisted_status == "failed" else None,
        }
        update_data["artifacts"] = Json(_to_json_compatible(all_artifacts or []))

        await prisma.skillrun.update(
            where={"id": run.id},
            data=update_data,
        )
    except Exception as e:
        logger.error("Failed to persist skill run results: %s", e)


async def run_skill_by_slug(
    slug: str,
    user_id: str,
    notebook_id: Optional[str] = None,
    session_id: Optional[str] = None,
    material_ids: Optional[List[str]] = None,
    variables: Optional[Dict[str, str]] = None,
) -> AsyncIterator[str]:
    """Run a skill by slug (used from chat /skills command)."""
    skill = await resolve_skill(slug, user_id, notebook_id)
    if not skill:
        error = f"Skill '{slug}' not found"
        yield _sse("skill_status", {"status": "failed", "error": error})
        yield _sse("skill_done", {
            "status": "failed",
            "total_steps": 0,
            "successful_steps": 0,
            "failed_steps": 0,
            "artifacts_count": 0,
            "elapsed_seconds": 0.0,
            "final_output": "",
            "step_logs": [],
            "artifacts": [],
            "error": error,
        })
        return

    async for event in run_skill(
        skill_id=skill.id,
        user_id=user_id,
        notebook_id=notebook_id,
        session_id=session_id,
        material_ids=material_ids,
        variables=variables,
    ):
        yield event


# ── Run History ────────────────────────────────────────────

async def get_skill_runs(
    user_id: str,
    skill_id: Optional[str] = None,
    limit: int = 20,
) -> List[dict]:
    """Get skill execution history."""
    where: Dict[str, Any] = {"userId": user_id}
    if skill_id:
        where["skillId"] = skill_id

    runs = await prisma.skillrun.find_many(
        where=where,
        order={"createdAt": "desc"},
        take=limit,
        include={"skill": True},
    )

    return [
        {
            "id": r.id,
            "skill_id": r.skillId,
            "skill_title": r.skill.title if r.skill else "Unknown",
            "status": r.status,
            "variables": _coerce_json_field(r.variables, {}),
            "step_logs": _coerce_json_field(r.stepLogs, []),
            "result": _coerce_json_field(r.result, None),
            "artifacts": _coerce_json_field(r.artifacts, []),
            "error": r.error,
            "elapsed_time": r.elapsedTime,
            "started_at": r.startedAt.isoformat() if r.startedAt else None,
            "completed_at": r.completedAt.isoformat() if r.completedAt else None,
            "created_at": r.createdAt.isoformat(),
        }
        for r in runs
    ]


async def get_skill_run(run_id: str, user_id: str) -> Optional[dict]:
    """Get a single skill run with full details."""
    run = await prisma.skillrun.find_first(
        where={"id": run_id, "userId": user_id},
        include={"skill": True},
    )
    if not run:
        return None

    return {
        "id": run.id,
        "skill_id": run.skillId,
        "skill_title": run.skill.title if run.skill else "Unknown",
        "skill_slug": run.skill.slug if run.skill else "",
        "status": run.status,
        "variables": _coerce_json_field(run.variables, {}),
        "step_logs": _coerce_json_field(run.stepLogs, []),
        "result": _coerce_json_field(run.result, None),
        "artifacts": _coerce_json_field(run.artifacts, []),
        "error": run.error,
        "elapsed_time": run.elapsedTime,
        "started_at": run.startedAt.isoformat() if run.startedAt else None,
        "completed_at": run.completedAt.isoformat() if run.completedAt else None,
        "created_at": run.createdAt.isoformat(),
    }


# ── Utility ────────────────────────────────────────────────

def _skill_to_dict(skill, definition=None) -> dict:
    """Convert a Prisma Skill record to a response dict."""
    result = {
        "id": skill.id,
        "slug": skill.slug,
        "title": skill.title,
        "description": skill.description,
        "markdown": skill.markdown,
        "version": skill.version,
        "is_global": skill.isGlobal,
        "tags": skill.tags or [],
        "notebook_id": skill.notebookId,
        "created_at": skill.createdAt.isoformat(),
        "updated_at": skill.updatedAt.isoformat(),
    }
    if definition:
        result["parsed"] = {
            "inputs": [
                {"name": v.name, "default_value": v.default_value, "description": v.description}
                for v in definition.inputs
            ],
            "steps_count": len(definition.steps),
            "outputs": definition.outputs,
            "variables": definition.all_variables,
        }
    return result
