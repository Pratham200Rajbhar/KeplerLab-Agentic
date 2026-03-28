from __future__ import annotations

import asyncio
import json
import logging
import os
import resource
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SandboxRunResult:
    stdout: str
    stderr: str
    exit_code: int
    timed_out: bool
    elapsed_seconds: float
    files: List[str] = field(default_factory=list)
    error: Optional[str] = None


_OUTPUT_JSON_NAME = "_sandbox_result.json"


def _safe_decode(raw: bytes) -> str:
    if not raw:
        return ""
    return raw.decode("utf-8", errors="replace")


def _preexec_limits(memory_mb: int, cpu_seconds: int, fsize_mb: int):
    def _apply() -> None:
        mem_bytes = int(memory_mb) * 1024 * 1024
        fsize_bytes = int(fsize_mb) * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        resource.setrlimit(resource.RLIMIT_FSIZE, (fsize_bytes, fsize_bytes))
        resource.setrlimit(resource.RLIMIT_NPROC, (128, 128))
        resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))

    return _apply


def _write_wrapper_script(
    code: str,
    wrapper_path: str,
    output_dir: str,
    result_json_path: str,
) -> None:
    payload = {
        "code": code,
        "output_dir": output_dir,
        "result_json_path": result_json_path,
    }
    payload_json = json.dumps(payload)

    wrapper = f"""
import builtins
import io
import json
import os
import pathlib
import socket
import sys
import traceback

payload = json.loads({payload_json!r})
code = payload["code"]
output_dir = os.path.abspath(payload["output_dir"])
result_json_path = os.path.abspath(payload["result_json_path"])

os.makedirs(output_dir, exist_ok=True)
os.chdir(output_dir)
os.environ.setdefault("MPLCONFIGDIR", output_dir)
os.environ.setdefault("XDG_CACHE_HOME", output_dir)

def _is_within(path, root):
    root = os.path.abspath(root)
    path = os.path.abspath(path)
    return path == root or path.startswith(root + os.sep)

_allowed_read_roots = set()
for _p in [sys.prefix, sys.base_prefix] + [p for p in sys.path if p]:
    try:
        if isinstance(_p, str) and os.path.isabs(_p):
            _allowed_read_roots.add(os.path.abspath(_p))
    except Exception:
        pass

def _is_write_mode(mode):
    m = str(mode or "r")
    return any(ch in m for ch in ("w", "a", "x", "+"))

def _resolve_user_path(path_like, mode="r"):
    if isinstance(path_like, int):
        return None
    p = os.fspath(path_like)
    if os.path.isabs(p):
        resolved = os.path.abspath(p)
    else:
        resolved = os.path.abspath(os.path.join(output_dir, p))

    if _is_write_mode(mode):
        if not _is_within(resolved, output_dir):
            raise PermissionError("Write access outside sandbox output directory is not allowed")
        return resolved

    if _is_within(resolved, output_dir):
        return resolved

    if any(_is_within(resolved, root) for root in _allowed_read_roots):
        return resolved

    raise PermissionError("Read access outside allowed sandbox paths is not allowed")
    return resolved

_orig_open = builtins.open
def _safe_open(file, mode="r", *args, **kwargs):
    resolved = _resolve_user_path(file, mode=mode)
    if resolved is None:
        raise PermissionError("Direct file descriptor access is not allowed")
    return _orig_open(resolved, mode, *args, **kwargs)

builtins.open = _safe_open
io.open = _safe_open

def _blocked_network(*args, **kwargs):
    raise PermissionError("Network is disabled in sandbox")

# Keep socket class intact (ssl imports subclass socket.socket).
# Only block outbound connection APIs.
socket.create_connection = _blocked_network

def _blocked_connect(self, *args, **kwargs):
    raise PermissionError("Network is disabled in sandbox")

def _blocked_connect_ex(self, *args, **kwargs):
    raise PermissionError("Network is disabled in sandbox")

socket.socket.connect = _blocked_connect
socket.socket.connect_ex = _blocked_connect_ex

stdout_buf = io.StringIO()
stderr_buf = io.StringIO()
exit_code = 0

with io.StringIO() as _stdout_proxy, io.StringIO() as _stderr_proxy:
    try:
        import contextlib
        with contextlib.redirect_stdout(_stdout_proxy), contextlib.redirect_stderr(_stderr_proxy):
            compiled = compile(code, "<sandbox>", "exec")
            glb = {{"__name__": "__main__", "__file__": "<sandbox>"}}
            exec(compiled, glb, glb)
    except SystemExit as se:
        exit_code = int(se.code) if isinstance(se.code, int) else 1
    except Exception:
        exit_code = 1
        traceback.print_exc(file=_stderr_proxy)
    finally:
        stdout_buf.write(_stdout_proxy.getvalue())
        stderr_buf.write(_stderr_proxy.getvalue())

files = []
for root, _, fnames in os.walk(output_dir):
    for fname in fnames:
        if fname.startswith("."):
            continue
        if fname == os.path.basename(result_json_path):
            continue
        fpath = os.path.join(root, fname)
        if os.path.isfile(fpath) and os.path.getsize(fpath) > 0:
            files.append(os.path.relpath(fpath, output_dir))

result = {{
    "stdout": stdout_buf.getvalue(),
    "stderr": stderr_buf.getvalue(),
    "exit_code": exit_code,
    "files": sorted(files),
}}

with _orig_open(result_json_path, "w", encoding="utf-8") as fh:
    json.dump(result, fh)

raise SystemExit(exit_code)
"""

    with open(wrapper_path, "w", encoding="utf-8") as fh:
        fh.write(wrapper)


