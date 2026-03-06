"""Tool Selector — Intelligent tool selection based on task analysis.

Classifies user requests and selects appropriate tools with reasoning.
Supports:
- Dataset analysis → Python sandbox
- ML training → Python sandbox  
- Web information → Web search tool
- Document questions → RAG retrieval
- Diagram generation → Visualization tool
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    """Classification of task types."""
    DATA_ANALYSIS = "data_analysis"
    ML_TRAINING = "ml_training"
    VISUALIZATION = "visualization"
    COMPUTATION = "computation"
    DOCUMENT_QA = "document_qa"
    WEB_SEARCH = "web_search"
    RESEARCH = "research"
    CODE_GENERATION = "code_generation"
    GENERAL = "general"


@dataclass
class ToolSelection:
    """Result of tool selection."""
    tool: str
    reasoning: str
    confidence: float
    expected_output: str
    inputs: Dict[str, Any]
    task_type: TaskType


@dataclass
class TaskClassification:
    """Classification result for a user query."""
    task_type: TaskType
    confidence: float
    requires_materials: bool
    requires_computation: bool
    requires_web: bool
    keywords_matched: List[str]


# Keyword patterns for task classification
TASK_PATTERNS = {
    TaskType.DATA_ANALYSIS: [
        "analyze", "analysis", "dataset", "data", "csv", "statistics",
        "summary", "describe", "distribution", "correlation", "missing",
        "explore", "exploratory", "eda", "profile", "overview"
    ],
    TaskType.ML_TRAINING: [
        "train", "model", "machine learning", "ml", "predict", "classifier",
        "regression", "classification", "accuracy", "fit", "random forest",
        "xgboost", "neural", "deep learning", "sklearn", "scikit"
    ],
    TaskType.VISUALIZATION: [
        "chart", "plot", "graph", "visualize", "visualization", "histogram",
        "scatter", "bar chart", "pie chart", "heatmap", "confusion matrix",
        "feature importance", "distribution plot"
    ],
    TaskType.COMPUTATION: [
        "calculate", "compute", "math", "formula", "equation", "solve",
        "numerical", "simulation", "algorithm"
    ],
    TaskType.DOCUMENT_QA: [
        "document", "explain", "summarize", "what is", "how does", "why",
        "according to", "based on", "from the", "in the material"
    ],
    TaskType.WEB_SEARCH: [
        "search", "find", "latest", "current", "news", "today", "recent",
        "look up", "google", "internet"
    ],
    TaskType.RESEARCH: [
        "research", "investigate", "deep dive", "comprehensive", "report",
        "sources", "cite", "reference"
    ],
    TaskType.CODE_GENERATION: [
        "code", "script", "program", "function", "implement", "write code",
        "python", "generate code"
    ],
}

# Tool mappings for task types
TASK_TO_TOOLS = {
    TaskType.DATA_ANALYSIS: ["python_tool"],
    TaskType.ML_TRAINING: ["python_tool"],
    TaskType.VISUALIZATION: ["python_tool"],
    TaskType.COMPUTATION: ["python_tool"],
    TaskType.DOCUMENT_QA: ["rag_tool"],
    TaskType.WEB_SEARCH: ["web_search_tool"],
    TaskType.RESEARCH: ["research_tool"],
    TaskType.CODE_GENERATION: ["python_tool"],
    TaskType.GENERAL: ["rag_tool", "python_tool"],
}


def classify_task(query: str, has_materials: bool = False) -> TaskClassification:
    """Classify a user query into a task type.
    
    Args:
        query: User's natural language query
        has_materials: Whether user has uploaded materials
        
    Returns:
        TaskClassification with type, confidence, and metadata
    """
    query_lower = query.lower()
    
    # Score each task type
    scores: Dict[TaskType, tuple[float, List[str]]] = {}
    
    for task_type, patterns in TASK_PATTERNS.items():
        matched = [p for p in patterns if p in query_lower]
        if matched:
            # Score based on number and specificity of matches
            score = sum(len(m) for m in matched) / 100.0
            score = min(score, 1.0)
            scores[task_type] = (score, matched)
    
    if not scores:
        # Default classification
        if has_materials:
            return TaskClassification(
                task_type=TaskType.DOCUMENT_QA,
                confidence=0.4,
                requires_materials=True,
                requires_computation=False,
                requires_web=False,
                keywords_matched=[],
            )
        return TaskClassification(
            task_type=TaskType.GENERAL,
            confidence=0.3,
            requires_materials=False,
            requires_computation=False,
            requires_web=False,
            keywords_matched=[],
        )
    
    # Find best match
    best_type = max(scores.keys(), key=lambda t: scores[t][0])
    best_score, matched = scores[best_type]
    
    # Determine requirements
    requires_computation = best_type in (
        TaskType.DATA_ANALYSIS, TaskType.ML_TRAINING,
        TaskType.VISUALIZATION, TaskType.COMPUTATION,
        TaskType.CODE_GENERATION
    )
    requires_materials = best_type == TaskType.DOCUMENT_QA and has_materials
    requires_web = best_type in (TaskType.WEB_SEARCH, TaskType.RESEARCH)
    
    return TaskClassification(
        task_type=best_type,
        confidence=best_score,
        requires_materials=requires_materials,
        requires_computation=requires_computation,
        requires_web=requires_web,
        keywords_matched=matched,
    )


def select_tool(
    query: str,
    task_classification: TaskClassification,
    context: Optional[str] = None,
    has_materials: bool = False,
) -> ToolSelection:
    """Select the best tool for a classified task.
    
    Args:
        query: User's query
        task_classification: Result of classify_task
        context: Optional context from previous steps
        has_materials: Whether materials are available
        
    Returns:
        ToolSelection with tool name, reasoning, and inputs
    """
    task_type = task_classification.task_type
    tools = TASK_TO_TOOLS.get(task_type, ["python_tool"])
    primary_tool = tools[0]
    
    # Build reasoning
    reasoning_parts = []
    reasoning_parts.append(f"Task classified as {task_type.value}")
    
    if task_classification.keywords_matched:
        keywords = ", ".join(task_classification.keywords_matched[:3])
        reasoning_parts.append(f"Keywords matched: {keywords}")
    
    # Determine expected output
    expected_outputs = {
        "python_tool": "Code execution results, data files, charts, or models",
        "rag_tool": "Relevant information from uploaded documents",
        "web_search_tool": "Current information from the web",
        "research_tool": "Comprehensive research report with sources",
    }
    expected_output = expected_outputs.get(primary_tool, "Tool output")
    
    # Build tool inputs
    inputs: Dict[str, Any] = {}
    
    if primary_tool == "python_tool":
        inputs["task"] = query
        if context:
            inputs["context"] = context
        reasoning_parts.append("Using Python sandbox for computation/analysis")
        
    elif primary_tool == "rag_tool":
        inputs["query"] = query
        reasoning_parts.append("Searching uploaded materials for relevant information")
        
    elif primary_tool == "web_search_tool":
        inputs["query"] = query
        reasoning_parts.append("Searching the web for current information")
        
    elif primary_tool == "research_tool":
        inputs["query"] = query
        reasoning_parts.append("Conducting deep research with multiple sources")
    
    return ToolSelection(
        tool=primary_tool,
        reasoning=". ".join(reasoning_parts),
        confidence=task_classification.confidence,
        expected_output=expected_output,
        inputs=inputs,
        task_type=task_type,
    )


async def generate_execution_plan(
    query: str,
    material_ids: List[str],
    context: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Generate a multi-step execution plan using LLM.
    
    Falls back to rule-based planning if LLM fails.
    
    Args:
        query: User's request
        material_ids: IDs of uploaded materials
        context: Optional prior context
        
    Returns:
        List of plan steps with tool, description, and inputs
    """
    from app.services.llm_service.llm import get_llm
    from app.services.llm_service.structured_invoker import async_invoke_structured_safe
    from app.services.agent.schemas import AgentPlan
    
    has_materials = bool(material_ids)
    
    # First, try task classification
    classification = classify_task(query, has_materials)
    
    # Build LLM prompt for planning
    tools_description = """Available tools:
- rag_tool: Search user's uploaded materials for relevant information. Input: {"query": "search query"}
- python_tool: Generate and run Python code to analyze data, create charts, train models, or compute results. Input: {"task": "description of what to code"}
- web_search_tool: Search the web for current information. Input: {"query": "search query"}  
- research_tool: Do deep multi-step web research. Input: {"query": "research question"}"""

    material_hint = (
        " (materials are available - consider searching them first)"
        if has_materials
        else " (no materials uploaded - skip rag_tool)"
    )

    system_prompt = f"""You are a task planner for an AI assistant. Given a user request, 
produce a JSON plan of tool steps to fulfill it.

{tools_description}

Planning rules:
1. Use rag_tool FIRST if the user needs info from their documents{material_hint}.
2. Use python_tool for ANY computation, data analysis, ML training, or chart generation.
3. Use web_search_tool for quick factual lookups from the internet.
4. Use research_tool only for comprehensive, multi-source research questions.
5. Keep plans concise: 1-5 steps typically. Don't over-plan.
6. For data analysis tasks: First analyze the dataset, then visualize, then summarize.
7. For ML tasks: Analyze data → clean/preprocess → train model → evaluate → generate charts.
8. If a dataset profile is provided below, USE it to make smarter plans:
   - Reference actual column names and types when describing python_tool tasks
   - Mention specific columns for visualization or analysis
   - Account for missing values and data distributions
   - Use correlation info to suggest feature selection for ML tasks
9. Dataset files are already available in the sandbox working directory — the python_tool can load them directly by filename.

Context from prior analysis:
{context or "No prior context."}

Return ONLY valid JSON matching this schema:
{{"steps": [{{"tool": "tool_name", "description": "what this step does", "inputs": {{...}}}}]}}
"""

    prompt = f"{system_prompt}\n\nUser request: {query}\n\nProduce the JSON plan:"

    try:
        result = await async_invoke_structured_safe(prompt, AgentPlan)
        
        if result.get("success") and result.get("data"):
            data = result["data"]
            if isinstance(data, dict) and "steps" in data:
                return data["steps"]
            if hasattr(data, "steps"):
                return [
                    {"tool": s.tool, "description": s.description, "inputs": dict(s.inputs)}
                    for s in data.steps
                ]
    except Exception as e:
        logger.warning("LLM planning failed: %s, using rule-based fallback", e)
    
    # Fallback: rule-based planning
    return _generate_fallback_plan(query, classification, has_materials)


