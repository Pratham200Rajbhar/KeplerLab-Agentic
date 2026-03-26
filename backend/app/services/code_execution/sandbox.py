from __future__ import annotations

import asyncio
import logging
import os
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_CHART_MARKER = "__CHART__:"

_MAX_OUTPUT_BYTES = 16 * 1024 * 1024

_LANG_CONFIG: Dict[str, Tuple[str, Optional[List[str]], List[str]]] = {
    "python": (".py", None, [sys.executable, "-u", "{script}"]),
    "javascript": (".js", None, ["node", "{script}"]),
    "typescript": (".ts", None, ["npx", "--yes", "ts-node", "{script}"]),
    "c": (".c", ["gcc", "-O2", "-o", "{binary}", "{script}"], ["{binary}"]),
    "cpp": (".cpp", ["g++", "-O2", "-o", "{binary}", "{script}"], ["{binary}"]),
    "java": (".java", ["javac", "{script}"], ["java", "-cp", "{work_dir}", "Main"]),
    "go": (".go", None, ["go", "run", "{script}"]),
    "rust": (".rs", ["rustc", "-o", "{binary}", "{script}"], ["{binary}"]),
    "bash": (".sh", None, ["bash", "{script}"]),
}

_ALIASES: Dict[str, str] = {
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "c++": "cpp",
    "golang": "go",
    "sh": "bash",
    "shell": "bash",
}

def _normalise_language(language: str) -> str:
    lang = language.lower().strip()
    return _ALIASES.get(lang, lang if lang in _LANG_CONFIG else "python")

@dataclass
class ExecutionResult:

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
    language: str = "python",
    stdin: Optional[str] = None,
) -> ExecutionResult:
    t0 = time.perf_counter()

    _owns_work_dir = work_dir is None
    if _owns_work_dir:
        work_dir = tempfile.mkdtemp(prefix="kepler_sandbox_")

    lang = _normalise_language(language)
    cfg = _LANG_CONFIG[lang]
    ext, compile_tpl, run_tpl = cfg

    script_name = f"Main{ext}" if lang == "java" else f"_kepler_exec{ext}"
    script_path = os.path.join(work_dir, script_name)
    binary_path = os.path.join(work_dir, "_kepler_bin")

    try:
        with open(script_path, "w", encoding="utf-8") as fh:
            fh.write(code)
    except Exception as exc:
        return ExecutionResult(
            exit_code=-1,
            error=f"Failed to write script: {exc}",
            elapsed_seconds=time.perf_counter() - t0,
        )

    def _render(tpl: List[str]) -> List[str]:
        return [
            part.replace("{script}", script_path)
                .replace("{binary}", binary_path)
                .replace("{work_dir}", work_dir)
            for part in tpl
        ]

    if compile_tpl is not None:
        compile_cmd = _render(compile_tpl)
        try:
            compile_proc = await asyncio.create_subprocess_exec(
                *compile_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir,
            )
            try:
                c_stdout, c_stderr = await asyncio.wait_for(
                    compile_proc.communicate(), timeout=60
                )
            except asyncio.TimeoutError:
                compile_proc.kill()
                return ExecutionResult(
                    exit_code=-1,
                    stderr="Compilation timed out",
                    elapsed_seconds=time.perf_counter() - t0,
                )
            if compile_proc.returncode != 0:
                return ExecutionResult(
                    exit_code=compile_proc.returncode,
                    stderr=c_stderr.decode("utf-8", errors="replace"),
                    elapsed_seconds=time.perf_counter() - t0,
                )
        except FileNotFoundError:
            return ExecutionResult(
                exit_code=-1,
                error=f"Compiler not found for language '{lang}'. Please install it.",
                elapsed_seconds=time.perf_counter() - t0,
            )

    run_cmd = _render(run_tpl)

    stdin_bytes: Optional[bytes] = None
    if stdin is not None and stdin != "":
        # Normalize line endings and ensure trailing newline so line-based readers
        # (Scanner/input/scanf loops) don't hang waiting for Enter.
        normalized_stdin = stdin.replace("\r\n", "\n").replace("\r", "\n")
        if normalized_stdin and not normalized_stdin.endswith("\n"):
            normalized_stdin += "\n"
        stdin_bytes = normalized_stdin.encode("utf-8")
    stdin_pipe = asyncio.subprocess.PIPE if stdin_bytes is not None else asyncio.subprocess.DEVNULL

    stdout_lines: List[str] = []
    stderr_lines: List[str] = []
    chart_b64: Optional[str] = None
    timed_out = False
    exit_code = -1
    error_msg: Optional[str] = None

    try:
        proc = await asyncio.create_subprocess_exec(
            *run_cmd,
            stdin=stdin_pipe,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=work_dir,
            env={**os.environ, "MPLBACKEND": "Agg"},
        )

        if stdin_bytes is not None:
            proc.stdin.write(stdin_bytes)
            await proc.stdin.drain()
            proc.stdin.close()

        async def _read_stream(stream: asyncio.StreamReader, lines_buf: List[str], is_stdout: bool) -> None:
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
                    break
                line = raw.decode("utf-8", errors="replace").rstrip("\n")
                if is_stdout and line.startswith(_CHART_MARKER):
                    chart_b64 = line[len(_CHART_MARKER):].strip()
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
            try:
                await asyncio.wait_for(proc.wait(), timeout=2)
            except asyncio.TimeoutError:
                pass
            exit_code = -1

    except FileNotFoundError:
        error_msg = f"Runtime not found for language '{lang}'. Please install it."
        logger.error("[sandbox] %s", error_msg)
    except Exception as exc:
        error_msg = str(exc)
        logger.error("[sandbox] Subprocess error: %s", exc)
    finally:
        for p in (script_path, binary_path):
            try:
                os.remove(p)
            except OSError:
                pass
        if _owns_work_dir:
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