async def _run_local_subprocess(
    code: str,
    timeout: int,
    memory_mb: int,
    cpu_seconds: int,
    max_file_mb: int,
    work_dir: Optional[str] = None,
) -> SandboxRunResult:
    t0 = time.perf_counter()
    owns_work_dir = work_dir is None
    work_dir = os.path.abspath(work_dir) if work_dir else tempfile.mkdtemp(prefix="kepler_sandbox_local_")
    os.makedirs(work_dir, exist_ok=True)
    output_dir = work_dir
    wrapper_path = os.path.join(work_dir, "_sandbox_wrapper.py")
    result_json = os.path.join(output_dir, _OUTPUT_JSON_NAME)
    _write_wrapper_script(code, wrapper_path, output_dir, result_json)

    timed_out = False
    stdout = ""
    stderr = ""
    exit_code = -1
    files: List[str] = []

    try:
        child_env = os.environ.copy()
        child_env.update({
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
            "TOKENIZERS_PARALLELISM": "false",
        })

        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-u",
            wrapper_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=work_dir,
            preexec_fn=_preexec_limits(memory_mb, cpu_seconds, max_file_mb),
            env=child_env,
        )
        try:
            raw_out, raw_err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            timed_out = True
            proc.kill()
            raw_out, raw_err = await proc.communicate()

        stdout = _safe_decode(raw_out)
        stderr = _safe_decode(raw_err)
        exit_code = proc.returncode if proc.returncode is not None else -1

        if os.path.isfile(result_json):
            try:
                with open(result_json, "r", encoding="utf-8") as fh:
                    result_payload = json.load(fh)
                stdout = result_payload.get("stdout", stdout)
                stderr = result_payload.get("stderr", stderr)
                exit_code = int(result_payload.get("exit_code", exit_code))
                files = [str(x) for x in result_payload.get("files", [])]
            except Exception as exc:
                logger.warning("Failed to parse sandbox result json: %s", exc)
    except Exception as exc:
        return SandboxRunResult(
            stdout="",
            stderr="",
            exit_code=-1,
            timed_out=False,
            elapsed_seconds=round(time.perf_counter() - t0, 3),
            files=[],
            error=str(exc),
        )
    finally:
        try:
            if os.path.exists(wrapper_path):
                os.remove(wrapper_path)
        except OSError:
            pass
        try:
            if os.path.exists(result_json):
                os.remove(result_json)
        except OSError:
            pass
        if owns_work_dir:
            shutil.rmtree(work_dir, ignore_errors=True)

    return SandboxRunResult(
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        timed_out=timed_out,
        elapsed_seconds=round(time.perf_counter() - t0, 3),
        files=files,
        error=None,
    )