def _generate_fallback_plan(
    query: str,
    classification: TaskClassification,
    has_materials: bool,
) -> List[Dict[str, Any]]:
    """Generate a fallback plan based on task classification."""
    steps = []
    
    # For document QA with materials
    if classification.task_type == TaskType.DOCUMENT_QA and has_materials:
        steps.append({
            "tool": "rag_tool",
            "description": "Search materials for relevant information",
            "inputs": {"query": query}
        })
        return steps
    
    # For data analysis/ML
    if classification.task_type in (TaskType.DATA_ANALYSIS, TaskType.ML_TRAINING):
        if has_materials:
            steps.append({
                "tool": "rag_tool",
                "description": "Extract dataset information from materials",
                "inputs": {"query": f"dataset information for: {query}"}
            })
        steps.append({
            "tool": "python_tool",
            "description": "Analyze data and generate results",
            "inputs": {"task": query}
        })
        return steps
    
    # For visualization
    if classification.task_type == TaskType.VISUALIZATION:
        steps.append({
            "tool": "python_tool",
            "description": "Generate visualizations",
            "inputs": {"task": query}
        })
        return steps
    
    # For web search
    if classification.task_type == TaskType.WEB_SEARCH:
        steps.append({
            "tool": "web_search_tool",
            "description": "Search the web for information",
            "inputs": {"query": query}
        })
        return steps
    
    # For research
    if classification.task_type == TaskType.RESEARCH:
        steps.append({
            "tool": "research_tool",
            "description": "Conduct comprehensive research",
            "inputs": {"query": query}
        })
        return steps
    
    # Default: single tool based on selection
    selection = select_tool(query, classification, has_materials=has_materials)
    steps.append({
        "tool": selection.tool,
        "description": selection.reasoning,
        "inputs": selection.inputs
    })
    
    return steps


def select_tools_for_task(
    query: str,
    has_materials: bool = False,
    context: Optional[str] = None,
) -> List[ToolSelection]:
    """Select multiple tools that may be needed for a task.
    
    Returns a prioritized list of tool selections.
    """
    classification = classify_task(query, has_materials)
    tools = []
    
    # Primary tool
    primary = select_tool(query, classification, context, has_materials)
    tools.append(primary)
    
    # Add RAG if materials available and not already selected
    if has_materials and primary.tool != "rag_tool":
        rag_selection = ToolSelection(
            tool="rag_tool",
            reasoning="Checking uploaded materials for relevant context",
            confidence=0.7,
            expected_output="Relevant information from documents",
            inputs={"query": query},
            task_type=TaskType.DOCUMENT_QA,
        )
        tools.insert(0, rag_selection)  # RAG first
    
    return tools
