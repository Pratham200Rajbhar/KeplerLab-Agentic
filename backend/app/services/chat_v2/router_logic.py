"""Chat V2 — Capability router.

Determines which capability (mode) to use for a given chat request.
Lightweight — no LLM calls, pure rule-based routing.
"""

from __future__ import annotations

import re
import logging
from typing import List, Optional

from .schemas import Capability

logger = logging.getLogger(__name__)

# Keywords that signal code execution intent
_CODE_KEYWORDS = re.compile(
    r"\b(plot|chart|graph|histogram|scatter|heatmap|dataset|csv|dataframe|"
    r"regression|classify|cluster|analyze data|data analysis|visuali[sz]e|"
    r"train model|predict|correlation|boxplot|bar chart|pie chart|"
    r"pandas|numpy|matplotlib|seaborn|sklearn)\b",
    re.IGNORECASE,
)

# Keywords that signal web search intent
_WEB_SEARCH_KEYWORDS = re.compile(
    r"\b(search the web|search online|latest news|current events|"
    r"look up online|find online|google|what.s happening|"
    r"recent developments|today.s|this week)\b",
    re.IGNORECASE,
)


def route_capability(
    message: str,
    material_ids: List[str],
    intent_override: Optional[str] = None,
) -> Capability:
    """Determine the capability for a chat request.

    Priority order:
    1. Explicit intent override from frontend slash command
    2. Materials selected → RAG
    3. Code/data keywords → CODE_EXECUTION
    4. Web search keywords → WEB_SEARCH
    5. Default → NORMAL_CHAT

    Args:
        message: User's message text.
        material_ids: List of selected material IDs (already validated).
        intent_override: Explicit override from frontend (AGENT, WEB_RESEARCH, etc.).

    Returns:
        The capability to use.
    """
    # 1. Explicit override always wins
    if intent_override:
        override_upper = intent_override.upper()
        try:
            cap = Capability(override_upper)
            logger.info("Capability routed by intent_override: %s", cap.value)
            return cap
        except ValueError:
            logger.warning("Unknown intent_override '%s', falling through", intent_override)

    # 2. Materials selected → RAG
    if material_ids:
        logger.info("Capability routed to RAG (materials selected: %d)", len(material_ids))
        return Capability.RAG

    # 3. Code / data keywords
    if _CODE_KEYWORDS.search(message):
        logger.info("Capability routed to CODE_EXECUTION (keyword match)")
        return Capability.CODE_EXECUTION

    # 4. Web search keywords
    if _WEB_SEARCH_KEYWORDS.search(message):
        logger.info("Capability routed to WEB_SEARCH (keyword match)")
        return Capability.WEB_SEARCH

    # 5. Default → normal chat
    logger.info("Capability routed to NORMAL_CHAT (default)")
    return Capability.NORMAL_CHAT