async def _run_in_docker(
    code: str,
    timeout: int,
    memory_mb: int,
    cpu_limit: float,
    max_file_mb: int,
    work_dir: Optional[str] = None,
) -> SandboxRunResult:
    t0 = time.perf_counter()
    owns_work_dir = work_dir is None
    host_workdir = os.path.abspath(work_dir) if work_dir else tempfile.mkdtemp(prefix="kepler_sandbox_docker_")
    os.makedirs(host_workdir, exist_ok=True)
    wrapper_host = os.path.join(host_workdir, "_sandbox_wrapper.py")
    result_json = os.path.join(host_workdir, _OUTPUT_JSON_NAME)
    _write_wrapper_script(code, wrapper_host, "/workspace_rw", "/workspace_rw/_sandbox_result.json")

    cmd = [
        "docker", "run", "--rm",
        "--network", "none",
        "--cpus", str(cpu_limit),
        "--memory", f"{int(memory_mb)}m",
        "--pids-limit", "64",
        "--read-only",
        "--tmpfs", "/tmp:rw,size=128m",
        "-v", f"{host_workdir}:/workspace_rw:rw",
        settings.WORKSPACE_CONTAINER_IMAGE,
        "python",
        "/workspace_rw/_sandbox_wrapper.py",
    ]

    timed_out = False
    stdout = ""
    stderr = ""
    exit_code = -1
    files: List[str] = []

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=host_workdir,
        )
        try:
            raw_out, raw_err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            timed_out = True
            proc.kill()
            raw_out, raw_err = await proc.communicate()

        stdout = _safe_decode(raw_out)
        stderr = _safe_decode(raw_err)
        exit_code = proc.returncode if proc.returncode is not None else -1

        if os.path.isfile(result_json):
            with open(result_json, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            stdout = payload.get("stdout", stdout)
            stderr = payload.get("stderr", stderr)
            exit_code = int(payload.get("exit_code", exit_code))
            files = [str(x) for x in payload.get("files", [])]
    except FileNotFoundError:
        raise RuntimeError("docker executable not available")
    finally:
        try:
            if os.path.exists(wrapper_host):
                os.remove(wrapper_host)
        except OSError:
            pass
        try:
            if os.path.exists(result_json):
                os.remove(result_json)
        except OSError:
            pass
        if owns_work_dir:
            shutil.rmtree(host_workdir, ignore_errors=True)

    return SandboxRunResult(
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        timed_out=timed_out,
        elapsed_seconds=round(time.perf_counter() - t0, 3),
        files=files,
        error=None,
    )


async def execute_python_sandboxed(
    code: str,
    *,
    timeout: int,
    prefer_docker: bool = True,
    work_dir: Optional[str] = None,
) -> SandboxRunResult:
    memory_mb = int(getattr(settings, "SANDBOX_MEMORY_MB", 512))
    cpu_seconds = int(getattr(settings, "SANDBOX_CPU_SECONDS", min(timeout, 10)))
    max_file_mb = int(getattr(settings, "SANDBOX_MAX_FILE_MB", 20))
    cpu_limit = float(getattr(settings, "SANDBOX_CPU_LIMIT", 1.0))

    if prefer_docker:
        try:
            return await _run_in_docker(
                code=code,
                timeout=timeout,
                memory_mb=memory_mb,
                cpu_limit=cpu_limit,
                max_file_mb=max_file_mb,
                work_dir=work_dir,
            )
        except Exception as exc:
            logger.warning("Docker sandbox unavailable; falling back to local isolation: %s", exc)

    return await _run_local_subprocess(
        code=code,
        timeout=timeout,
        memory_mb=memory_mb,
        cpu_seconds=cpu_seconds,
        max_file_mb=max_file_mb,
        work_dir=work_dir,
    )
