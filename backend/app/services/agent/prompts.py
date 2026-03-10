from __future__ import annotations


PLANNER_PROMPT = """\
You are an autonomous AI agent planner. Create a concise execution plan for the goal.

GOAL: {goal}

CONTEXT:
{context}

RESOURCE PROFILE:
{resource_info}

AVAILABLE TOOLS:
{tools_description}

ROUTING RULES:
- CSV/Excel/tabular data → "python_auto" (executes code, shows charts inline, creates downloadable files)
- PDFs/text/notes → "rag" (retrieves relevant passages)
- Current/live/real-time info → "web_search" or "research"
- File/chart/report generation → "python_auto"
- General knowledge (common facts, lists, definitions) → "python_auto" (NO web_search needed)
- Mixed tasks → combine tools in order

Instructions:
- 1–4 steps maximum. Fewer is better.
- Each step = one tool invocation.
- Simple file generation = 1 step with "python_auto".
- Do NOT add web_search for facts the LLM already knows.

Respond with ONLY a JSON array:
[{{"description": "what to do", "tool_hint": "tool_name_or_null"}}]

Examples:
[{{"description": "Generate a PDF listing top 10 Indian cities by population", "tool_hint": "python_auto"}}]

[{{"description": "Search for today's cryptocurrency prices", "tool_hint": "web_search"}}, {{"description": "Generate a PDF report with the prices", "tool_hint": "python_auto"}}]

[{{"description": "Retrieve relevant sections from the uploaded paper", "tool_hint": "rag"}}, {{"description": "Analyze the dataset statistics", "tool_hint": "python_auto"}}]

JSON plan:
"""


TOOL_SELECTOR_PROMPT = """\
Select the single best tool for this step.

GOAL: {goal}
STEP: {step_description}
HINT: {tool_hint}

RESOURCES: {resource_info}
TOOLS: {tools_description}
OBSERVATIONS: {observations}

Rules:
- CSV/Excel/tabular → "python_auto"
- PDFs/documents → "rag"
- Live/current data → "web_search" or "research"
- File/chart generation → "python_auto"
- General knowledge → "python_auto" (not web_search)

Respond with ONLY the tool name:
"""


REFLECTION_PROMPT = """\
Evaluate agent progress toward the goal.

GOAL: {goal}

PLAN:
{plan_summary}

LATEST STEP: {latest_step}
RESULT: {latest_result}

OBSERVATIONS:
{observations}

ARTIFACTS: {artifacts}

Decide:
- "retry" only for transient errors likely to succeed on retry
- "continue" to advance to next step
- "complete" if goal is achieved or all steps done
- "abort" if goal is impossible

Respond with ONLY JSON:
{{"step_succeeded": true/false, "goal_achieved": true/false, "action": "continue|retry|complete|abort", "reason": "brief explanation"}}
"""


SYNTHESIS_PROMPT = """\
You are KeplerLab AI. Synthesize a final response from the agent's execution.

GOAL: {goal}

EXECUTION:
{execution_summary}

OBSERVATIONS:
{observations}

ARTIFACTS: {artifacts}
SOURCES: {sources}

Instructions:
- Address the user's goal clearly with well-structured Markdown.
- For generated files/charts, mention them briefly (the UI shows download cards and inline images).
- Do NOT create markdown tables listing filenames — the UI handles artifact display.
- Cite sources with [1] [2] format where applicable.
- Only report facts found in OBSERVATIONS. Do NOT invent data.
- Be thorough but concise.

Response:
"""
