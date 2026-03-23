from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Any

_DIR = os.path.dirname(__file__)
_VAR_PATTERN = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


@lru_cache(maxsize=128)
def _load(rel_path: str) -> str:
    with open(os.path.join(_DIR, rel_path), encoding="utf-8") as f:
        return f.read()


def _render(text: str, variables: dict[str, Any] | None = None) -> str:
    vars_map = {k: "" if v is None else str(v) for k, v in (variables or {}).items()}

    def repl(match: re.Match[str]) -> str:
        return vars_map.get(match.group(1), "")

    return _VAR_PATTERN.sub(repl, text)


def compose_prompt(parts: list[str], variables: dict[str, Any] | None = None) -> str:
    text = "\n\n".join(_load(part).strip() for part in parts if part)
    return _render(text, variables).strip()


def get_prompt_template(path: str) -> str:
    return _load(path)


def get_flashcard_prompt(
    content_text: str,
    card_count: int | None = None,
    difficulty: str = "Medium",
    instructions: str | None = None,
) -> str:
    count = str(card_count) if card_count else "5-10"
    return compose_prompt(
        [
            "system/base_system.md",
            "shared/style.md",
            "shared/formatting.md",
            "generation/flashcard.md",
        ],
        {
            "mode": "flashcard_generation",
            "materials": content_text,
            "difficulty": difficulty,
            "count": count,
            "instructions": instructions or "",
        },
    )


def get_quiz_prompt(
    content_text: str,
    mcq_count: int | None = None,
    difficulty: str = "Medium",
    instructions: str | None = None,
) -> str:
    count = str(mcq_count) if mcq_count else "adaptive"
    return compose_prompt(
        [
            "system/base_system.md",
            "shared/style.md",
            "shared/formatting.md",
            "generation/quiz.md",
        ],
        {
            "mode": "quiz_generation",
            "materials": content_text,
            "difficulty": difficulty,
            "count": count,
            "instructions": instructions or "",
        },
    )


def get_chat_prompt(context: str, chat_history: str, user_message: str) -> str:
    return compose_prompt(
        [
            "system/base_system.md",
            "system/rag_system.md",
            "shared/reasoning.md",
            "shared/style.md",
            "chat/chat_base.md",
            "chat/chat_rag.md",
        ],
        {
            "mode": "chat_rag",
            "question": user_message,
            "conversation_history": chat_history,
            "context": context,
            "materials": "selected notebook materials",
            "instructions": "",
        },
    )


def get_prompt_optimizer_prompt(user_prompt: str, count: int = 4, context: str = "") -> str:
    question = (
        f"Optimize this prompt for better AI performance: \"{user_prompt}\"\n\n"
        f"Generate {count} improved versions with differing styles.\n"
    )
    if context:
        question += (
            "\n"
            "CRITICAL: The user is asking about specific information. Use the following RELEVANT context "
            "to understand the resources they are analyzing, so you can tailor the prompt to be highly "
            "relevant. Do NOT hallucinate facts, but make the prompt specific to the topic present in "
            "the context. DO NOT give unnecessary stuff.\n"
            "---\nCONTEXT START\n"
            f"{context[:10000]}\n"
            "CONTEXT END\n---\n"
        )
    question += (
        "\nReturn as strict JSON with this exact schema:\n"
        "{\"prompts\":[{\"optimized_prompt\":\"...\",\"confidence\":90,\"explanation\":\"...\"}]}"
    )

    return compose_prompt(
        ["generation/optimize.md"],
        {
            "mode": "prompt_optimization",
            "question": question,
        },
    )


def get_presentation_intent_prompt(
    topic: str,
    audience: str,
    purpose: str,
    theme_preference: str,
    material_excerpt: str,
) -> str:
    request = (
        "Analyze presentation intent and output strict JSON with fields: "
        "core_message, presentation_type, tone, complexity_level, key_themes, suggested_structure, visual_emphasis.\n"
        f"Topic: {topic}\nAudience: {audience}\nPurpose: {purpose}\n"
        f"Theme preference: {theme_preference or 'auto'}\n"
        f"Material excerpt:\n{material_excerpt[:3000]}"
    )
    return compose_prompt(
        ["system/base_system.md", "shared/reasoning.md", "shared/formatting.md"],
        {"mode": "presentation_intent", "question": request},
    )


def get_presentation_strategy_prompt(
    intent_analysis: str,
    knowledge_map: str,
    material_context: str,
    slide_count: int,
) -> str:
    request = (
        "Create a slide-by-slide strategy as strict JSON: "
        "{\"slides\":[{\"index\":1,\"title\":\"...\",\"objective\":\"...\",\"layout\":\"...\",\"content_points\":[\"...\"]}]}.\n"
        f"Target slide count: {slide_count}\nIntent: {intent_analysis}\n"
        f"Knowledge map: {knowledge_map}\nContext: {material_context[:4000]}"
    )
    return compose_prompt(
        ["system/base_system.md", "shared/reasoning.md", "shared/formatting.md"],
        {"mode": "presentation_strategy", "question": request},
    )


