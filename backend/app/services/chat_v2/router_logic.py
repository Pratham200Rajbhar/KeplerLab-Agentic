from __future__ import annotations

import re
import logging
from typing import List, Optional

from .schemas import Capability

logger = logging.getLogger(__name__)

_CODE_KEYWORDS = re.compile(
    r"\b(plot|chart|graph|histogram|scatter|heatmap|dataset|csv|dataframe|"
    r"regression|classify|cluster|analyze data|data analysis|visuali[sz]e|"
    r"train model|predict|correlation|boxplot|bar chart|pie chart|"
    r"pandas|numpy|matplotlib|seaborn|sklearn)\b",
    re.IGNORECASE,
)

_WEB_SEARCH_KEYWORDS = re.compile(
    r"\b(search the web|search online|latest news|current events|"
    r"look up online|find online|google|what.s happening|"
    r"recent developments|today.s|this week)\b",
    re.IGNORECASE,
)

# Tasks that need code execution even when materials are selected.
# These should route to AGENT (which runs python_auto), not RAG.
_DATA_ANALYSIS_KEYWORDS = re.compile(
    r"\b(plot|chart|graph|histogram|scatter|heatmap|boxplot|bar chart|"
    r"pie chart|line chart|visuali[sz]e|visualization|dashboard|"
    r"train model|predict|regression|classif|cluster|correlation|"
    r"machine learning|random forest|xgboost|logistic|"
    r"EDA|exploratory data|statistics|distribution|"
    r"generate .{0,30}(?:pdf|csv|excel|xlsx|docx|report|pptx)|"
    r"create .{0,30}(?:pdf|csv|excel|xlsx|docx|report|pptx)|"
    r"export .{0,20}(?:pdf|csv|excel|xlsx|docx|report)|confusion matrix)\b",
    re.IGNORECASE,
)

_GENERATIVE_KEYWORDS = re.compile(
    r"\b(write|draft|compose|create a report|generate a presentation|workflow|multi-step|plan and execute)\b",
    re.IGNORECASE,
)


def _classify_request_type(message: str) -> str:
    """Classify request into factual, analytical, computational, generative, or external."""
    if _WEB_SEARCH_KEYWORDS.search(message):
        return "external"
    if _CODE_KEYWORDS.search(message) or _DATA_ANALYSIS_KEYWORDS.search(message):
        return "computational"
    if _GENERATIVE_KEYWORDS.search(message):
        return "generative"

    lowered = message.lower()
    analytical_markers = (
        "why ", "how ", "compare", "contrast", "tradeoff", "pros and cons", "analysis"
    )
    if any(m in lowered for m in analytical_markers):
        return "analytical"
    return "factual"

def route_capability(
    message: str,
    material_ids: List[str],
    intent_override: Optional[str] = None,
) -> Capability:
    has_materials = bool(material_ids)
    request_type = _classify_request_type(message)

    if intent_override:
        override_upper = intent_override.upper()
        try:
            cap = Capability(override_upper)
            if has_materials and cap == Capability.AGENT:
                logger.info("Capability routed by intent_override: AGENT (materials preserved)")
                return Capability.AGENT
            if has_materials and cap == Capability.RAG:
                logger.info("RAG intent override adjusted to NORMAL_CHAT (decommissioned)")
                return Capability.NORMAL_CHAT
            logger.info("Capability routed by intent_override: %s", cap.value)
            return cap
        except ValueError:
            logger.warning("Unknown intent_override '%s', falling through", intent_override)

    if message.lstrip().startswith("/skills"):
        logger.info("Capability routed to SKILL_EXECUTION (/skills prefix)")
        return Capability.SKILL_EXECUTION

    if message.lstrip().startswith("/image"):
        logger.info("Capability routed to IMAGE_GENERATION (/image prefix)")
        return Capability.IMAGE_GENERATION

    if message.lstrip().startswith("/agent"):
        # Explicit /agent command must stay in AGENT mode even with selected sources.
        # The agent enforces retrieval-first policy internally when materials exist.
        logger.info("Capability routed to AGENT (/agent prefix)")
        return Capability.AGENT

    # When materials are selected AND the task needs code execution
    # (charts, ML, file generation), route to AGENT — not RAG.
    # RAG is decommissioned, falling back to NORMAL_CHAT or AGENT.
    if has_materials:
        if _DATA_ANALYSIS_KEYWORDS.search(message) or request_type in {"computational", "generative"}:
            logger.info(
                "Capability routed to AGENT with selected materials (request_type=%s)",
                request_type,
            )
            return Capability.AGENT
        logger.info("Capability routed to NORMAL_CHAT (RAG decommissioned)")
        return Capability.NORMAL_CHAT

    logger.info("Request classified as: %s", request_type)

    if request_type in {"factual", "analytical"}:
        return Capability.NORMAL_CHAT
    if request_type == "computational":
        return Capability.CODE_EXECUTION
    if request_type == "generative":
        return Capability.AGENT
    if request_type == "external":
        return Capability.WEB_SEARCH

    if _CODE_KEYWORDS.search(message):
        logger.info("Capability routed to CODE_EXECUTION (keyword match)")
        return Capability.CODE_EXECUTION

    if _WEB_SEARCH_KEYWORDS.search(message):
        logger.info("Capability routed to WEB_SEARCH (keyword match)")
        return Capability.WEB_SEARCH

    logger.info("Capability routed to NORMAL_CHAT (default)")
    return Capability.NORMAL_CHAT
