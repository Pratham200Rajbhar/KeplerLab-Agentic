from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import List

from app.core.config import settings

_BLOCKED_MODULES: set[str] = {
    "os",
    "sys",
    "shutil",
    "subprocess",
    "socket",
    "requests",
    "urllib",
    "httpx",
    "aiohttp",
    "ftplib",
    "smtplib",
    "paramiko",
    "fabric",
    "pexpect",
    "ptyprocess",
    "ctypes",
    "cffi",
    "resource",
    "signal",
    "multiprocessing",
    "concurrent",
    "threading",
    "pickle",
    "shelve",
    "marshal",
    "pty",
    "tty",
    "termios",
    "fcntl",
    "grp",
    "pwd",
    "spwd",
    "crypt",
    "nis",
    "syslog",
    "mmap",
}

_HARD_BLOCKED_CALLS: List[str] = [
    r"\beval\s*\(",
    r"\bexec\s*\(",
    r"\bcompile\s*\(",
    r"\b__import__\s*\(",
    r"\bimportlib\.import_module\s*\(",
    r"\bos\.system\s*\(",
    r"\bos\.popen\s*\(",
    r"\bos\.exec",
    r"\bos\.spawn",
    r"\bos\.kill\s*\(",
    r"\bos\.killpg\s*\(",
    r"\bos\.fork\s*\(",
    r"\bos\.remove\s*\(",
    r"\bos\.unlink\s*\(",
    r"\bos\.rmdir\s*\(",
    r"\bshutil\.rmtree\s*\(",
]

_SOFT_BLOCKED_CALLS: List[str] = [
    r"\bos\.environ\b",
    r"\bos\.getenv\s*\(",
    r"\bos\.putenv\s*\(",
    r"\bos\.walk\s*\(",
    r"\bos\.listdir\s*\(",
    r"\bos\.makedirs\s*\(",
    r"\bos\.mkdir\s*\(",
    r"\bos\.rename\s*\(",
    r"\bshutil\b",
    r"\bopen\s*\(.*['\"]w['\"]",
    r"\bopen\s*\(.*['\"]a['\"]",
    r"\bopen\s*\(.*['\"]wb['\"]",
    r"\bopen\s*\(.*['\"]ab['\"]",
    r"\bopen\s*\(.*\.\./",
    r"\bpathlib\.Path\s*\(.*\.\./",
]

_HARD_BLOCKED_CALL_RES = [re.compile(p) for p in _HARD_BLOCKED_CALLS]
_SOFT_BLOCKED_CALL_RES = [re.compile(p) for p in _SOFT_BLOCKED_CALLS]

_CHART_CAPTURE_SNIPPET = """
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as _plt_module
_original_show = _plt_module.show
_kepler_chart_counter = 0

def _capture_show():
    import io, base64, os
    global _kepler_chart_counter
    buf = io.BytesIO()
    _plt_module.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode('utf-8')
    print(f"__CHART__:{encoded}")
    # Also save to file so agent artifact detection finds it
    _kepler_chart_counter += 1
    _fname = f'chart_output_{_kepler_chart_counter}.png'
    _plt_module.savefig(_fname, dpi=150, bbox_inches='tight')
    print(f"SAVED: {_fname}")
    _plt_module.close('all')

_plt_module.show = _capture_show
"""

_CHART_CAPTURE_SNIPPET_NOFILE = """
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as _plt_module
_original_show = _plt_module.show

def _capture_show():
    import io, base64
    buf = io.BytesIO()
    _plt_module.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode('utf-8')
    print(f"__CHART__:{encoded}")
    _plt_module.close('all')

_plt_module.show = _capture_show
"""

@dataclass
class ValidationResult:

    is_safe: bool = True
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

def validate_code(code: str) -> ValidationResult:
    result = ValidationResult()

    if bool(getattr(settings, "CODE_EXECUTION_FULL_ACCESS", False)):
        return result

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        result.warnings.append(f"Syntax warning: {exc}")
        return result

    max_nodes = 2000
    node_count = sum(1 for _ in ast.walk(tree))
    if node_count > max_nodes:
        result.violations.append(
            f"Code too complex for sandbox policy: AST nodes={node_count} > {max_nodes}"
        )
        result.is_safe = False

    max_function_body_stmts = 300

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module_name: str = ""
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name.split(".")[0]
                    if module_name in _BLOCKED_MODULES:
                        result.violations.append(
                            f"Blocked import: '{alias.name}'"
                        )
                        result.is_safe = False
            elif isinstance(node, ast.ImportFrom) and node.module:
                module_name = node.module.split(".")[0]
                if module_name in _BLOCKED_MODULES:
                    result.violations.append(
                        f"Blocked import: 'from {node.module} import ...'"
                    )
                    result.is_safe = False
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "open" and node.args:
                first = node.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    if first.value.startswith("/") or ".." in first.value.replace("\\", "/"):
                        result.violations.append(
                            f"Blocked file path access: {first.value!r}"
                        )
                        result.is_safe = False
        elif isinstance(node, ast.FunctionDef):
            if len(node.body) > max_function_body_stmts:
                result.warnings.append(
                    f"Large function '{node.name}' may timeout in sandbox ({len(node.body)} statements)"
                )

    for pattern in _HARD_BLOCKED_CALL_RES:
        for match in pattern.finditer(code):
            result.violations.append(
                f"Blocked dangerous pattern: {match.group()!r}"
            )
            result.is_safe = False

    for pattern in _SOFT_BLOCKED_CALL_RES:
        for match in pattern.finditer(code):
            result.warnings.append(
                f"Potentially dangerous pattern: {match.group()!r}"
            )

    return result

def sanitize_code(code: str, ensure_file_output: bool = False) -> str:
    """Sanitize generated code before sandbox execution.

    Args:
        code: Raw generated code.
        ensure_file_output: If True (agent mode), also replace bare plt.show()
            calls with savefig + close to guarantee chart files on disk.
    """
    code = code.strip()

    needs_capture = (
        "matplotlib" in code
        or "plt.show" in code
        or "pyplot" in code
    )
    if needs_capture:
        has_explicit_save = "savefig(" in code
        capture_snippet = _CHART_CAPTURE_SNIPPET_NOFILE if has_explicit_save else _CHART_CAPTURE_SNIPPET
        code = capture_snippet.strip() + "\n\n" + code

    # In agent mode, replace any remaining bare plt.show() calls (where the
    # programmer forgot to savefig) with explicit file saves.  The chart capture
    # snippet already saves to file, but this catches edge cases where show()
    # is called in unusual ways.
    if ensure_file_output and needs_capture:
        # Also ensure matplotlib doesn't try to open a display
        if "plt.ion()" in code:
            code = code.replace("plt.ion()", "plt.ioff()")

    # Always neutralize plotly .show() since it tries to open a browser.
    # Inject a monkey-patch that replaces show() with write_html() automatically.
    if "plotly" in code and ".show()" in code:
        _plotly_shim = (
            "import plotly.graph_objects as _pg\n"
            "_orig_show = _pg.Figure.show\n"
            "def _safe_show(self, *a, **kw):\n"
            "    import os, hashlib\n"
            "    name = 'plotly_' + hashlib.md5(str(id(self)).encode()).hexdigest()[:8] + '.html'\n"
            "    self.write_html(name)\n"
            "    print(f'SAVED: {name}')\n"
            "_pg.Figure.show = _safe_show\n"
        )
        code = _plotly_shim + code

    return code
