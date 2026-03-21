"""Structured logging helpers for the agent pipeline.

Each pipeline stage emits a clean bordered block, e.g.:

    ╔══════════════════════════════════════════════════════════════╗
    ║  [AGENT] Phase 1 · Intent Analysis                          ║
    ║  ─────────────────────────────────────────────────────────  ║
    ║  has_datasets   : False                                     ║
    ║  has_documents  : True                                      ║
    ║  file_gen       : False                                     ║
    ╚══════════════════════════════════════════════════════════════╝

Usage::

    from .log_utils import log_stage
    log_stage(logger, "Phase 1 · Intent Analysis", {"task_type": task_type, ...})
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

_W = 64  # total line width (including the two ║ border chars)


def log_stage(
    logger: logging.Logger,
    label: str,
    fields: Optional[Dict[str, Any]] = None,
    *,
    level: int = logging.INFO,
) -> None:
    """Emit a clean bordered log block for a named pipeline stage."""
    inner = _W - 2          # chars between the two ║ chars
    bar   = "═" * inner

    title_text = f"  [AGENT] {label}"
    title_line = ("║" + title_text).ljust(_W - 1) + "║"

    lines: list[str] = [f"╔{bar}╗", title_line]

    if fields:
        sep = "║  " + "─" * (inner - 3) + "  ║"
        lines.append(sep)
        for k, v in fields.items():
            val  = str(v)
            cell = f"║  {k:<16}: {val}"
            if len(cell) >= _W - 1:
                cell = cell[: _W - 4] + "…"
            lines.append(cell.ljust(_W - 1) + "║")

    lines.append(f"╚{bar}╝")

    for line in lines:
        logger.log(level, line)