def get_slide_content_prompt(
    slide_title: str,
    slide_purpose: str,
    layout_type: str,
    primary_component: str,
    supporting_components: str,
    information_density: str,
    narrative_position: str,
    assigned_context: str,
    theme_description: str,
) -> str:
    request = (
        "Generate strict JSON for slide content using the given layout and purpose.\n"
        f"Title: {slide_title}\nPurpose: {slide_purpose}\nLayout: {layout_type}\n"
        f"Primary component: {primary_component}\nSupporting: {supporting_components}\n"
        f"Density: {information_density}\nNarrative position: {narrative_position}\n"
        f"Theme: {theme_description}\nContext: {assigned_context[:3000]}"
    )
    return compose_prompt(
        ["system/base_system.md", "shared/style.md", "shared/formatting.md"],
        {"mode": "slide_content", "question": request},
    )


def get_mindmap_prompt(material_text: str) -> str:
    return compose_prompt(
        [
            "system/base_system.md",
            "shared/reasoning.md",
            "shared/formatting.md",
            "generation/mindmap.md",
        ],
        {
            "mode": "mindmap_generation",
            "materials": material_text,
            "instructions": "",
        },
    )


def get_ppt_prompt(
    material_text: str,
    slide_count: int = 10,
    theme: str | None = None,
    additional_instructions: str | None = None,
) -> str:
    return compose_prompt(
        [
            "system/base_system.md",
            "shared/reasoning.md",
            "shared/style.md",
            "generation/presentation.md",
        ],
        {
            "mode": "presentation_generation",
            "materials": material_text,
            "slide_count": slide_count,
            "theme": theme or "auto",
            "instructions": additional_instructions or "",
        },
    )


def get_code_repair_prompt(broken_code: str, stderr: str) -> str:
    return compose_prompt(
        [
            "system/base_system.md",
            "system/tool_system.md",
            "shared/reasoning.md",
            "code/code_execution.md",
        ],
        {
            "mode": "code_repair",
            "broken_code": broken_code,
            "stderr": stderr,
            "constraints": "Sandboxed execution, relative file paths only.",
            "tool_name": "python_auto",
            "tool_hint": "repair",
            "step_description": "Fix runtime error",
        },
    )


def get_podcast_qa_prompt(language: str, context: str, question: str) -> str:
    return compose_prompt(
        ["system/base_system.md", "shared/style.md", "generation/podcast.md"],
        {
            "mode": "podcast_qa",
            "language": language,
            "materials": context,
            "question": question,
            "mode_instruction": "Answer listener question with context fidelity.",
        },
    )


def get_podcast_script_prompt(language: str, mode_instruction: str, context: str) -> str:
    return compose_prompt(
        ["system/base_system.md", "shared/style.md", "generation/podcast.md"],
        {
            "mode": "podcast_script",
            "language": language,
            "materials": context,
            "mode_instruction": mode_instruction,
            "question": "",
        },
    )


def get_code_generation_prompt(user_request: str) -> str:
    return compose_prompt(
        [
            "system/base_system.md",
            "system/tool_system.md",
            "shared/reasoning.md",
            "code/code_generation.md",
        ],
        {
            "mode": "code_generation",
            "question": user_request,
            "language": "python",
            "context": "",
            "constraints": "Sandboxed execution with relative output paths.",
            "tool_name": "python_auto",
            "tool_hint": "generate",
            "step_description": "Produce executable code",
        },
    )


def get_agent_codegen_prompt(step_goal: str, prior_context: str) -> str:
    return compose_prompt(
        [
            "system/base_system.md",
            "system/agent_system.md",
            "system/tool_system.md",
            "shared/reasoning.md",
            "code/code_generation.md",
        ],
        {
            "mode": "agent_codegen",
            "goal": step_goal,
            "question": step_goal,
            "context": prior_context,
            "language": "python",
            "constraints": "Use prior tool outputs as source of truth.",
            "tools": "python_auto",
            "tool_results": prior_context,
            "tool_name": "python_auto",
            "tool_hint": "codegen",
            "step_description": "Generate artifact-producing code",
        },
    )


def get_data_analysis_prompt(
    filename: str,
    shape: str,
    columns: str,
    dtypes: str,
    describe: str,
    user_request: str,
    dataset_profile: str = "",
) -> str:
    context = (
        f"Filename: {filename}\nShape: {shape}\nColumns: {columns}\nTypes: {dtypes}\n"
        f"Summary: {describe}\nProfile: {dataset_profile or 'N/A'}"
    )
    return compose_prompt(
        [
            "system/base_system.md",
            "system/tool_system.md",
            "shared/reasoning.md",
            "code/code_generation.md",
        ],
        {
            "mode": "dataset_analysis",
            "question": user_request,
            "language": "python",
            "context": context,
            "constraints": "Use provided dataset path and save outputs with deterministic names.",
            "tool_name": "python_auto",
            "tool_hint": "analysis",
            "step_description": "Analyze dataset and generate outputs",
        },
    )


