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

def route_capability(
    message: str,
    material_ids: List[str],
    intent_override: Optional[str] = None,
) -> Capability:
    if intent_override:
        override_upper = intent_override.upper()
        try:
            cap = Capability(override_upper)
            logger.info("Capability routed by intent_override: %s", cap.value)
            return cap
        except ValueError:
            logger.warning("Unknown intent_override '%s', falling through", intent_override)

    if message.lstrip().startswith("/agent"):
        logger.info("Capability routed to AGENT (/agent prefix)")
        return Capability.AGENT

    if material_ids:
        logger.info("Capability routed to RAG (materials selected: %d)", len(material_ids))
        return Capability.RAG

    if _CODE_KEYWORDS.search(message):
        logger.info("Capability routed to CODE_EXECUTION (keyword match)")
        return Capability.CODE_EXECUTION

    if _WEB_SEARCH_KEYWORDS.search(message):
        logger.info("Capability routed to WEB_SEARCH (keyword match)")
        return Capability.WEB_SEARCH

    logger.info("Capability routed to NORMAL_CHAT (default)")
    return Capability.NORMAL_CHAT
