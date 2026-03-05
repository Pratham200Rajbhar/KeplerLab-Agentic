"""Sandbox — subprocess-based isolated Python execution.

Provides:
  - ExecutionResult  dataclass
  - run_in_sandbox() async function
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import re
import sys
import tempfile
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable, List, Optional

logger = logging.getLogger(__name__)

# Marker prefix injected by security.py chart capture
_CHART_MARKER = "__CHART__:"

# Maximum bytes of stdout we'll capture (16 MB)
_MAX_OUTPUT_BYTES = 16 * 1024 * 1024


@dataclass
class ExecutionResult:
    """Result from running code in the subprocess sandbox."""

    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    timed_out: bool = False
    elapsed_seconds: float = 0.0
    chart_base64: Optional[str] = None
    error: Optional[str] = None
    output_files: List[str] = field(default_factory=list)


async def run_in_sandbox(
    code: str,
    work_dir: Optional[str] = None,
    timeout: int = 30,
    on_stdout_line: Optional[Callable[[str], Awaitable[None]]] = None,
) -> ExecutionResult:
    """Execute *code* in an isolated subprocess.

    - Creates a temporary working directory if *work_dir* is not given.
    - Streams stdout line-by-line through *on_stdout_line* if provided.
    - Detects ``__CHART__:<base64>`` marker in stdout and extracts it.
    - Enforces *timeout* (seconds); sets ``timed_out=True`` on breach.

    Returns an :class:`ExecutionResult` instance.
    """
    t0 = time.perf_counter()

    _owns_work_dir = work_dir is None
    if _owns_work_dir:
        work_dir = tempfile.mkdtemp(prefix="kepler_sandbox_")

    # Write code to a temp script file
    script_path = os.path.join(work_dir, "_kepler_exec.py")
    try:
        with open(script_path, "w", encoding="utf-8") as fh:
            fh.write(code)
    except Exception as exc:
        return ExecutionResult(
            exit_code=-1,
            error=f"Failed to write script: {exc}",
            elapsed_seconds=time.perf_counter() - t0,
        )

    # Build the subprocess command
    python_exe = sys.executable
    cmd = [python_exe, "-u", script_path]

    stdout_lines: List[str] = []
    stderr_lines: List[str] = []
    chart_b64: Optional[str] = None
    timed_out = False
    exit_code = -1
    error_msg: Optional[str] = None

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=work_dir,
            env={**os.environ, "MPLBACKEND": "Agg"},
        )

        async def _read_stream(stream: asyncio.StreamReader, lines_buf: List[str], is_stdout: bool) -> None:
            """Read a stream line-by-line, collect and optionally emit."""
            nonlocal chart_b64
            total = 0
            while True:
                try:
                    raw = await stream.readline()
                except Exception:
                    break
                if not raw:
                    break
                total += len(raw)
                if total > _MAX_OUTPUT_BYTES:
                    lines_buf.append("[output truncated — too large]")
                    stream.feed_eof()
                    break
                line = raw.decode("utf-8", errors="replace").rstrip("\n")
                if is_stdout and line.startswith(_CHART_MARKER):
                    chart_b64 = line[len(_CHART_MARKER):].strip()
                    # Don't add the raw base64 blob to human-readable output
                else:
                    lines_buf.append(line)
                    if is_stdout and on_stdout_line:
                        try:
                            await on_stdout_line(line)
                        except Exception:
                            pass

        try:
            await asyncio.wait_for(
                asyncio.gather(
                    _read_stream(proc.stdout, stdout_lines, True),
                    _read_stream(proc.stderr, stderr_lines, False),
                ),
                timeout=timeout,
            )
            await proc.wait()
            exit_code = proc.returncode
        except asyncio.TimeoutError:
            timed_out = True
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            # Drain remaining output briefly
            try:
                await asyncio.wait_for(proc.wait(), timeout=2)
            except asyncio.TimeoutError:
                pass
            exit_code = -1

    except Exception as exc:
        error_msg = str(exc)
        logger.error("[sandbox] Subprocess error: %s", exc)
    finally:
        # Clean up temp script
        try:
            os.remove(script_path)
        except OSError:
            pass
        # Remove temp work dir if we created it
        if _owns_work_dir:
            import shutil
            try:
                shutil.rmtree(work_dir, ignore_errors=True)
            except Exception:
                pass

    elapsed = time.perf_counter() - t0

    return ExecutionResult(
        stdout="\n".join(stdout_lines),
        stderr="\n".join(stderr_lines),
        exit_code=exit_code,
        timed_out=timed_out,
        elapsed_seconds=round(elapsed, 3),
        chart_base64=chart_b64,
        error=error_msg,
    )
