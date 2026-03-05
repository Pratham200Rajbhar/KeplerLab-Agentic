#!/usr/bin/env python3
"""
=============================================================================
 KeplerLab — Agentic Pipeline End-to-End Test Suite
=============================================================================
 Tests ALL four agentic modes:  /agent, /code, /web, /research
 plus the Phase 2 execute-code endpoint.

 Resources: CSV files in the /test folder
 Output:    /test/output/ folder

 Usage:
   python test/test_agentic_pipeline.py
   python test/test_agentic_pipeline.py --base http://localhost:8001
   python test/test_agentic_pipeline.py --skip-slow

 Requirements:
   pip install httpx rich
=============================================================================
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent           # /test
PROJECT_ROOT = SCRIPT_DIR.parent                        # /New KeplerLab
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# CSV test resources in /test
CSV_FILES = sorted(SCRIPT_DIR.glob("*.csv"))

# ── Config ────────────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:8000"
TIMEOUT = 180       # per request
POLL_TIMEOUT = 300  # for async jobs
POLL_INTERVAL = 4   # seconds between polls

_RUN_ID = uuid.uuid4().hex[:8]
TEST_EMAIL = f"agenttest_{_RUN_ID}@example.com"
TEST_USERNAME = f"agenttest_{_RUN_ID}"
TEST_PASSWORD = "AgentTest1!"

# ── Colour helpers ────────────────────────────────────────────────────────────
def _green(s): return f"\033[92m{s}\033[0m"
def _red(s):   return f"\033[91m{s}\033[0m"
def _yellow(s):return f"\033[93m{s}\033[0m"
def _bold(s):  return f"\033[1m{s}\033[0m"
def _cyan(s):  return f"\033[96m{s}\033[0m"

# ── Result tracking ───────────────────────────────────────────────────────────
@dataclass
class TestResult:
    name: str
    passed: bool
    detail: str = ""
    duration: float = 0.0
    section: str = ""

results: list[TestResult] = []
state: dict = {}


def log(msg: str, level: str = "INFO"):
    prefix = {"INFO": "ℹ", "PASS": "✔", "FAIL": "✘", "WARN": "⚠", "HEAD": "▶"}.get(level, " ")
    colour = {"PASS": _green, "FAIL": _red, "WARN": _yellow, "HEAD": _bold}.get(level, str)
    print(f"  {colour(prefix)} {msg}")


def section(title: str):
    print(f"\n{'='*72}")
    print(f"  {_bold(title)}")
    print(f"{'='*72}")


def record(name: str, passed: bool, detail: str = "", duration: float = 0.0, sect: str = ""):
    results.append(TestResult(name, passed, detail, duration, sect))
    level = "PASS" if passed else "FAIL"
    det = f" — {detail}" if detail else ""
    log(f"{name}{det} ({duration:.2f}s)", level)


def check_response(name: str, resp, expected: int = 200, t0: float = 0.0, sect: str = "") -> bool:
    dur = time.time() - t0
    if resp.status_code == expected:
        record(name, True, f"HTTP {resp.status_code}", dur, sect)
        return True
    try:
        body = resp.json()
    except Exception:
        body = resp.text[:300]
    record(name, False, f"Expected {expected}, got {resp.status_code}: {body}", dur, sect)
    return False


# ── HTTP Client ───────────────────────────────────────────────────────────────
def make_client(base_url: str = BASE_URL, timeout: int = TIMEOUT) -> httpx.Client:
    headers = {"Content-Type": "application/json"}
    tok = state.get("access_token")
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    return httpx.Client(
        base_url=base_url,
        headers=headers,
        timeout=timeout,
        cookies=state.get("cookies", {}),
        follow_redirects=True,
    )


def make_upload_client(base_url: str = BASE_URL, timeout: int = TIMEOUT) -> httpx.Client:
    """Client WITHOUT Content-Type (httpx sets multipart boundary)."""
    headers = {}
    tok = state.get("access_token")
    if tok:
        headers["Authorization"] = f"Bearer {tok}"
    return httpx.Client(
        base_url=base_url,
        headers=headers,
        timeout=timeout,
        cookies=state.get("cookies", {}),
        follow_redirects=True,
    )


# ── SSE Stream Parser ────────────────────────────────────────────────────────
def parse_sse_response(resp: httpx.Response) -> List[Dict[str, Any]]:
    """Parse SSE text into [{event, data}, ...] events."""
    events = []
    current_event = "message"
    text = resp.text if hasattr(resp, "text") else str(resp)

    for line in text.split("\n"):
        line = line.rstrip()
        if line.startswith("event: "):
            current_event = line[7:]
        elif line.startswith("data: "):
            raw = line[6:]
            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                data = raw
            events.append({"event": current_event, "data": data})
            current_event = "message"
        elif line == "":
            current_event = "message"

    return events


def find_events(events: list, event_type: str) -> list:
    """Filter events by type."""
    return [e for e in events if e["event"] == event_type]


def concat_tokens(events: list) -> str:
    """Join all token event contents."""
    parts = []
    for e in events:
        if e["event"] == "token":
            content = e["data"].get("content", "") if isinstance(e["data"], dict) else ""
            parts.append(content)
    return "".join(parts)


def save_output(filename: str, content: str, prefix: str = ""):
    """Write content to test/output/."""
    path = OUTPUT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        if prefix:
            f.write(prefix + "\n\n")
        f.write(content)
    log(f"Output saved: {path.relative_to(PROJECT_ROOT)}")
    return path


def save_json(filename: str, data: Any):
    """Write JSON to test/output/."""
    path = OUTPUT_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
    log(f"JSON saved: {path.relative_to(PROJECT_ROOT)}")
    return path


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 0 — Preflight
# ══════════════════════════════════════════════════════════════════════════════
def test_preflight(base_url: str):
    section("SECTION 0 — Preflight Checks")

    # 0.1 CSV resources exist
    t0 = time.time()
    record("CSV test files exist", len(CSV_FILES) > 0,
           f"Found {len(CSV_FILES)}: {[f.name for f in CSV_FILES]}", time.time() - t0, "preflight")
    for f in CSV_FILES:
        log(f"  → {f.name} ({f.stat().st_size:,} bytes)")

    # 0.2 Output dir writable
    t0 = time.time()
    test_file = OUTPUT_DIR / ".write_test"
    try:
        test_file.write_text("ok")
        test_file.unlink()
        record("Output directory writable", True, str(OUTPUT_DIR), time.time() - t0, "preflight")
    except Exception as e:
        record("Output directory writable", False, str(e), time.time() - t0, "preflight")

    # 0.3 Backend reachable
    t0 = time.time()
    try:
        with httpx.Client(timeout=10) as c:
            r = c.get(f"{base_url}/docs")
        reachable = r.status_code in (200, 301, 302)
        record("Backend reachable", reachable, f"HTTP {r.status_code}", time.time() - t0, "preflight")
    except Exception as e:
        record("Backend reachable", False, str(e), time.time() - t0, "preflight")
        print(_red("\n  FATAL: Backend is not running. Start it first.\n"))
        sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 1 — Auth + Notebook + Upload CSV
# ══════════════════════════════════════════════════════════════════════════════
def test_setup(base_url: str):
    section("SECTION 1 — Auth, Notebook, CSV Upload")

    # 1.1 Signup
    t0 = time.time()
    with httpx.Client(base_url=base_url, timeout=TIMEOUT) as c:
        r = c.post("/auth/signup", json={
            "email": TEST_EMAIL,
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
        })
    if r.status_code == 201:
        record("Signup", True, f"Created {TEST_EMAIL}", time.time() - t0, "setup")
    else:
        record("Signup", r.status_code in (400, 409), f"Exists or error: HTTP {r.status_code}", time.time() - t0, "setup")

    # 1.2 Login
    t0 = time.time()
    with httpx.Client(base_url=base_url, timeout=TIMEOUT) as c:
        r = c.post("/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    if not check_response("Login", r, 200, t0, "setup"):
        print(_red("  FATAL: Cannot login. Aborting."))
        sys.exit(1)
    state["access_token"] = r.json().get("access_token", "")
    state["cookies"] = dict(r.cookies)

    # 1.3 Create notebook
    t0 = time.time()
    with make_client(base_url) as c:
        r = c.post("/notebooks", json={
            "name": f"Agentic Test {_RUN_ID}",
            "description": "Testing agentic pipeline modes",
        })
    if check_response("Create notebook", r, 201, t0, "setup"):
        state["notebook_id"] = r.json()["id"]
        log(f"  Notebook: {state['notebook_id']}")

    nb_id = state.get("notebook_id")
    if not nb_id:
        print(_red("  FATAL: No notebook. Aborting."))
        sys.exit(1)

    # 1.4 Upload CSV files
    state["material_ids"] = []
    for csv_path in CSV_FILES:
        t0 = time.time()
        with open(csv_path, "rb") as fh:
            with make_upload_client(base_url) as c:
                r = c.post(
                    "/upload",
                    data={"notebook_id": nb_id},
                    files={"file": (csv_path.name, fh, "text/csv")},
                )
        if check_response(f"Upload {csv_path.name}", r, 202, t0, "setup"):
            mid = r.json().get("material_id")
            state["material_ids"].append(mid)
            log(f"  material_id={mid}")
        else:
            log(f"  Upload failed for {csv_path.name}", "WARN")

    if not state["material_ids"]:
        print(_red("  FATAL: No materials uploaded. Aborting."))
        sys.exit(1)

    # 1.5 Wait for materials to be processed
    log(f"Waiting for {len(state['material_ids'])} materials to complete processing...")
    deadline = time.time() + POLL_TIMEOUT
    completed = set()
    while time.time() < deadline and len(completed) < len(state["material_ids"]):
        time.sleep(POLL_INTERVAL)
        with make_client(base_url) as c:
            r = c.get(f"/materials?notebook_id={nb_id}")
        if r.status_code == 200:
            mats = r.json()
            for m in mats:
                if m["id"] in state["material_ids"]:
                    if m["status"] == "completed":
                        completed.add(m["id"])
                    elif m["status"] == "failed":
                        log(f"  Material {m['id']} ({m.get('title','?')}) FAILED", "FAIL")
                        completed.add(m["id"])  # don't wait forever
            log(f"  {len(completed)}/{len(state['material_ids'])} done", "INFO")

    state["material_ready"] = len(completed) == len(state["material_ids"])
    record(
        "Materials processed",
        state["material_ready"],
        f"{len(completed)}/{len(state['material_ids'])}",
        sect="setup",
    )

    # 1.6 Create chat session
    t0 = time.time()
    with make_client(base_url) as c:
        r = c.post("/chat/sessions", json={"notebook_id": nb_id, "title": f"Agent Test {_RUN_ID}"})
    if check_response("Create chat session", r, 200, t0, "setup"):
        state["session_id"] = r.json().get("session_id") or r.json().get("id")
        log(f"  Session: {state['session_id']}")


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 2 — /agent mode (full agentic pipeline)
# ══════════════════════════════════════════════════════════════════════════════
def test_agent_mode(base_url: str, skip_slow: bool = False):
    section("SECTION 2 — /agent Mode (Autonomous Agent Pipeline)")
    if skip_slow:
        log("Skipping (--skip-slow)", "WARN")
        return
    if not state.get("material_ready"):
        log("Materials not ready — skipping", "WARN")
        return

    nb_id = state["notebook_id"]
    mat_ids = state["material_ids"]
    session_id = state.get("session_id")

    # 2.1 Agent mode: analyze data across CSVs
    t0 = time.time()
    with make_client(base_url, timeout=300) as c:
        r = c.post("/chat", json={
            "material_ids": mat_ids,
            "notebook_id": nb_id,
            "session_id": session_id,
            "message": "Analyze the car data CSV. What are the key statistics? Show the top 5 most expensive cars.",
            "stream": True,
            "intent_override": "AGENT",
        })
    dur = time.time() - t0
    record("/agent — HTTP request", r.status_code == 200,
           f"HTTP {r.status_code} ({dur:.1f}s)", dur, "agent")

    if r.status_code == 200:
        events = parse_sse_response(r)
        save_json("agent_mode_events.json", events)

        # Check for key SSE events
        agent_starts = find_events(events, "agent_start")
        tool_starts = find_events(events, "tool_start")
        tool_results = find_events(events, "tool_result")
        tokens = find_events(events, "token")
        dones = find_events(events, "done")
        errors = find_events(events, "error")
        artifacts = find_events(events, "artifact")

        record("/agent — agent_start event received", len(agent_starts) > 0,
               f"count={len(agent_starts)}", sect="agent")
        record("/agent — tool executions happened", len(tool_results) > 0,
               f"starts={len(tool_starts)} results={len(tool_results)}", sect="agent")
        record("/agent — tokens streamed", len(tokens) > 0,
               f"token_events={len(tokens)}", sect="agent")
        record("/agent — done event received", len(dones) > 0,
               f"count={len(dones)}", sect="agent")
        record("/agent — no errors", len(errors) == 0,
               f"errors={[e['data'] for e in errors]}" if errors else "clean", sect="agent")

        # Aggregate token content
        full_response = concat_tokens(events)
        if full_response:
            save_output("agent_mode_response.md", full_response,
                        "# /agent Mode Response\n\nQuery: Analyze the car data CSV")
            record("/agent — response content non-empty", True,
                   f"length={len(full_response)}", sect="agent")
        else:
            record("/agent — response content non-empty", False, "empty", sect="agent")

        # Summary of tools used
        tools_used = [tr["data"].get("tool", "?") for tr in tool_results if isinstance(tr["data"], dict)]
        log(f"  Tools used: {tools_used}")
        if artifacts:
            log(f"  Artifacts: {len(artifacts)}")
            for art_ev in artifacts:
                art_data = art_ev["data"] if isinstance(art_ev["data"], dict) else {}
                log(f"    → {art_data.get('filename', '?')} ({art_data.get('display_type', '?')})")

    # 2.2 Agent mode: simpler question (should use rag_tool)
    t0 = time.time()
    with make_client(base_url, timeout=300) as c:
        r2 = c.post("/chat", json={
            "material_ids": mat_ids,
            "notebook_id": nb_id,
            "session_id": session_id,
            "message": "Summarize the uploaded datasets in 3 sentences.",
            "stream": True,
            "intent_override": "AGENT",
        })
    dur = time.time() - t0
    if r2.status_code == 200:
        events2 = parse_sse_response(r2)
        resp2 = concat_tokens(events2)
        record("/agent — simple query works", len(resp2) > 10,
               f"response_length={len(resp2)}", dur, "agent")
        save_output("agent_mode_simple.md", resp2, "# /agent Simple Query")
    else:
        record("/agent — simple query works", False,
               f"HTTP {r2.status_code}", dur, "agent")


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 3 — /code mode (two-phase: generate → execute)
# ══════════════════════════════════════════════════════════════════════════════
def test_code_mode(base_url: str, skip_slow: bool = False):
    section("SECTION 3 — /code Mode (Two-Phase Code Execution)")
    if skip_slow:
        log("Skipping (--skip-slow)", "WARN")
        return
    if not state.get("material_ready"):
        log("Materials not ready — skipping", "WARN")
        return

    nb_id = state["notebook_id"]
    mat_ids = state["material_ids"]
    session_id = state.get("session_id")

    # 3.1 Phase 1: Generate code via /chat with intent_override=CODE_EXECUTION
    t0 = time.time()
    with make_client(base_url, timeout=300) as c:
        r = c.post("/chat", json={
            "material_ids": mat_ids,
            "notebook_id": nb_id,
            "session_id": session_id,
            "message": "Write Python code to load the car data CSV and show the average selling price by fuel type. Save a bar chart as chart.png.",
            "stream": True,
            "intent_override": "CODE_EXECUTION",
        })
    dur = time.time() - t0
    record("/code Phase 1 — HTTP request", r.status_code == 200,
           f"HTTP {r.status_code} ({dur:.1f}s)", dur, "code")

    generated_code = None
    if r.status_code == 200:
        events = parse_sse_response(r)
        save_json("code_mode_phase1_events.json", events)

        code_blocks = find_events(events, "code_block")
        done_gens = find_events(events, "done_generation")
        tokens = find_events(events, "token")
        errors = find_events(events, "error")

        # Look for code in code_block or done_generation events
        if code_blocks:
            generated_code = code_blocks[0]["data"].get("code", "") if isinstance(code_blocks[0]["data"], dict) else ""
            record("/code Phase 1 — code_block event", True,
                   f"code_length={len(generated_code)}", sect="code")
        elif done_gens:
            generated_code = done_gens[0]["data"].get("code", "") if isinstance(done_gens[0]["data"], dict) else ""
            record("/code Phase 1 — done_generation event", True,
                   f"code_length={len(generated_code)}", sect="code")
        elif tokens:
            # Code might be in streamed tokens (wrapped in markdown fences)
            full_text = concat_tokens(events)
            import re
            m = re.search(r"```python\n(.*?)```", full_text, re.DOTALL)
            if m:
                generated_code = m.group(1).strip()
                record("/code Phase 1 — code from tokens", True,
                       f"code_length={len(generated_code)}", sect="code")
            else:
                record("/code Phase 1 — code extracted", False,
                       "no code_block/done_generation event or python fence", sect="code")
        else:
            record("/code Phase 1 — code generated", False, "no events", sect="code")

        record("/code Phase 1 — no errors", len(errors) == 0,
               f"errors={errors}" if errors else "clean", sect="code")

        if generated_code:
            save_output("code_mode_generated.py", generated_code,
                        "# Generated by /code Phase 1")
            log(f"  Code preview: {generated_code[:120]}...")

    # 3.2 Phase 2: Execute code via /agent/execute-code
    if generated_code:
        t0 = time.time()
        with make_client(base_url, timeout=120) as c:
            r2 = c.post("/agent/execute-code", json={
                "code": generated_code,
                "notebook_id": nb_id,
                "session_id": session_id,
                "timeout": 30,
            })
        dur = time.time() - t0
        record("/code Phase 2 — execute-code HTTP", r2.status_code == 200,
               f"HTTP {r2.status_code} ({dur:.1f}s)", dur, "code")

        if r2.status_code == 200:
            exec_events = parse_sse_response(r2)
            save_json("code_mode_phase2_events.json", exec_events)

            exec_starts = find_events(exec_events, "execution_start")
            exec_dones = find_events(exec_events, "execution_done")
            exec_blocked = find_events(exec_events, "execution_blocked")
            exec_artifacts = find_events(exec_events, "artifact")
            exec_repairs = find_events(exec_events, "repair_suggestion")
            exec_errors = find_events(exec_events, "error")

            record("/code Phase 2 — execution_start", len(exec_starts) > 0,
                   f"count={len(exec_starts)}", sect="code")
            record("/code Phase 2 — execution_done", len(exec_dones) > 0,
                   f"count={len(exec_dones)}", sect="code")
            record("/code Phase 2 — no block", len(exec_blocked) == 0,
                   f"blocked={exec_blocked}" if exec_blocked else "clean", sect="code")

            if exec_dones:
                exit_code = exec_dones[0]["data"].get("exit_code", -1) if isinstance(exec_dones[0]["data"], dict) else -1
                needs_rerun = exec_dones[0]["data"].get("needs_rerun", False) if isinstance(exec_dones[0]["data"], dict) else False
                # exit_code=0 is ideal, but exit_code!=0 + repair suggestion is also valid
                ok = exit_code == 0 or (exit_code != 0 and len(exec_repairs) > 0)
                record("/code Phase 2 — execution completed", ok,
                       f"exit_code={exit_code}, repairs={len(exec_repairs)}, needs_rerun={needs_rerun}", sect="code")

            if exec_artifacts:
                log(f"  Phase 2 artifacts: {len(exec_artifacts)}")
                for art in exec_artifacts:
                    art_data = art["data"] if isinstance(art["data"], dict) else {}
                    log(f"    → {art_data.get('filename', '?')} ({art_data.get('display_type', '?')})")

            if exec_repairs:
                log(f"  Repair suggestions: {len(exec_repairs)}")

    # 3.3 Direct code execution (simple test)
    t0 = time.time()
    simple_code = "import sys\nprint(f'Python {sys.version}')\nprint('2+2 =', 2+2)"
    with make_client(base_url, timeout=60) as c:
        r3 = c.post("/agent/execute-code", json={
            "code": simple_code,
            "notebook_id": nb_id,
            "timeout": 15,
        })
    dur = time.time() - t0
    record("/agent/execute-code — simple code", r3.status_code == 200,
           f"HTTP {r3.status_code} ({dur:.1f}s)", dur, "code")
    if r3.status_code == 200:
        simple_events = parse_sse_response(r3)
        exec_d = find_events(simple_events, "execution_done")
        if exec_d:
            ec = exec_d[0]["data"].get("exit_code", -1) if isinstance(exec_d[0]["data"], dict) else -1
            record("/agent/execute-code — simple exit_code=0", ec == 0,
                   f"exit_code={ec}", sect="code")

    # 3.4 Security: blocked code (os.system is a hard violation)
    t0 = time.time()
    with make_client(base_url, timeout=30) as c:
        r4 = c.post("/agent/execute-code", json={
            "code": "import os\nos.system('rm -rf /')",
            "notebook_id": nb_id,
            "timeout": 10,
        })
    dur = time.time() - t0
    if r4.status_code == 200:
        blocked_events = parse_sse_response(r4)
        blocked = find_events(blocked_events, "execution_blocked")
        exec_d4 = find_events(blocked_events, "execution_done")
        # Blocked is ideal; also accept if execution ran but failed (code is in sandbox)
        code_was_stopped = len(blocked) > 0 or (
            exec_d4 and isinstance(exec_d4[0]["data"], dict) and exec_d4[0]["data"].get("exit_code", 0) != 0
        )
        record("/agent/execute-code — dangerous code handled", code_was_stopped,
               f"blocked={len(blocked)}, exec_done={len(exec_d4)}", dur, "code")
    else:
        record("/agent/execute-code — dangerous code rejected", r4.status_code in (400, 422),
               f"HTTP {r4.status_code}", dur, "code")

    # 3.5 Validation: empty code
    t0 = time.time()
    with make_client(base_url, timeout=15) as c:
        r5 = c.post("/agent/execute-code", json={"code": "", "notebook_id": nb_id})
    record("/agent/execute-code — empty code → 422", r5.status_code == 422,
           f"HTTP {r5.status_code}", time.time() - t0, "code")


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 4 — /web mode (search + scrape + synthesize)
# ══════════════════════════════════════════════════════════════════════════════
def test_web_mode(base_url: str, skip_slow: bool = False):
    section("SECTION 4 — /web Mode (Quick Web Search)")
    if skip_slow:
        log("Skipping (--skip-slow)", "WARN")
        return
    if not state.get("material_ready"):
        log("Materials not ready — skipping", "WARN")
        return

    nb_id = state["notebook_id"]
    mat_ids = state["material_ids"]
    session_id = state.get("session_id")

    # 4.1 Web search
    t0 = time.time()
    with make_client(base_url, timeout=300) as c:
        r = c.post("/chat", json={
            "material_ids": mat_ids,
            "notebook_id": nb_id,
            "session_id": session_id,
            "message": "What are the latest trends in electric vehicle pricing in 2025?",
            "stream": True,
            "intent_override": "WEB_SEARCH",
        })
    dur = time.time() - t0
    record("/web — HTTP request", r.status_code == 200,
           f"HTTP {r.status_code} ({dur:.1f}s)", dur, "web")

    if r.status_code == 200:
        events = parse_sse_response(r)
        save_json("web_mode_events.json", events)

        web_starts = find_events(events, "web_start")
        web_scraping = find_events(events, "web_scraping")
        web_sources = find_events(events, "web_sources")
        tokens = find_events(events, "token")
        dones = find_events(events, "done")
        errors = find_events(events, "error")

        record("/web — web_start event", len(web_starts) > 0,
               f"count={len(web_starts)}", sect="web")
        record("/web — tokens streamed", len(tokens) > 0,
               f"count={len(tokens)}", sect="web")
        record("/web — web_sources received", len(web_sources) > 0,
               f"count={len(web_sources)}", sect="web")
        record("/web — done event", len(dones) > 0,
               f"count={len(dones)}", sect="web")
        record("/web — no errors", len(errors) == 0,
               f"errors={errors}" if errors else "clean", sect="web")

        full_response = concat_tokens(events)
        if full_response:
            save_output("web_mode_response.md", full_response,
                        "# /web Mode Response\n\nQuery: EV pricing trends 2025")
            record("/web — response content", True,
                   f"length={len(full_response)}", sect="web")

        if web_sources:
            src_data = web_sources[0]["data"] if isinstance(web_sources[0]["data"], dict) else {}
            sources = src_data.get("sources", [])
            log(f"  Sources returned: {len(sources)}")
            for s in sources[:5]:
                if isinstance(s, dict):
                    log(f"    → {s.get('title', '?')[:60]} ({s.get('domain', '?')})")
            save_json("web_mode_sources.json", sources)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 5 — /research mode (deep iterative research)
# ══════════════════════════════════════════════════════════════════════════════
def test_research_mode(base_url: str, skip_slow: bool = False):
    section("SECTION 5 — /research Mode (Deep Iterative Research)")
    if skip_slow:
        log("Skipping (--skip-slow)", "WARN")
        return
    if not state.get("material_ready"):
        log("Materials not ready — skipping", "WARN")
        return

    nb_id = state["notebook_id"]
    mat_ids = state["material_ids"]
    session_id = state.get("session_id")

    # 5.1 Research query
    t0 = time.time()
    with make_client(base_url, timeout=600) as c:
        r = c.post("/chat", json={
            "material_ids": mat_ids,
            "notebook_id": nb_id,
            "session_id": session_id,
            "message": "Do a comprehensive research on factors affecting used car prices including depreciation curves, mileage impact, and brand value retention.",
            "stream": True,
            "intent_override": "WEB_RESEARCH",
        })
    dur = time.time() - t0
    record("/research — HTTP request", r.status_code == 200,
           f"HTTP {r.status_code} ({dur:.1f}s)", dur, "research")

    if r.status_code == 200:
        events = parse_sse_response(r)
        save_json("research_mode_events.json", events)

        research_starts = find_events(events, "research_start")
        research_phases = find_events(events, "research_phase")
        research_sources = find_events(events, "research_source")
        citations_ev = find_events(events, "citations")
        tokens = find_events(events, "token")
        dones = find_events(events, "done")
        errors = find_events(events, "error")

        record("/research — research_start event", len(research_starts) > 0,
               f"count={len(research_starts)}", sect="research")
        record("/research — research_phase events", len(research_phases) > 0,
               f"count={len(research_phases)}", sect="research")
        record("/research — sources found", len(research_sources) > 0,
               f"count={len(research_sources)}", sect="research")
        record("/research — tokens streamed", len(tokens) > 0,
               f"count={len(tokens)}", sect="research")
        record("/research — done event", len(dones) > 0,
               f"count={len(dones)}", sect="research")
        record("/research — no errors", len(errors) == 0,
               f"errors={[e['data'] for e in errors]}" if errors else "clean", sect="research")

        # Analyze phases
        phases = [p["data"] for p in research_phases if isinstance(p["data"], dict)]
        unique_phases = set(p.get("phase", "?") for p in phases)
        iterations = set(p.get("iteration", 0) for p in phases if p.get("iteration"))
        log(f"  Phases seen: {unique_phases}")
        log(f"  Iterations seen: {iterations}")

        full_response = concat_tokens(events)
        if full_response:
            save_output("research_mode_report.md", full_response,
                        "# /research Mode Report\n\nQuery: Used car price factors")
            record("/research — report content", True,
                   f"length={len(full_response)}", sect="research")

        if citations_ev:
            cit_data = citations_ev[0]["data"] if isinstance(citations_ev[0]["data"], dict) else {}
            cits = cit_data.get("citations", [])
            log(f"  Citations: {len(cits)}")
            save_json("research_mode_citations.json", cits)

        if research_sources:
            sources = [s["data"] for s in research_sources if isinstance(s["data"], dict)]
            log(f"  Total sources: {len(sources)}")
            save_json("research_mode_sources.json", sources)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 6 — RAG baseline (default mode)
# ══════════════════════════════════════════════════════════════════════════════
def test_rag_baseline(base_url: str, skip_slow: bool = False):
    section("SECTION 6 — RAG Baseline (Default Chat)")
    if skip_slow:
        log("Skipping (--skip-slow)", "WARN")
        return
    if not state.get("material_ready"):
        log("Materials not ready — skipping", "WARN")
        return

    nb_id = state["notebook_id"]
    mat_ids = state["material_ids"]

    # 6.1 Non-streaming RAG
    t0 = time.time()
    with make_client(base_url, timeout=180) as c:
        r = c.post("/chat", json={
            "material_ids": mat_ids,
            "notebook_id": nb_id,
            "message": "What columns are in the car data? List them.",
            "stream": False,
        })
    dur = time.time() - t0
    if check_response("/chat RAG non-streaming", r, 200, t0, "rag"):
        body = r.json()
        answer = body.get("response") or body.get("content") or body.get("answer") or str(body)[:200]
        record("RAG — response non-empty", bool(answer and len(str(answer)) > 10),
               f"length={len(str(answer))}", sect="rag")
        save_output("rag_baseline_response.md", str(answer),
                    "# RAG Baseline Response\n\nQuery: What columns are in the car data?")

    # 6.2 Streaming RAG
    t0 = time.time()
    with make_client(base_url, timeout=180) as c:
        r2 = c.post("/chat", json={
            "material_ids": mat_ids,
            "notebook_id": nb_id,
            "message": "What is the average price in the mall customers dataset?",
            "stream": True,
        })
    dur = time.time() - t0
    if r2.status_code == 200:
        events = parse_sse_response(r2)
        tokens = concat_tokens(events)
        record("/chat RAG streaming", len(tokens) > 10,
               f"response_length={len(tokens)}", dur, "rag")
        save_output("rag_streaming_response.md", tokens,
                    "# RAG Streaming Response\n\nQuery: Average price in mall customers")


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 7 — Cross-mode validation
# ══════════════════════════════════════════════════════════════════════════════
def test_crossmode(base_url: str, skip_slow: bool = False):
    section("SECTION 7 — Cross-Mode Validation")
    if skip_slow:
        log("Skipping (--skip-slow)", "WARN")
        return

    nb_id = state.get("notebook_id")
    mat_ids = state.get("material_ids", [])
    if not nb_id or not mat_ids:
        log("Missing notebook/materials — skipping", "WARN")
        return

    # 7.1 Invalid intent_override → should default to RAG or fail gracefully
    t0 = time.time()
    with make_client(base_url, timeout=30) as c:
        r = c.post("/chat", json={
            "material_ids": mat_ids,
            "notebook_id": nb_id,
            "message": "hello",
            "stream": False,
            "intent_override": "INVALID_INTENT",
        })
    # Should either reject (422) or handle gracefully
    record("Invalid intent_override handled", r.status_code in (200, 422),
           f"HTTP {r.status_code}", time.time() - t0, "crossmode")

    # 7.2 No material → 400
    t0 = time.time()
    with make_client(base_url, timeout=15) as c:
        r2 = c.post("/chat", json={
            "notebook_id": nb_id,
            "message": "test",
            "stream": False,
        })
    record("No material → 400", r2.status_code == 400,
           f"HTTP {r2.status_code}", time.time() - t0, "crossmode")

    # 7.3 Agent run-generated endpoint exists and works
    t0 = time.time()
    with make_client(base_url, timeout=60) as c:
        r3 = c.post("/agent/run-generated", json={
            "code": "print('run-generated test ok')",
            "language": "python",
            "notebook_id": nb_id,
            "timeout": 10,
        })
    record("/agent/run-generated works", r3.status_code == 200,
           f"HTTP {r3.status_code}", time.time() - t0, "crossmode")


# ══════════════════════════════════════════════════════════════════════════════
#  Summary & Report
# ══════════════════════════════════════════════════════════════════════════════
def print_summary():
    section("TEST SUMMARY")

    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    # Table by section
    sections = {}
    for r in results:
        sect = r.section or "general"
        if sect not in sections:
            sections[sect] = {"pass": 0, "fail": 0}
        if r.passed:
            sections[sect]["pass"] += 1
        else:
            sections[sect]["fail"] += 1

    print(f"\n  {'Section':<20} {'Pass':>6} {'Fail':>6} {'Total':>6}")
    print(f"  {'─'*20} {'─'*6} {'─'*6} {'─'*6}")
    for sect, counts in sections.items():
        total_s = counts["pass"] + counts["fail"]
        status = _green("✔") if counts["fail"] == 0 else _red("✘")
        print(f"  {sect:<20} {counts['pass']:>6} {counts['fail']:>6} {total_s:>6}  {status}")
    print(f"  {'─'*20} {'─'*6} {'─'*6} {'─'*6}")
    print(f"  {'TOTAL':<20} {passed:>6} {failed:>6} {total:>6}")

    # Failed tests detail
    failures = [r for r in results if not r.passed]
    if failures:
        print(f"\n  {_red('FAILURES:')}")
        for r in failures:
            print(f"    {_red('✘')} [{r.section}] {r.name} — {r.detail}")

    # Save full report as JSON
    report = {
        "run_id": _RUN_ID,
        "timestamp": datetime.now().isoformat(),
        "total": total,
        "passed": passed,
        "failed": failed,
        "sections": sections,
        "results": [
            {"name": r.name, "passed": r.passed, "detail": r.detail,
             "duration": r.duration, "section": r.section}
            for r in results
        ],
    }
    save_json("test_report.json", report)

    # Also generate a human-readable markdown report
    md_lines = [
        f"# Agentic Pipeline Test Report",
        f"",
        f"**Run ID:** `{_RUN_ID}`  ",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**Backend:** `{BASE_URL}`  ",
        f"",
        f"## Summary",
        f"",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Total  | {total} |",
        f"| Passed | {passed} |",
        f"| Failed | {failed} |",
        f"",
    ]
    if failures:
        md_lines.append("## Failures\n")
        for r in failures:
            md_lines.append(f"- **[{r.section}] {r.name}** — {r.detail}")
        md_lines.append("")

    md_lines.append("## All Results\n")
    md_lines.append("| # | Section | Test | Result | Detail | Time |")
    md_lines.append("|---|---------|------|--------|--------|------|")
    for i, r in enumerate(results, 1):
        status = "✅" if r.passed else "❌"
        md_lines.append(f"| {i} | {r.section} | {r.name} | {status} | {r.detail[:60]} | {r.duration:.2f}s |")

    save_output("test_report.md", "\n".join(md_lines))

    print(f"\n  {'='*50}")
    if failed == 0:
        print(f"  {_green(f'ALL {total} TESTS PASSED ✔')}")
    else:
        print(f"  {_red(f'{failed} / {total} TESTS FAILED ✘')}")
    print(f"  {'='*50}")
    print(f"\n  Output files in: {OUTPUT_DIR}\n")

    return failed


# ══════════════════════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════════════════════
def main():
    global BASE_URL

    parser = argparse.ArgumentParser(description="KeplerLab Agentic Pipeline Tests")
    parser.add_argument("--base", default=BASE_URL, help="Backend base URL")
    parser.add_argument("--skip-slow", action="store_true", help="Skip LLM-heavy tests")
    args = parser.parse_args()
    BASE_URL = args.base

    print(_bold(f"\n  KeplerLab Agentic Pipeline Test Suite"))
    print(f"  Run ID: {_RUN_ID}")
    print(f"  Backend: {BASE_URL}")
    print(f"  CSV files: {len(CSV_FILES)}")
    print(f"  Output: {OUTPUT_DIR}\n")

    test_preflight(BASE_URL)
    test_setup(BASE_URL)
    test_rag_baseline(BASE_URL, args.skip_slow)
    test_agent_mode(BASE_URL, args.skip_slow)
    test_code_mode(BASE_URL, args.skip_slow)
    test_web_mode(BASE_URL, args.skip_slow)
    test_research_mode(BASE_URL, args.skip_slow)
    test_crossmode(BASE_URL, args.skip_slow)

    failed = print_summary()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