def get_suggestions_prompt(
    notebook_title: str,
    materials_context: str,
    partial_input: str,
) -> str:
    request = (
        "Generate 3-5 high-quality autocomplete suggestions as strict JSON array: "
        "[{\"suggestion\":\"...\",\"confidence\":0.0}].\n"
        f"Notebook: {notebook_title}\nMaterials:\n{materials_context}\n"
        f"Partial input: {partial_input}"
    )
    return compose_prompt(
        ["system/base_system.md", "chat/chat_base.md", "shared/formatting.md"],
        {
            "mode": "suggestions",
            "question": request,
            "conversation_history": "",
            "instructions": "Return JSON only.",
        },
    )


def get_empty_state_suggestions_prompt(materials_context: str) -> str:
    request = (
        "Infer key topics and actionable starter questions from the selected materials. "
        "Return strict JSON: {\"topics\":[\"...\"],\"suggestions\":[\"...\"]}.\n"
        f"Materials:\n{materials_context}"
    )
    return compose_prompt(
        ["system/base_system.md", "chat/chat_base.md", "shared/formatting.md"],
        {
            "mode": "empty_state_suggestions",
            "question": request,
            "conversation_history": "",
            "instructions": "Return JSON object only.",
        },
    )


def get_research_decompose_prompt(query: str, n: int) -> str:
    template = (
        f"You are a research assistant planning a deep web investigation.\n\n"
        f"Decompose the following research query into EXACTLY {n} diverse, specific sub-questions.\n"
        f"Each sub-question should cover a DIFFERENT angle of the topic.\n"
        f"For each sub-question, write one precise web search query (short, 4-10 words).\n\n"
        f"Query: {query}\n\n"
        f"Return ONLY a valid JSON array with this exact structure, no other text:\n"
        f'[{{"sub_question": "...", "search_query": "..."}}]'
    )
    return template


def get_research_gap_prompt(query: str, sources_summary: str, previous_queries: str) -> str:
    template = (
        f"You are a research gap analyst.\n\n"
        f"After reading the sources below, identify EXACTLY 4-6 specific topics, angles, or subtopics "
        f"that are NOT yet covered and would improve the research.\n\n"
        f"Original research question: {query}\n\n"
        f"What has been covered so far (source titles + snippets):\n{sources_summary}\n\n"
        f"Search queries already used:\n{previous_queries}\n\n"
        f"IMPORTANT: Only propose follow-up queries about genuinely missing aspects."
        f" Do NOT repeat or rephrase queries already used.\n\n"
        f"Return ONLY a valid JSON array with this exact structure, no other text:\n"
        f'[{{"sub_question": "what is missing here", "search_query": "precise web search"}}]\n\n'
        f"If all important aspects are already covered, return: []"
    )
    return template


def get_research_report_prompt(query: str, source_ctx: str, source_count: int) -> str:
    request = (
        "Write a comprehensive research report grounded in the provided sources. "
        "Use markdown sections and include evidence-backed analysis.\n"
        f"Topic: {query}\nSource count: {source_count}\nSources:\n{source_ctx}"
    )
    return compose_prompt(
        ["system/base_system.md", "shared/reasoning.md", "shared/style.md", "chat/chat_agent.md"],
        {
            "mode": "research_report",
            "question": request,
            "tool_results": source_ctx,
            "artifacts": "None",
        },
    )


def get_explainer_slide_prompt(
    slide_number: int,
    total_slides: int,
    title: str,
    content: str,
    language: str,
) -> str:
    return compose_prompt(
        ["system/base_system.md", "shared/style.md", "generation/explainer.md"],
        {
            "mode": "explainer_script",
            "slide_number": slide_number,
            "total_slides": total_slides,
            "title": title,
            "content": content,
            "language": language,
        },
    )


def get_podcast_satisfaction_prompt(message: str) -> str:
    return compose_prompt(
        ["system/base_system.md", "chat/chat_base.md", "shared/formatting.md"],
        {
            "mode": "podcast_satisfaction_detection",
            "question": (
                "Classify whether the listener message indicates satisfaction and readiness to continue. "
                "Respond with one word: Yes or No.\n"
                f"Listener message: {message}"
            ),
            "conversation_history": "",
            "instructions": "Return exactly one token: Yes or No.",
        },
    )


def get_web_search_synthesis_prompt(search_results: str, question: str) -> str:
    return compose_prompt(
        ["chat/web_search_synthesis.md"],
        {
            "search_results": search_results,
            "question": question,
        },
    )


def get_json_repair_prompt(broken_json: str, error: str) -> str:
    return _render(
        _load("system/json_repair.md"),
        {"broken_json": broken_json, "error": error},
    )


def get_block_followup_prompt(action: str, block_text: str, question: str = "") -> str:
    action_file_map = {
        "ask": "chat/block_ask.md",
        "simplify": "chat/block_simplify.md",
        "translate": "chat/block_translate.md",
        "explain": "chat/block_explain.md",
    }
    template_path = action_file_map.get(action, "chat/block_ask.md")
    return compose_prompt(
        [template_path],
        {
            "block_text": block_text,
            "question": question,
            "language": question,  # used by block_translate.md
        },
    )


def get_web_completeness_prompt(question: str, search_results: str) -> str:
    return compose_prompt(
        ["generation/web_completeness_check.md"],
        {
            "question": question,
            "search_results": search_results,
        },
    )
