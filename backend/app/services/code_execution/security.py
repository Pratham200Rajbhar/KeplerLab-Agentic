from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import List

_BLOCKED_MODULES: set[str] = {
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
]

_HARD_BLOCKED_CALL_RES = [re.compile(p) for p in _HARD_BLOCKED_CALLS]
_SOFT_BLOCKED_CALL_RES = [re.compile(p) for p in _SOFT_BLOCKED_CALLS]

_CHART_CAPTURE_SNIPPET = """
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as _plt_module
_original_show = _plt_module.show

def _capture_show():
    import io, base64
    buf = io.BytesIO()
    _plt_module.savefig(buf, format='png', dpi=100, bbox_inches='tight')
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

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        result.warnings.append(f"Syntax warning: {exc}")
        return result

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

def sanitize_code(code: str) -> str:
    code = code.strip()

    needs_capture = (
        "matplotlib" in code
        or "plt.show" in code
        or "pyplot" in code
    )
    if needs_capture:
        code = _CHART_CAPTURE_SNIPPET.strip() + "\n\n" + code

    return code
