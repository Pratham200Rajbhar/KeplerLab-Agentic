#!/usr/bin/env python3
"""
=============================================================================
 KeplerLab — Full End-to-End Test Suite
=============================================================================
 Tests EVERY pipeline from new user registration to content generation.
 Resource: /home/pratham/disk1/New KeplerLab /Introduction.pdf

 Usage:
   python test_full_app.py                 # default: http://localhost:8000
   python test_full_app.py --base http://localhost:8001
   python test_full_app.py --skip-slow     # skip LLM-heavy tests

 Requirements:
   pip install httpx rich

 Exit codes:
   0  — all tests passed
   1  — one or more tests failed
=============================================================================
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

import httpx

# ── Optional rich output ──────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.table import Table
    from rich import print as rprint
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None

# ── Configuration ─────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:8000"
PDF_PATH = "/home/pratham/disk1/New KeplerLab /Introduction.pdf"
TIMEOUT = 120          # seconds per request
JOB_POLL_TIMEOUT = 300 # seconds to wait for async jobs (processing, generation)
JOB_POLL_INTERVAL = 4  # seconds between polls

# Unique test run identifiers
_RUN_ID = uuid.uuid4().hex[:8]
TEST_EMAIL = f"testuser_{_RUN_ID}@example.com"
TEST_USERNAME = f"testuser_{_RUN_ID}"
TEST_PASSWORD = "SecureTest1!"

# ── Result tracking ───────────────────────────────────────────────────────────
@dataclass
class TestResult:
    name: str
    passed: bool
    detail: str = ""
    duration: float = 0.0

results: list[TestResult] = []

# ── Colour helpers (fallback when rich not installed) ─────────────────────────
def _green(s): return f"\033[92m{s}\033[0m"
def _red(s):   return f"\033[91m{s}\033[0m"
def _yellow(s):return f"\033[93m{s}\033[0m"
def _bold(s):  return f"\033[1m{s}\033[0m"

# ── Logging ───────────────────────────────────────────────────────────────────
def log(msg: str, level: str = "INFO"):
    prefix = {"INFO": "ℹ", "PASS": "✔", "FAIL": "✘", "WARN": "⚠", "HEAD": "▶"}.get(level, " ")
    if level == "PASS":
        print(f"  {_green(prefix)} {msg}")
    elif level == "FAIL":
        print(f"  {_red(prefix)} {msg}")
    elif level == "WARN":
        print(f"  {_yellow(prefix)} {msg}")
    elif level == "HEAD":
        print(f"\n{_bold(f'── {msg} ──')}")
    else:
        print(f"  {prefix} {msg}")

def section(title: str):
    width = 70
    print(f"\n{'='*width}")
    print(f"  {title}")
    print(f"{'='*width}")

# ── HTTP helpers ──────────────────────────────────────────────────────────────
def record(name: str, passed: bool, detail: str = "", duration: float = 0.0):
    results.append(TestResult(name, passed, detail, duration))
    level = "PASS" if passed else "FAIL"
    det = f" — {detail}" if detail else ""
    log(f"{name}{det} ({duration:.2f}s)", level)

def check_response(name: str, resp: httpx.Response, expected_status: int = 200, t0: float = 0.0):
    dur = time.time() - t0
    if resp.status_code == expected_status:
        record(name, True, f"HTTP {resp.status_code}", dur)
        return True
    else:
        try:
            body = resp.json()
        except Exception:
            body = resp.text[:200]
        record(name, False, f"Expected {expected_status}, got {resp.status_code}: {body}", dur)
        return False

# ── Global state shared across tests ─────────────────────────────────────────
state: dict = {}

# ── Client factory ─────────────────────────────────────────────────────────────
def make_client(base_url: str, access_token: Optional[str] = None, cookies: dict = None) -> httpx.Client:
    headers = {"Content-Type": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    return httpx.Client(
        base_url=base_url,
        headers=headers,
        timeout=TIMEOUT,
        cookies=cookies or {},
        follow_redirects=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 0 — Preflight checks
# ══════════════════════════════════════════════════════════════════════════════
def test_preflight(base_url: str):
    section("SECTION 0 — Preflight Checks")

    # 0.1 PDF resource exists
    t0 = time.time()
    exists = os.path.isfile(PDF_PATH)
    record("PDF resource exists", exists, PDF_PATH if exists else "FILE MISSING", time.time()-t0)

    # 0.2 Backend reachable (unauthenticated)
    t0 = time.time()
    try:
        with httpx.Client(timeout=10) as c:
            r = c.get(f"{base_url}/docs")
        reachable = r.status_code in (200, 301, 302)
        record("Backend reachable", reachable, f"HTTP {r.status_code}", time.time()-t0)
    except Exception as e:
        record("Backend reachable", False, str(e), time.time()-t0)
        print(_red("\n  FATAL: Backend is not running. Start it and retry.\n"))
        sys.exit(1)

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 1 — Authentication
# ══════════════════════════════════════════════════════════════════════════════
def test_auth(base_url: str) -> tuple[str, dict]:
    """Returns (access_token, cookies)."""
    section("SECTION 1 — Authentication")

    # 1.1 Signup
    t0 = time.time()
    with httpx.Client(base_url=base_url, timeout=TIMEOUT) as c:
        r = c.post("/auth/signup", json={
            "email": TEST_EMAIL,
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
        })
    if check_response("POST /auth/signup (new user)", r, 201, t0):
        state["user"] = r.json()
        log(f"  Created user: {state['user'].get('email')} id={state['user'].get('id')}")
    else:
        log("Signup failed — attempting login with existing credentials", "WARN")

    # 1.2 Duplicate signup rejected
    t0 = time.time()
    with httpx.Client(base_url=base_url, timeout=TIMEOUT) as c:
        r2 = c.post("/auth/signup", json={
            "email": TEST_EMAIL,
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
        })
    record("POST /auth/signup (duplicate rejected)", r2.status_code in (400, 409, 422), f"HTTP {r2.status_code}", time.time()-t0)

    # 1.3 Login with valid credentials
    t0 = time.time()
    with httpx.Client(base_url=base_url, timeout=TIMEOUT) as c:
        r3 = c.post("/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    if check_response("POST /auth/login (valid)", r3, 200, t0):
        access_token = r3.json().get("access_token", "")
        cookies = dict(r3.cookies)
        state["access_token"] = access_token
        state["cookies"] = cookies
        log(f"  Token received (first 20 chars): {access_token[:20]}…")
    else:
        print(_red("  FATAL: Login failed — cannot continue tests."))
        sys.exit(1)

    # 1.4 Login with wrong password
    t0 = time.time()
    with httpx.Client(base_url=base_url, timeout=TIMEOUT) as c:
        r4 = c.post("/auth/login", json={"email": TEST_EMAIL, "password": "WrongPass99!"})
    record("POST /auth/login (wrong password → 401)", r4.status_code == 401, f"HTTP {r4.status_code}", time.time()-t0)

    # 1.5 Token refresh via cookie
    t0 = time.time()
    with httpx.Client(base_url=base_url, timeout=TIMEOUT, cookies=state["cookies"]) as c:
        r5 = c.post("/auth/refresh")
    if check_response("POST /auth/refresh (cookie-based)", r5, 200, t0):
        new_tok = r5.json().get("access_token", "")
        if new_tok:
            state["access_token"] = new_tok
            state["cookies"] = dict(r5.cookies) or state["cookies"]
            log("  Token rotated successfully")

    # 1.6 Access protected route without token (401)
    t0 = time.time()
    with httpx.Client(base_url=base_url, timeout=TIMEOUT) as c:
        r6 = c.get("/notebooks")
    record("GET /notebooks (no token → 401)", r6.status_code == 401, f"HTTP {r6.status_code}", time.time()-t0)

    # 1.7 Get current user /auth/me
    t0 = time.time()
    with make_client(base_url, state["access_token"], state["cookies"]) as c:
        r7 = c.get("/auth/me")
    check_response("GET /auth/me", r7, 200, t0)
    if r7.status_code == 200:
        log(f"  User info: {r7.json()}")

    return state["access_token"], state["cookies"]

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 2 — Health & Models
# ══════════════════════════════════════════════════════════════════════════════
def test_health_and_models(base_url: str):
    section("SECTION 2 — Health & Models Status")
    tok = state["access_token"]

    # 2.1 Health check — accept 200 (healthy/degraded) or 503 (unhealthy)
    # 503 is legitimate when ChromaDB hasn't been initialised yet; it will
    # self-heal on first material processing.
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r = c.get("/health")
    # We accept both 200 and 503 here; what matters is the payload fields.
    record("GET /health", r.status_code in (200, 503), f"HTTP {r.status_code}", time.time() - t0)
    if r.status_code in (200, 503):
        h = r.json()
        log(f"  overall={h.get('overall')} db={h.get('database')} "
            f"vector_db={h.get('vector_db')} llm={h.get('llm')}")
        record(
            "Health — database component ok",
            h.get("database") == "ok",
            f"database={h.get('database')}",
        )

    # 2.2 Models status
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r2 = c.get("/models/status")
    if check_response("GET /models/status", r2, 200, t0):
        ms = r2.json()
        log(f"  Models summary: {ms.get('summary')}")

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 3 — Notebook CRUD
# ══════════════════════════════════════════════════════════════════════════════
def test_notebooks(base_url: str):
    section("SECTION 3 — Notebook CRUD")
    tok = state["access_token"]

    # 3.1 Create notebook
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r = c.post("/notebooks", json={
            "name": f"Test Notebook {_RUN_ID}",
            "description": "Automated test notebook"
        })
    if check_response("POST /notebooks (create)", r, 201, t0):
        nb = r.json()
        state["notebook_id"] = nb["id"]
        log(f"  Notebook created: id={nb['id']} name={nb['name']}")

    # 3.2 List notebooks
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r2 = c.get("/notebooks")
    if check_response("GET /notebooks (list)", r2, 200, t0):
        notebooks = r2.json()
        record("Notebook appears in list", any(n["id"] == state.get("notebook_id") for n in notebooks), f"count={len(notebooks)}")

    # 3.3 Get notebook by ID
    nb_id = state.get("notebook_id")
    if nb_id:
        t0 = time.time()
        with make_client(base_url, tok, state["cookies"]) as c:
            r3 = c.get(f"/notebooks/{nb_id}")
        check_response(f"GET /notebooks/{nb_id}", r3, 200, t0)

    # 3.4 Update notebook
    if nb_id:
        t0 = time.time()
        with make_client(base_url, tok, state["cookies"]) as c:
            r4 = c.put(f"/notebooks/{nb_id}", json={"name": f"Updated Notebook {_RUN_ID}"})
        check_response("PUT /notebooks/:id (update name)", r4, 200, t0)

    # 3.5 Create a second notebook to test deletion later
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r5 = c.post("/notebooks", json={"name": f"Temp Notebook {_RUN_ID}"})
    if check_response("POST /notebooks (second notebook)", r5, 201, t0):
        state["notebook_to_delete"] = r5.json()["id"]

    # 3.6 Delete second notebook
    if state.get("notebook_to_delete"):
        t0 = time.time()
        with make_client(base_url, tok, state["cookies"]) as c:
            r6 = c.delete(f"/notebooks/{state['notebook_to_delete']}")
        check_response("DELETE /notebooks/:id", r6, 204, t0)

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 4 — Upload & Material Processing
# ══════════════════════════════════════════════════════════════════════════════
def test_upload_and_processing(base_url: str):
    section("SECTION 4 — File Upload & Material Processing")
    tok = state["access_token"]
    nb_id = state.get("notebook_id")

    if not os.path.isfile(PDF_PATH):
        log("PDF file missing — skipping upload tests", "WARN")
        return

    # 4.1 Upload PDF
    t0 = time.time()
    with open(PDF_PATH, "rb") as fh:
        with httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {tok}"},
            timeout=TIMEOUT,
            cookies=state["cookies"],
        ) as c:
            r = c.post(
                "/upload",
                data={"notebook_id": nb_id},
                files={"file": ("Introduction.pdf", fh, "application/pdf")},
            )
    if check_response("POST /upload (PDF file)", r, 202, t0):
        body = r.json()
        state["upload_job_id"] = body.get("job_id")
        state["material_id"] = body.get("material_id")
        log(f"  Upload accepted: job_id={state['upload_job_id']} material_id={state['material_id']}")

    # 4.2 Upload same file twice (deduplication / second upload succeeds)
    t0 = time.time()
    with open(PDF_PATH, "rb") as fh:
        with httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {tok}"},
            timeout=TIMEOUT,
            cookies=state["cookies"],
        ) as c:
            r2 = c.post(
                "/upload",
                data={"notebook_id": nb_id},
                files={"file": ("Introduction.pdf", fh, "application/pdf")},
            )
    record("POST /upload (duplicate upload handled)", r2.status_code in (202, 400, 409), f"HTTP {r2.status_code}", time.time()-t0)
    if r2.status_code == 202:
        state["material_id_2"] = r2.json().get("material_id")

    # 4.3 Upload plain text
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r3 = c.post("/upload/text", json={
            "text": "Kepler's laws of planetary motion describe how planets orbit the Sun.\n"
                    "First law: orbits are ellipses.\nSecond law: equal areas in equal time.\n"
                    "Third law: orbital period squared proportional to semi-major axis cubed.",
            "title": "Kepler Laws Summary",
            "notebook_id": nb_id,
        })
    if check_response("POST /upload/text", r3, 202, t0):
        state["text_material_id"] = r3.json().get("material_id")
        log(f"  Text material: {state['text_material_id']}")

    # 4.4 Poll job until completion (or timeout)
    job_id = state.get("upload_job_id")
    if job_id:
        log(f"Polling job {job_id} until complete (max {JOB_POLL_TIMEOUT}s)…")
        deadline = time.time() + JOB_POLL_TIMEOUT
        final_status = "unknown"
        while time.time() < deadline:
            with make_client(base_url, tok, state["cookies"]) as c:
                jr = c.get(f"/jobs/{job_id}")
            if jr.status_code == 200:
                jd = jr.json()
                final_status = jd.get("status", "unknown")
                log(f"  Job status: {final_status}")
                if final_status in ("completed", "failed"):
                    break
            time.sleep(JOB_POLL_INTERVAL)
        record("Job processing completes (PDF → completed)", final_status == "completed", f"final_status={final_status}", time.time()-t0)

    # 4.5 List materials → material appears
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r5 = c.get(f"/materials?notebook_id={nb_id}")
    if check_response("GET /materials (list for notebook)", r5, 200, t0):
        mats = r5.json()
        found = any(m["id"] == state.get("material_id") for m in mats)
        record("Material appears in list", found, f"total={len(mats)}")
        if mats:
            state["material_status"] = next((m["status"] for m in mats if m["id"] == state.get("material_id")), "unknown")
            log(f"  Material status: {state['material_status']}")

    # 4.6 Update material title
    mat_id = state.get("material_id")
    if mat_id:
        t0 = time.time()
        with make_client(base_url, tok, state["cookies"]) as c:
            r6 = c.patch(f"/materials/{mat_id}", json={"title": "Introduction (test)"})
        check_response("PATCH /materials/:id (update title)", r6, 200, t0)

    # 4.7 Ensure at least one completed material for generation tests
    log("Waiting for material to be in 'completed' state for generation tests…")
    _wait_for_material_completed(base_url, tok, state.get("material_id"), nb_id)

def _wait_for_material_completed(base_url, tok, material_id, nb_id, timeout=JOB_POLL_TIMEOUT):
    """Poll materials list until the target material is 'completed'."""
    if not material_id:
        return
    deadline = time.time() + timeout
    while time.time() < deadline:
        with make_client(base_url, tok, state["cookies"]) as c:
            r = c.get(f"/materials?notebook_id={nb_id}")
        if r.status_code == 200:
            mats = r.json()
            for m in mats:
                if m["id"] == material_id:
                    if m["status"] == "completed":
                        state["material_ready"] = True
                        log(f"  Material {material_id} is completed ✔")
                        return
                    elif m["status"] == "failed":
                        log(f"  Material {material_id} FAILED processing", "FAIL")
                        return
                    else:
                        log(f"  Material status: {m['status']} (waiting…)")
        time.sleep(JOB_POLL_INTERVAL)
    log(f"  Timed out waiting for material {material_id} to complete", "WARN")

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 5 — URL & YouTube Upload
# ══════════════════════════════════════════════════════════════════════════════
def test_url_upload(base_url: str):
    section("SECTION 5 — URL Upload")
    tok = state["access_token"]
    nb_id = state.get("notebook_id")

    # 5.1 Upload from URL (Wikipedia article — reliable)
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r = c.post("/upload/url", json={
            "url": "https://en.wikipedia.org/wiki/Johannes_Kepler",
            "notebook_id": nb_id,
            "source_type": "web",
            "title": "Wikipedia: Johannes Kepler",
        })
    if check_response("POST /upload/url (web page)", r, 202, t0):
        state["url_material_id"] = r.json().get("material_id")
        log(f"  URL material: {state['url_material_id']}")
    else:
        log("URL upload returned non-202 (may be expected in offline mode)", "WARN")

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 6 — Flashcard Generation
# ══════════════════════════════════════════════════════════════════════════════
def test_flashcards(base_url: str, skip_slow: bool = False):
    section("SECTION 6 — Flashcard Generation")
    if skip_slow:
        log("Skipping (--skip-slow)", "WARN")
        return
    if not state.get("material_ready"):
        log("Material not ready — skipping flashcard tests", "WARN")
        return

    tok = state["access_token"]
    mat_id = state["material_id"]

    # 6.1 Generate flashcards — easy
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r = c.post("/flashcard", json={
            "material_id": mat_id,
            "card_count": 5,
            "difficulty": "easy",
        }, timeout=180)
    if check_response("POST /flashcard (easy, 5 cards)", r, 200, t0):
        fc = r.json()
        cards = fc.get("flashcards") or fc.get("cards") or []
        record("Flashcards — has cards", len(cards) > 0, f"count={len(cards)}")
        if cards:
            log(f"  Sample card Q: {cards[0].get('question','?')[:80]}")

    # 6.2 Generate flashcards — medium with topic
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r2 = c.post("/flashcard", json={
            "material_id": mat_id,
            "card_count": 3,
            "difficulty": "medium",
            "topic": "main concepts",
        }, timeout=180)
    if check_response("POST /flashcard (medium, topic filter)", r2, 200, t0):
        fc2 = r2.json()
        cards2 = fc2.get("flashcards") or fc2.get("cards") or []
        record("Flashcards — topic filter returns cards", len(cards2) > 0, f"count={len(cards2)}")

    # 6.3 No material → 400
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r3 = c.post("/flashcard", json={"card_count": 5}, timeout=30)
    record("POST /flashcard (no material → 400)", r3.status_code == 400, f"HTTP {r3.status_code}", time.time()-t0)

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 7 — Quiz Generation
# ══════════════════════════════════════════════════════════════════════════════
def test_quiz(base_url: str, skip_slow: bool = False):
    section("SECTION 7 — Quiz Generation")
    if skip_slow:
        log("Skipping (--skip-slow)", "WARN")
        return
    if not state.get("material_ready"):
        log("Material not ready — skipping quiz tests", "WARN")
        return

    tok = state["access_token"]
    mat_id = state["material_id"]

    # 7.1 Generate quiz
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r = c.post("/quiz", json={
            "material_id": mat_id,
            "mcq_count": 5,
            "difficulty": "medium",
        }, timeout=180)
    if check_response("POST /quiz (5 questions)", r, 200, t0):
        q = r.json()
        questions = q.get("questions") or q.get("mcqs") or []
        record("Quiz — has questions", len(questions) > 0, f"count={len(questions)}")
        if questions:
            log(f"  Sample Q: {questions[0].get('question','?')[:80]}")

    # 7.2 Hard difficulty
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r2 = c.post("/quiz", json={
            "material_id": mat_id,
            "mcq_count": 3,
            "difficulty": "hard",
            "topic": "key details",
        }, timeout=180)
    if check_response("POST /quiz (hard, topic)", r2, 200, t0):
        q2 = r2.json()
        qs2 = q2.get("questions") or q2.get("mcqs") or []
        record("Quiz — hard difficulty returns questions", len(qs2) > 0, f"count={len(qs2)}")

    # 7.3 No material → 400
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r3 = c.post("/quiz", json={"mcq_count": 5}, timeout=30)
    record("POST /quiz (no material → 400)", r3.status_code == 400, f"HTTP {r3.status_code}", time.time()-t0)

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 8 — Chat (RAG)
# ══════════════════════════════════════════════════════════════════════════════
def test_chat(base_url: str, skip_slow: bool = False):
    section("SECTION 8 — Chat (RAG)")
    if skip_slow:
        log("Skipping (--skip-slow)", "WARN")
        return
    if not state.get("material_ready"):
        log("Material not ready — skipping chat tests", "WARN")
        return

    tok = state["access_token"]
    mat_id = state["material_id"]
    nb_id = state["notebook_id"]

    # 8.1 Create a chat session
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r = c.post("/chat/sessions", json={"notebook_id": nb_id, "title": "Test Session"})
    if check_response("POST /chat/sessions (create)", r, 200, t0):
        # Route returns {"session_id": ...}
        session_id = r.json().get("session_id") or r.json().get("id")
        state["chat_session_id"] = session_id
        log(f"  Session: {session_id}")

    # 8.2 RAG chat (non-streaming to simplify testing)
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r2 = c.post("/chat", json={
            "material_id": mat_id,
            "notebook_id": nb_id,
            "message": "What is the main topic of this document? Give a brief summary.",
            "stream": False,
            "session_id": state.get("chat_session_id"),
        }, timeout=180)
    if check_response("POST /chat (RAG, non-streaming)", r2, 200, t0):
        body = r2.json()
        answer = body.get("response") or body.get("content") or body.get("answer") or str(body)[:100]
        record("Chat — RAG response non-empty", bool(answer and len(answer) > 5), f"length={len(str(answer))}")
        log(f"  Answer excerpt: {str(answer)[:120]}")

    # 8.3 Get chat sessions list — path param: /chat/sessions/{notebook_id}
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r3 = c.get(f"/chat/sessions/{nb_id}")
    check_response("GET /chat/sessions/:notebook_id (list)", r3, 200, t0)

    # 8.4 Get chat history — path param: /chat/history/{notebook_id}?session_id=...
    sess_id = state.get("chat_session_id")
    if sess_id:
        t0 = time.time()
        with make_client(base_url, tok, state["cookies"]) as c:
            r4 = c.get(f"/chat/history/{nb_id}?session_id={sess_id}")
        check_response("GET /chat/history/:notebook_id (with session)", r4, 200, t0)

    # 8.5 Chat requires material → 400
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r5 = c.post("/chat", json={
            "notebook_id": nb_id,
            "message": "hello",
            "stream": False,
        }, timeout=30)
    record("POST /chat (no material → 400)", r5.status_code == 400, f"HTTP {r5.status_code}", time.time()-t0)

    # 8.6 Delete chat session
    if sess_id:
        t0 = time.time()
        with make_client(base_url, tok, state["cookies"]) as c:
            r6 = c.delete(f"/chat/sessions/{sess_id}")
        check_response("DELETE /chat/sessions/:session_id", r6, 200, t0)

    # 8.7 Clear chat history for notebook
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r7 = c.delete(f"/chat/history/{nb_id}")
    check_response("DELETE /chat/history/:notebook_id", r7, 200, t0)

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 9 — Mind Map Generation
# ══════════════════════════════════════════════════════════════════════════════
def test_mindmap(base_url: str, skip_slow: bool = False):
    section("SECTION 9 — Mind Map Generation")
    if skip_slow:
        log("Skipping (--skip-slow)", "WARN")
        return
    if not state.get("material_ready"):
        log("Material not ready — skipping mindmap tests", "WARN")
        return

    tok = state["access_token"]
    mat_id = state["material_id"]
    nb_id = state["notebook_id"]

    # 9.1 Generate mind map
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r = c.post("/mindmap", json={
            "material_ids": [mat_id],
            "notebook_id": nb_id,
        }, timeout=600)
    if check_response("POST /mindmap (generate)", r, 200, t0):
        mm = r.json()
        nodes = mm.get("nodes") or []
        record("MindMap — has nodes", len(nodes) > 0, f"nodes={len(nodes)}")
        if nodes:
            log(f"  Root: {nodes[0].get('label','?')[:60]}")

    # 9.2 Get saved mind map
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r2 = c.get(f"/mindmap/{nb_id}")
    # May be 200 or 404 if nothing was auto-saved
    record("GET /mindmap/:notebook_id", r2.status_code in (200, 404), f"HTTP {r2.status_code}", time.time()-t0)

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 10 — Presentation (PPT) Generation
# ══════════════════════════════════════════════════════════════════════════════
def test_ppt(base_url: str, skip_slow: bool = False):
    section("SECTION 10 — Presentation (PPT) Generation")
    if skip_slow:
        log("Skipping (--skip-slow)", "WARN")
        return
    if not state.get("material_ready"):
        log("Material not ready — skipping PPT tests", "WARN")
        return

    tok = state["access_token"]
    mat_id = state["material_id"]
    nb_id = state["notebook_id"]

    # 10.1 Generate presentation
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r = c.post("/presentation", json={
            "material_id": mat_id,
            "max_slides": 6,
            "theme": "minimalist",
            "additional_instructions": "Focus on key points",
        }, timeout=600)
    if check_response("POST /presentation (generate)", r, 200, t0):
        ppt = r.json()
        slides = ppt.get("slides") or ppt.get("data", {}).get("slides") or []
        html_content = ppt.get("html") or ppt.get("data", {}).get("html") or ""
        record("PPT — has slides or HTML content", len(slides) > 0 or len(html_content) > 100,
               f"slides={len(slides)} html_len={len(html_content)}")
        if slides:
            log(f"  Slide 1 title: {slides[0].get('title','?')[:60]}")
        state["ppt_data"] = ppt

    # 10.2 No material → 400
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r2 = c.post("/presentation", json={"max_slides": 5}, timeout=30)
    record("POST /presentation (no material → 400)", r2.status_code == 400, f"HTTP {r2.status_code}", time.time()-t0)

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 11 — Notebook Content (Save / Get / Update / Delete)
# ══════════════════════════════════════════════════════════════════════════════
def test_notebook_content(base_url: str):
    section("SECTION 11 — Notebook Generated Content CRUD")
    tok = state["access_token"]
    nb_id = state.get("notebook_id")
    if not nb_id:
        log("No notebook — skipping", "WARN")
        return

    # 11.1 Save flashcards content
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r = c.post(f"/notebooks/{nb_id}/content", json={
            "content_type": "flashcards",
            "title": "Test Flashcards",
            "data": {
                "flashcards": [
                    {"question": "What is a test?", "answer": "A test validates correctness."}
                ]
            },
            "material_id": state.get("material_id"),
        })
    if check_response("POST /notebooks/:id/content (flashcards)", r, 200, t0):
        state["content_id"] = r.json().get("id")
        log(f"  Content saved: id={state['content_id']}")

    # 11.2 Get notebook content
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r2 = c.get(f"/notebooks/{nb_id}/content")
    if check_response("GET /notebooks/:id/content", r2, 200, t0):
        contents = r2.json()
        record("Content appears in notebook", any(c.get("id") == state.get("content_id") for c in contents), f"total={len(contents)}")

    # 11.3 Save quiz content
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r3 = c.post(f"/notebooks/{nb_id}/content", json={
            "content_type": "quiz",
            "title": "Test Quiz",
            "data": {
                "questions": [
                    {
                        "question": "Sample?",
                        "options": ["A", "B", "C", "D"],
                        "correct": "A",
                        "explanation": "Because A."
                    }
                ]
            },
        })
    check_response("POST /notebooks/:id/content (quiz)", r3, 200, t0)

    # 11.4 Update content title
    content_id = state.get("content_id")
    if content_id:
        t0 = time.time()
        with make_client(base_url, tok, state["cookies"]) as c:
            r4 = c.put(f"/notebooks/{nb_id}/content/{content_id}", json={"title": "Updated Flashcards"})
        check_response("PUT /notebooks/:id/content/:cid (update title)", r4, 200, t0)

    # 11.5 Delete content
    if content_id:
        t0 = time.time()
        with make_client(base_url, tok, state["cookies"]) as c:
            r5 = c.delete(f"/notebooks/{nb_id}/content/{content_id}")
        check_response("DELETE /notebooks/:id/content/:cid", r5, 200, t0)

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 12 — Podcast Session
# ══════════════════════════════════════════════════════════════════════════════
def test_podcast(base_url: str, skip_slow: bool = False):
    section("SECTION 12 — Podcast Session (Create/List)")
    if skip_slow:
        log("Skipping (--skip-slow)", "WARN")
        return
    if not state.get("material_ready"):
        log("Material not ready — skipping podcast tests", "WARN")
        return

    tok = state["access_token"]
    nb_id = state["notebook_id"]
    mat_id = state["material_id"]

    # 12.1 Create podcast session
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r = c.post("/podcast/session", json={
            "notebook_id": nb_id,
            "mode": "overview",
            "language": "en",
            "material_ids": [mat_id],
        }, timeout=60)
    if check_response("POST /podcast/session (create)", r, 200, t0):
        sess = r.json()
        state["podcast_session_id"] = sess.get("id") or sess.get("session_id")
        log(f"  Podcast session: {state['podcast_session_id']}")

    # 12.2 List podcast sessions — path param: /podcast/sessions/{notebook_id}
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r2 = c.get(f"/podcast/sessions/{nb_id}")
    check_response("GET /podcast/sessions/:notebook_id (list)", r2, 200, t0)

    # 12.3 Get podcast voices — GET /podcast/voices
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r3 = c.get("/podcast/voices")
    check_response("GET /podcast/voices", r3, 200, t0)
    if r3.status_code == 200:
        voices = r3.json()
        log(f"  Voices: {list(voices.keys())[:3]}")

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 13 — Explainer (Check Presentations)
# ══════════════════════════════════════════════════════════════════════════════
def test_explainer(base_url: str, skip_slow: bool = False):
    section("SECTION 13 — Explainer Pipeline")
    if skip_slow:
        log("Skipping (--skip-slow)", "WARN")
        return
    if not state.get("material_ready"):
        log("Material not ready — skipping explainer tests", "WARN")
        return

    tok = state["access_token"]
    nb_id = state["notebook_id"]
    mat_id = state["material_id"]

    # 13.1 Check existing presentations
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r = c.post("/explainer/check-presentations", json={
            "material_ids": [mat_id],
            "notebook_id": nb_id,
        }, timeout=30)
    check_response("POST /explainer/check-presentations", r, 200, t0)

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 14 — Search
# ══════════════════════════════════════════════════════════════════════════════
def test_search(base_url: str):
    section("SECTION 14 — Web Search (proxy)")
    tok = state["access_token"]

    # 14.1 Web search request
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r = c.post("/search/web", json={
            "query": "Kepler laws of planetary motion",
            "engine": "duckduckgo",
        }, timeout=30)
    # Could be 200 (results) or 502 (external service down)
    record("POST /search/web", r.status_code in (200, 502, 503), f"HTTP {r.status_code}", time.time()-t0)
    if r.status_code == 200:
        results_list = r.json()
        log(f"  Search results: {len(results_list)}")

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 15 — Materials Cleanup & Delete
# ══════════════════════════════════════════════════════════════════════════════
def test_material_delete(base_url: str):
    section("SECTION 15 — Material Deletion")
    tok = state["access_token"]

    # 15.1 Delete secondary material if created
    mat_id2 = state.get("material_id_2")
    if mat_id2:
        t0 = time.time()
        with make_client(base_url, tok, state["cookies"]) as c:
            r = c.delete(f"/materials/{mat_id2}")
        check_response(f"DELETE /materials/{mat_id2[:8]}…", r, 200, t0)

    # 15.2 Delete text material
    text_mat = state.get("text_material_id")
    if text_mat:
        t0 = time.time()
        with make_client(base_url, tok, state["cookies"]) as c:
            r2 = c.delete(f"/materials/{text_mat}")
        check_response(f"DELETE /materials/{text_mat[:8]}… (text)", r2, 200, t0)

    # 15.3 Access non-existent material
    t0 = time.time()
    fake_id = str(uuid.uuid4())
    with make_client(base_url, tok, state["cookies"]) as c:
        r3 = c.delete(f"/materials/{fake_id}")
    record("DELETE /materials (non-existent → 404)", r3.status_code == 404, f"HTTP {r3.status_code}", time.time()-t0)

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 16 — Jobs Endpoint Validation
# ══════════════════════════════════════════════════════════════════════════════
def test_jobs(base_url: str):
    section("SECTION 16 — Jobs Endpoint")
    tok = state["access_token"]

    # 16.1 Non-existent job → 404
    t0 = time.time()
    fake_job = str(uuid.uuid4())
    with make_client(base_url, tok, state["cookies"]) as c:
        r = c.get(f"/jobs/{fake_job}")
    record("GET /jobs/:id (non-existent → 404)", r.status_code == 404, f"HTTP {r.status_code}", time.time()-t0)

    # 16.2 Job from upload step is accessible
    job_id = state.get("upload_job_id")
    if job_id:
        t0 = time.time()
        with make_client(base_url, tok, state["cookies"]) as c:
            r2 = c.get(f"/jobs/{job_id}")
        check_response("GET /jobs/:id (valid job)", r2, 200, t0)

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 17 — Auth Lifecycle (Logout)
# ══════════════════════════════════════════════════════════════════════════════
def test_logout(base_url: str):
    section("SECTION 17 — Logout & Token Revocation")
    tok = state["access_token"]

    # 17.1 Logout
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r = c.post("/auth/logout")
    check_response("POST /auth/logout", r, 200, t0)

    # 17.2 Refresh token should now be revoked — GET /auth/refresh must return 401
    # (Access tokens are stateless JWTs; they remain valid until expiry.
    #  What logout invalidates is the refresh token stored in the HttpOnly cookie.)
    t0 = time.time()
    with httpx.Client(base_url=base_url, timeout=TIMEOUT, cookies=state["cookies"]) as c:
        r2 = c.post("/auth/refresh")
    record(
        "POST /auth/refresh after logout → 401 (refresh token revoked)",
        r2.status_code == 401,
        f"HTTP {r2.status_code}",
        time.time() - t0,
    )

    # 17.3 Unauthenticated request (no token at all) → 401
    t0 = time.time()
    with httpx.Client(base_url=base_url, timeout=TIMEOUT) as c:
        r3 = c.get("/notebooks")
    record("GET /notebooks (no token) → 401", r3.status_code == 401, f"HTTP {r3.status_code}", time.time()-t0)

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 18 — Input Validation Guards
# ══════════════════════════════════════════════════════════════════════════════
def test_input_validation(base_url: str):
    section("SECTION 18 — Input Validation Guards")

    # 18.1 Signup with weak password
    t0 = time.time()
    with httpx.Client(base_url=base_url, timeout=TIMEOUT) as c:
        r = c.post("/auth/signup", json={
            "email": f"val_{_RUN_ID}@test.com",
            "username": "testval",
            "password": "weak",
        })
    record("POST /auth/signup (weak password → 422)", r.status_code == 422, f"HTTP {r.status_code}", time.time()-t0)

    # 18.2 Signup with invalid email
    t0 = time.time()
    with httpx.Client(base_url=base_url, timeout=TIMEOUT) as c:
        r2 = c.post("/auth/signup", json={
            "email": "not-an-email",
            "username": "someone",
            "password": "ValidPass1!",
        })
    record("POST /auth/signup (invalid email → 422)", r2.status_code == 422, f"HTTP {r2.status_code}", time.time()-t0)

    # 18.3 Notebook with empty name
    tok2 = state.get("access_token", "")
    if tok2:
        t0 = time.time()
        with make_client(base_url, tok2, state["cookies"]) as c:
            r3 = c.post("/notebooks", json={"name": "", "description": "test"})
        record("POST /notebooks (empty name → 422)", r3.status_code == 422, f"HTTP {r3.status_code}", time.time()-t0)

# ══════════════════════════════════════════════════════════════════════════════
#  MULTI-MATERIAL Tests
# ══════════════════════════════════════════════════════════════════════════════
def test_multi_material(base_url: str, skip_slow: bool = False):
    section("SECTION 19 — Multi-Material Generation")
    if skip_slow:
        log("Skipping (--skip-slow)", "WARN")
        return
    if not state.get("material_ready"):
        log("Material not ready — skipping", "WARN")
        return

    tok = state["access_token"]
    nb_id = state["notebook_id"]
    mat_id = state["material_id"]

    # Need at least 2 materials; use text_material if available, else same material twice
    mat_ids = [mat_id]
    if state.get("text_material_id"):
        mat_ids.append(state["text_material_id"])
    elif state.get("url_material_id"):
        mat_ids.append(state["url_material_id"])

    if len(mat_ids) < 2:
        log("Only 1 material available — multi-material tests skipped", "WARN")
        return

    # 19.1 Multi-material flashcards
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r = c.post("/flashcard", json={
            "material_ids": mat_ids,
            "card_count": 4,
            "difficulty": "easy",
        }, timeout=180)
    if check_response("POST /flashcard (multi-material)", r, 200, t0):
        cards = r.json().get("flashcards") or r.json().get("cards") or []
        record("Multi-material flashcards — has cards", len(cards) > 0, f"count={len(cards)}")

    # 19.2 Multi-material quiz
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r2 = c.post("/quiz", json={
            "material_ids": mat_ids,
            "mcq_count": 3,
            "difficulty": "medium",
        }, timeout=180)
    if check_response("POST /quiz (multi-material)", r2, 200, t0):
        qs = r2.json().get("questions") or r2.json().get("mcqs") or []
        record("Multi-material quiz — has questions", len(qs) > 0, f"count={len(qs)}")

    # 19.3 Multi-material mindmap
    t0 = time.time()
    with make_client(base_url, tok, state["cookies"]) as c:
        r3 = c.post("/mindmap", json={
            "material_ids": mat_ids,
            "notebook_id": nb_id,
        }, timeout=600)
    if check_response("POST /mindmap (multi-material)", r3, 200, t0):
        nodes = r3.json().get("nodes") or []
        record("Multi-material mindmap — has nodes", len(nodes) > 0, f"nodes={len(nodes)}")

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 20 — Agent: Code Execution (REPL)
# ══════════════════════════════════════════════════════════════════════════════
def test_agent_execute(base_url: str, skip_slow: bool = False):
    section("SECTION 20 — Agent: Code Execution (REPL)")
    if skip_slow:
        log("Skipping (--skip-slow)", "WARN")
        return

    tok = state["access_token"]
    nb_id = state.get("notebook_id", "test-nb")

    # 20.1 Direct code execution via POST /agent/execute (SSE — read raw text)
    t0 = time.time()
    with httpx.Client(
        base_url=base_url,
        headers={"Authorization": f"Bearer {tok}"},
        timeout=60,
        cookies=state.get("cookies", {}),
        follow_redirects=True,
    ) as c:
        r = c.post("/agent/execute", json={
            "code": "print('hello from kepler test')\nx = 2 + 2\nprint(x)",
            "notebook_id": nb_id,
            "timeout": 15,
        })
    record("POST /agent/execute (Python REPL)", r.status_code == 200, f"HTTP {r.status_code}", time.time() - t0)
    if r.status_code == 200:
        raw = r.text
        log(f"  SSE preview: {raw[:120].replace(chr(10),' ')}")

    # 20.2 Empty code → 422 validation error
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r2 = c.post("/agent/execute", json={"code": "", "notebook_id": nb_id})
    record("POST /agent/execute (empty code → 422)", r2.status_code == 422, f"HTTP {r2.status_code}", time.time() - t0)

    # 20.3 Run LLM-generated code via POST /agent/run-generated
    t0 = time.time()
    with httpx.Client(
        base_url=base_url,
        headers={"Authorization": f"Bearer {tok}"},
        timeout=60,
        cookies=state.get("cookies", {}),
        follow_redirects=True,
    ) as c:
        r3 = c.post("/agent/run-generated", json={
            "code": "result = sum(range(10))\nprint(f'Sum 0-9: {result}')",
            "language": "python",
            "notebook_id": nb_id,
            "timeout": 15,
        })
    record("POST /agent/run-generated (approved code)", r3.status_code == 200, f"HTTP {r3.status_code}", time.time() - t0)

    # 20.4 Run generated — unsupported language → 200 (SSE error event)
    t0 = time.time()
    with httpx.Client(
        base_url=base_url,
        headers={"Authorization": f"Bearer {tok}"},
        timeout=30,
        cookies=state.get("cookies", {}),
        follow_redirects=True,
    ) as c:
        r4 = c.post("/agent/run-generated", json={
            "code": "console.log('hi')",
            "language": "javascript",
            "notebook_id": nb_id,
        })
    record("POST /agent/run-generated (unsupported lang → SSE error)", r4.status_code == 200, f"HTTP {r4.status_code}", time.time() - t0)

    # 20.5 Agent execution status — non-existent → returns 200 with 'completed' (sync)
    t0 = time.time()
    fake_job = str(uuid.uuid4())
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r5 = c.get(f"/agent/status/{fake_job}")
    record("GET /agent/status/:job_id (non-existent → synthetic completed)", r5.status_code == 200, f"HTTP {r5.status_code}", time.time() - t0)

    # 20.6 List generated files — no session files yet → empty list
    t0 = time.time()
    fake_session = str(uuid.uuid4())
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r6 = c.get(f"/agent/files", params={"session_id": fake_session})
    record("GET /agent/files (no files → empty list)", r6.status_code == 200, f"HTTP {r6.status_code}", time.time() - t0)
    if r6.status_code == 200:
        record("Agent files — returns files array", "files" in r6.json(), str(r6.json())[:60])


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 21 — Agent: Data Analysis
# ══════════════════════════════════════════════════════════════════════════════
def test_agent_analyze(base_url: str, skip_slow: bool = False):
    section("SECTION 21 — Agent: Data Analysis")
    if skip_slow:
        log("Skipping (--skip-slow)", "WARN")
        return

    tok = state["access_token"]
    nb_id = state.get("notebook_id", "test-nb")

    # 21.1 Data-analysis request (SSE stream)
    t0 = time.time()
    with httpx.Client(
        base_url=base_url,
        headers={"Authorization": f"Bearer {tok}"},
        timeout=120,
        cookies=state.get("cookies", {}),
        follow_redirects=True,
    ) as c:
        r = c.post("/agent/analyze", json={
            "query": "Summarise the key numbers from the uploaded material",
            "notebook_id": nb_id,
            "material_ids": [state["material_id"]] if state.get("material_id") else [],
        })
    record("POST /agent/analyze (data analysis SSE)", r.status_code == 200, f"HTTP {r.status_code}", time.time() - t0)
    if r.status_code == 200:
        raw = r.text[:200].replace("\n", " ")
        log(f"  SSE preview: {raw}")

    # 21.2 Missing query → 422
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r2 = c.post("/agent/analyze", json={"notebook_id": nb_id})
    record("POST /agent/analyze (no query → 422)", r2.status_code == 422, f"HTTP {r2.status_code}", time.time() - t0)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 22 — Agent: Deep Research
# ══════════════════════════════════════════════════════════════════════════════
def test_agent_research(base_url: str, skip_slow: bool = False):
    section("SECTION 22 — Agent: Deep Research")
    if skip_slow:
        log("Skipping (--skip-slow)", "WARN")
        return

    tok = state["access_token"]
    nb_id = state.get("notebook_id", "test-nb")

    # 22.1 Deep research request (SSE stream)
    t0 = time.time()
    with httpx.Client(
        base_url=base_url,
        headers={"Authorization": f"Bearer {tok}"},
        timeout=180,
        cookies=state.get("cookies", {}),
        follow_redirects=True,
    ) as c:
        r = c.post("/agent/research", json={
            "query": "What are Kepler's three laws of planetary motion?",
            "notebook_id": nb_id,
            "material_ids": [state["material_id"]] if state.get("material_id") else [],
        })
    record("POST /agent/research (deep research SSE)", r.status_code == 200, f"HTTP {r.status_code}", time.time() - t0)
    if r.status_code == 200:
        raw = r.text[:200].replace("\n", " ")
        log(f"  SSE preview: {raw}")

    # 22.2 Missing query → 422
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r2 = c.post("/agent/research", json={"notebook_id": nb_id})
    record("POST /agent/research (no query → 422)", r2.status_code == 422, f"HTTP {r2.status_code}", time.time() - t0)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 23 — Chat: Intent Overrides (Agentic / WEB_SEARCH / WEB_RESEARCH / CODE)
# ══════════════════════════════════════════════════════════════════════════════
def test_chat_intent_overrides(base_url: str, skip_slow: bool = False):
    section("SECTION 23 — Chat: Intent Override Modes")
    if skip_slow:
        log("Skipping (--skip-slow)", "WARN")
        return
    if not state.get("material_ready"):
        log("Material not ready — skipping intent-override tests", "WARN")
        return

    tok = state["access_token"]
    mat_id = state["material_id"]
    nb_id = state["notebook_id"]

    # Shared helper: POST /chat with intent_override, consume SSE, check for non-error
    def _sse_chat(intent: str, message: str, timeout_s: int = 180):
        t0 = time.time()
        with httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {tok}"},
            timeout=timeout_s,
            cookies=state.get("cookies", {}),
            follow_redirects=True,
        ) as c:
            r = c.post("/chat", json={
                "material_id": mat_id,
                "notebook_id": nb_id,
                "message": message,
                "stream": True,
                "intent_override": intent,
            })
        dur = time.time() - t0
        ok = r.status_code == 200
        raw_snippet = r.text[:150].replace("\n", " ") if ok else r.text[:100]
        has_error_event = "event: error" in r.text if ok else False
        return ok, dur, raw_snippet, has_error_event

    # 23.1 AGENT intent
    ok, dur, snip, has_err = _sse_chat("AGENT", "Given the material, what are three key insights?", 180)
    record("POST /chat intent=AGENT (SSE 200)", ok, f"HTTP {'200' if ok else 'non-200'} err={has_err}", dur)
    if ok:
        log(f"  Preview: {snip}")

    # 23.2 WEB_RESEARCH intent (deep research pipeline)
    ok2, dur2, snip2, has_err2 = _sse_chat("WEB_RESEARCH", "Research the latest findings on Kepler's laws", 180)
    record("POST /chat intent=WEB_RESEARCH (SSE 200)", ok2, f"HTTP {'200' if ok2 else 'non-200'} err={has_err2}", dur2)

    # 23.3 WEB_SEARCH intent (quick search + summarize)
    ok3, dur3, snip3, has_err3 = _sse_chat("WEB_SEARCH", "Search: Johannes Kepler biography summary", 60)
    record("POST /chat intent=WEB_SEARCH (SSE 200)", ok3, f"HTTP {'200' if ok3 else 'non-200'} err={has_err3}", dur3)

    # 23.4 CODE_EXECUTION intent
    ok4, dur4, snip4, has_err4 = _sse_chat("CODE_EXECUTION", "Write and run Python code to compute orbit period using T^2 = a^3", 120)
    record("POST /chat intent=CODE_EXECUTION (SSE 200)", ok4, f"HTTP {'200' if ok4 else 'non-200'} err={has_err4}", dur4)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 24 — Chat: Block Follow-Up
# ══════════════════════════════════════════════════════════════════════════════
def test_chat_block_followup(base_url: str, skip_slow: bool = False):
    section("SECTION 24 — Chat: Block Follow-Up")
    if skip_slow:
        log("Skipping (--skip-slow)", "WARN")
        return

    tok = state["access_token"]

    # 24.1 Non-existent block → 404
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r = c.post("/chat/block-followup", json={
            "block_id": str(uuid.uuid4()),
            "question": "Can you explain this in simpler terms?",
            "action": "simplify",
        })
    record("POST /chat/block-followup (invalid block → 404)", r.status_code == 404, f"HTTP {r.status_code}", time.time() - t0)

    # 24.2 Missing required fields → 422
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r2 = c.post("/chat/block-followup", json={"action": "ask"})
    record("POST /chat/block-followup (missing fields → 422)", r2.status_code == 422, f"HTTP {r2.status_code}", time.time() - t0)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 25 — Materials: Text Retrieval & Edge Cases
# ══════════════════════════════════════════════════════════════════════════════
def test_material_text(base_url: str):
    section("SECTION 25 — Material Text Retrieval & Edge Cases")
    tok = state["access_token"]

    # 25.1 Get text of processed material
    mat_id = state.get("material_id")
    if mat_id and state.get("material_ready"):
        t0 = time.time()
        with make_client(base_url, tok, state.get("cookies", {})) as c:
            r = c.get(f"/materials/{mat_id}/text")
        if check_response("GET /materials/:id/text (completed material)", r, 200, t0):
            body = r.json()
            text = body.get("text", "")
            record("Material text — non-empty content", len(text) > 10, f"chars={len(text)}")
            log(f"  Text excerpt: {text[:80].replace(chr(10),' ')}")
    else:
        log("Skipping material text test (material not ready)", "WARN")

    # 25.2 Non-existent material → 404
    t0 = time.time()
    fake_id = str(uuid.uuid4())
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r2 = c.get(f"/materials/{fake_id}/text")
    record("GET /materials/:id/text (non-existent → 404)", r2.status_code == 404, f"HTTP {r2.status_code}", time.time() - t0)

    # 25.3 List all materials (no notebook filter)
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r3 = c.get("/materials")
    if check_response("GET /materials (no notebook filter)", r3, 200, t0):
        all_mats = r3.json()
        record("Materials list — is a list", isinstance(all_mats, list), f"count={len(all_mats)}")

    # 25.4 Non-existent material patch → 404
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r4 = c.patch(f"/materials/{fake_id}", json={"title": "Ghost"})
    record("PATCH /materials/:id (non-existent → 404)", r4.status_code == 404, f"HTTP {r4.status_code}", time.time() - t0)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 26 — Explainer: Full Pipeline (Generate → Poll)
# ══════════════════════════════════════════════════════════════════════════════
def test_explainer_full(base_url: str, skip_slow: bool = False):
    section("SECTION 26 — Explainer: Full Pipeline")
    if skip_slow:
        log("Skipping (--skip-slow)", "WARN")
        return
    if not state.get("material_ready"):
        log("Material not ready — skipping explainer pipeline tests", "WARN")
        return

    tok = state["access_token"]
    nb_id = state["notebook_id"]
    mat_id = state["material_id"]

    # 26.1 Start explainer generation
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r = c.post("/explainer/generate", json={
            "material_ids": [mat_id],
            "notebook_id": nb_id,
            "ppt_language": "en",
            "narration_language": "en",
            "voice_gender": "female",
            "create_new_ppt": True,
        }, timeout=300)
    if check_response("POST /explainer/generate (start)", r, 200, t0):
        body = r.json()
        state["explainer_id"] = body.get("explainer_id")
        est = body.get("estimated_time_minutes", "?")
        log(f"  Explainer job started: id={state['explainer_id']} est={est}m")

    # 26.2 Poll explainer status (don't wait — just verify endpoint responds)
    if state.get("explainer_id"):
        t0 = time.time()
        with make_client(base_url, tok, state.get("cookies", {})) as c:
            r2 = c.get(f"/explainer/{state['explainer_id']}/status")
        if check_response("GET /explainer/:id/status (poll)", r2, 200, t0):
            body2 = r2.json()
            log(f"  Status: {body2.get('status')} progress={body2.get('progress')}%")
            record(
                "Explainer status — valid status field",
                body2.get("status") in ("pending", "capturing_slides", "generating_script",
                                        "generating_audio", "composing_video", "completed", "failed"),
                f"status={body2.get('status')}",
            )

    # 26.3 Non-existent explainer → 404
    t0 = time.time()
    fake_id = str(uuid.uuid4())
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r3 = c.get(f"/explainer/{fake_id}/status")
    record("GET /explainer/:id/status (non-existent → 404)", r3.status_code == 404, f"HTTP {r3.status_code}", time.time() - t0)

    # 26.4 Video not ready → 400 (status != completed)
    if state.get("explainer_id"):
        t0 = time.time()
        with make_client(base_url, tok, state.get("cookies", {})) as c:
            r4 = c.get(f"/explainer/{state['explainer_id']}/video")
        record(
            "GET /explainer/:id/video (not completed → 400 or 404)",
            r4.status_code in (400, 404),
            f"HTTP {r4.status_code}",
            time.time() - t0,
        )

    # 26.5 Unsupported language → 400
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r5 = c.post("/explainer/generate", json={
            "material_ids": [mat_id],
            "notebook_id": nb_id,
            "ppt_language": "xx-invalid",
            "narration_language": "en",
            "voice_gender": "female",
        }, timeout=30)
    record("POST /explainer/generate (invalid language → 400)", r5.status_code == 400, f"HTTP {r5.status_code}", time.time() - t0)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 27 — Podcast: Full Session Lifecycle
# ══════════════════════════════════════════════════════════════════════════════
def test_podcast_full(base_url: str, skip_slow: bool = False):
    section("SECTION 27 — Podcast: Full Session Lifecycle")
    if skip_slow:
        log("Skipping (--skip-slow)", "WARN")
        return
    if not state.get("material_ready"):
        log("Material not ready — skipping podcast lifecycle tests", "WARN")
        return

    tok = state["access_token"]
    nb_id = state["notebook_id"]
    mat_id = state["material_id"]

    # Reuse session created in section 12 or create a fresh one
    sess_id = state.get("podcast_session_id")
    if not sess_id:
        t0 = time.time()
        with make_client(base_url, tok, state.get("cookies", {})) as c:
            r_c = c.post("/podcast/session", json={
                "notebook_id": nb_id,
                "mode": "overview",
                "language": "en",
                "material_ids": [mat_id],
            }, timeout=60)
        if check_response("POST /podcast/session (create — section 27)", r_c, 200, t0):
            sess_id = r_c.json().get("id") or r_c.json().get("session_id")
            state["podcast_session_id"] = sess_id

    if not sess_id:
        log("Could not obtain a podcast session — skipping lifecycle tests", "WARN")
        return

    # 27.1 Get session by ID
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r1 = c.get(f"/podcast/session/{sess_id}")
    if check_response("GET /podcast/session/:id", r1, 200, t0):
        log(f"  Session state: {str(r1.json())[:80]}")

    # 27.2 Update session title and tags
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r2 = c.patch(f"/podcast/session/{sess_id}", json={
            "title": f"Updated Podcast {_RUN_ID}",
            "tags": ["test", "kepler", "automated"],
        })
    check_response("PATCH /podcast/session/:id (title+tags)", r2, 200, t0)

    # 27.3 Get all voices (all languages)
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r3 = c.get("/podcast/voices/all")
    if check_response("GET /podcast/voices/all", r3, 200, t0):
        all_voices = r3.json()
        record("Podcast voices/all — non-empty", bool(all_voices), f"keys={list(all_voices.keys())[:3]}")

    # 27.4 Start podcast generation
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r4 = c.post(f"/podcast/session/{sess_id}/start", timeout=120)
    record(
        "POST /podcast/session/:id/start (kick off generation)",
        r4.status_code in (200, 400),  # 400 = already started / no materials ready
        f"HTTP {r4.status_code}",
        time.time() - t0,
    )
    if r4.status_code == 200:
        log(f"  Generation started: {r4.json()}")

    # 27.5 Add a bookmark
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r5 = c.post(f"/podcast/session/{sess_id}/bookmark", json={
            "segment_index": 0,
            "label": "Intro highlight",
        })
    if check_response("POST /podcast/session/:id/bookmark (add)", r5, 200, t0):
        state["podcast_bookmark_id"] = r5.json().get("id")
        log(f"  Bookmark id: {state['podcast_bookmark_id']}")

    # 27.6 Get bookmarks
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r6 = c.get(f"/podcast/session/{sess_id}/bookmarks")
    if check_response("GET /podcast/session/:id/bookmarks", r6, 200, t0):
        bm_count = len(r6.json())
        record("Podcast bookmarks — has at least 1", bm_count >= 1, f"count={bm_count}")

    # 27.7 Delete bookmark
    bm_id = state.get("podcast_bookmark_id")
    if bm_id:
        t0 = time.time()
        with make_client(base_url, tok, state.get("cookies", {})) as c:
            r7 = c.delete(f"/podcast/session/{sess_id}/bookmark/{bm_id}")
        check_response("DELETE /podcast/session/:id/bookmark/:bm_id", r7, 200, t0)

    # 27.8 Add an annotation
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r8 = c.post(f"/podcast/session/{sess_id}/annotation", json={
            "segment_index": 0,
            "note": "Interesting point about orbital mechanics",
        })
    if check_response("POST /podcast/session/:id/annotation (add)", r8, 200, t0):
        state["podcast_annotation_id"] = r8.json().get("id")
        log(f"  Annotation id: {state['podcast_annotation_id']}")

    # 27.9 Delete annotation
    ann_id = state.get("podcast_annotation_id")
    if ann_id:
        t0 = time.time()
        with make_client(base_url, tok, state.get("cookies", {})) as c:
            r9 = c.delete(f"/podcast/session/{sess_id}/annotation/{ann_id}")
        check_response("DELETE /podcast/session/:id/annotation/:ann_id", r9, 200, t0)

    # 27.10 Get doubts / Q&A history (may be empty)
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r10 = c.get(f"/podcast/session/{sess_id}/doubts")
    check_response("GET /podcast/session/:id/doubts", r10, 200, t0)

    # 27.11 Trigger JSON export
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r11 = c.post(f"/podcast/session/{sess_id}/export", json={"format": "json"})
    if check_response("POST /podcast/session/:id/export (JSON)", r11, 200, t0):
        state["podcast_export_id"] = r11.json().get("id") or r11.json().get("export_id")
        log(f"  Export id: {state['podcast_export_id']}")

    # 27.12 Poll export status
    if state.get("podcast_export_id"):
        t0 = time.time()
        with make_client(base_url, tok, state.get("cookies", {})) as c:
            r12 = c.get(f"/podcast/export/{state['podcast_export_id']}")
        check_response("GET /podcast/export/:export_id (status)", r12, 200, t0)

    # 27.13 Generate session summary card
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r13 = c.post(f"/podcast/session/{sess_id}/summary", timeout=120)
    record(
        "POST /podcast/session/:id/summary",
        r13.status_code in (200, 400),  # 400 if no segments yet
        f"HTTP {r13.status_code}",
        time.time() - t0,
    )

    # 27.14 Non-existent session → 404
    t0 = time.time()
    fake_sess = str(uuid.uuid4())
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r14 = c.get(f"/podcast/session/{fake_sess}")
    record("GET /podcast/session/:id (non-existent → 404)", r14.status_code == 404, f"HTTP {r14.status_code}", time.time() - t0)

    # 27.15 Create podcast in topic/deep-dive mode (missing topic → 400)
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r15 = c.post("/podcast/session", json={
            "notebook_id": nb_id,
            "mode": "deep-dive",
            "language": "en",
            "material_ids": [mat_id],
            # topic intentionally omitted
        }, timeout=30)
    record("POST /podcast/session (deep-dive, no topic → 400)", r15.status_code == 400, f"HTTP {r15.status_code}", time.time() - t0)

    # 27.16 Delete the podcast session
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r16 = c.delete(f"/podcast/session/{sess_id}")
    check_response("DELETE /podcast/session/:id", r16, 200, t0)
    state.pop("podcast_session_id", None)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 28 — Models: Reload (Admin Guard)
# ══════════════════════════════════════════════════════════════════════════════
def test_models_reload(base_url: str):
    section("SECTION 28 — Models: Reload Endpoint (Admin Guard)")
    tok = state["access_token"]

    # 28.1 Regular user → 403 Forbidden
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r = c.post("/models/reload")
    record("POST /models/reload (non-admin → 403)", r.status_code == 403, f"HTTP {r.status_code}", time.time() - t0)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 29 — MindMap: Delete & 404 Guards
# ══════════════════════════════════════════════════════════════════════════════
def test_mindmap_delete(base_url: str):
    section("SECTION 29 — MindMap: Delete & Error Guards")
    tok = state["access_token"]
    nb_id = state.get("notebook_id")

    # 29.1 Generate a fresh mindmap to get its ID for deletion
    if state.get("material_ready") and nb_id:
        t0 = time.time()
        with make_client(base_url, tok, state.get("cookies", {})) as c:
            r = c.post("/mindmap", json={
                "material_ids": [state["material_id"]],
                "notebook_id": nb_id,
            }, timeout=600)
        if check_response("POST /mindmap (for delete test)", r, 200, t0):
            nodes = r.json().get("nodes", [])
            log(f"  Generated mindmap with {len(nodes)} nodes for deletion test")
    else:
        log("Material not ready — skipping mindmap delete generate step", "WARN")

    # 29.2 Get saved mindmap — should now be 200 or 404
    if nb_id:
        t0 = time.time()
        with make_client(base_url, tok, state.get("cookies", {})) as c:
            r2 = c.get(f"/mindmap/{nb_id}")
        record("GET /mindmap/:notebook_id (after generate)", r2.status_code in (200, 404), f"HTTP {r2.status_code}", time.time() - t0)
        if r2.status_code == 200:
            mm_data = r2.json()
            state["mindmap_id_to_delete"] = mm_data.get("id")

    # 29.3 Delete mindmap by ID (if we got one)
    mm_delete_id = state.get("mindmap_id_to_delete")
    if mm_delete_id:
        t0 = time.time()
        with make_client(base_url, tok, state.get("cookies", {})) as c:
            r3 = c.delete(f"/mindmap/{mm_delete_id}")
        check_response("DELETE /mindmap/:id", r3, 200, t0)
    else:
        log("No mindmap ID available for deletion test", "WARN")

    # 29.4 Delete non-existent mindmap → 404
    t0 = time.time()
    fake_mm = str(uuid.uuid4())
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r4 = c.delete(f"/mindmap/{fake_mm}")
    record("DELETE /mindmap/:id (non-existent → 404)", r4.status_code == 404, f"HTTP {r4.status_code}", time.time() - t0)

    # 29.5 MindMap requires material_ids → 400
    if nb_id:
        t0 = time.time()
        with make_client(base_url, tok, state.get("cookies", {})) as c:
            r5 = c.post("/mindmap", json={"notebook_id": nb_id, "material_ids": []}, timeout=30)
        record("POST /mindmap (empty material_ids → 400)", r5.status_code == 400, f"HTTP {r5.status_code}", time.time() - t0)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 30 — Notebook Pagination & 404 Guards
# ══════════════════════════════════════════════════════════════════════════════
def test_notebook_pagination(base_url: str):
    section("SECTION 30 — Notebook Pagination & Error Guards")
    tok = state["access_token"]

    # 30.1 Pagination — skip/take
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r = c.get("/notebooks?skip=0&take=2")
    if check_response("GET /notebooks (skip=0 take=2)", r, 200, t0):
        nb_list = r.json()
        record("Notebooks pagination — list ≤ 2", len(nb_list) <= 2, f"returned={len(nb_list)}")

    # 30.2 skip=1000000 → empty list (not 4xx)
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r2 = c.get("/notebooks?skip=1000000&take=10")
    if check_response("GET /notebooks (skip=1000000 → empty)", r2, 200, t0):
        record("Notebooks pagination — deep skip yields empty list", r2.json() == [], f"got={r2.json()}")

    # 30.3 Non-existent notebook → 404
    t0 = time.time()
    fake_nb = str(uuid.uuid4())
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r3 = c.get(f"/notebooks/{fake_nb}")
    record("GET /notebooks/:id (non-existent → 404)", r3.status_code == 404, f"HTTP {r3.status_code}", time.time() - t0)

    # 30.4 Update non-existent notebook → 404
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r4 = c.put(f"/notebooks/{fake_nb}", json={"name": "Ghost"})
    record("PUT /notebooks/:id (non-existent → 404)", r4.status_code == 404, f"HTTP {r4.status_code}", time.time() - t0)

    # 30.5 Delete non-existent notebook → 404
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r5 = c.delete(f"/notebooks/{fake_nb}")
    record("DELETE /notebooks/:id (non-existent → 404)", r5.status_code == 404, f"HTTP {r5.status_code}", time.time() - t0)

    # 30.6 take=0 → 422 (ge=1 constraint)
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r6 = c.get("/notebooks?take=0")
    record("GET /notebooks (take=0 → 422)", r6.status_code == 422, f"HTTP {r6.status_code}", time.time() - t0)

    # 30.7 take=201 → 422 (le=200 constraint)
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r7 = c.get("/notebooks?take=201")
    record("GET /notebooks (take=201 → 422)", r7.status_code == 422, f"HTTP {r7.status_code}", time.time() - t0)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 31 — Search: Enhanced (File-Type Filter & Engine Selection)
# ══════════════════════════════════════════════════════════════════════════════
def test_search_enhanced(base_url: str):
    section("SECTION 31 — Search: Enhanced Filters")
    tok = state["access_token"]

    # 31.1 Search with file_type filter (PDF)
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r = c.post("/search/web", json={
            "query": "Kepler laws of planetary motion",
            "file_type": "pdf",
            "engine": "duckduckgo",
        }, timeout=30)
    record("POST /search/web (filetype=pdf filter)", r.status_code in (200, 502, 503), f"HTTP {r.status_code}", time.time() - t0)
    if r.status_code == 200:
        log(f"  Results: {len(r.json())}")

    # 31.2 Empty query → 422 (implicitly required by Pydantic)
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r2 = c.post("/search/web", json={"engine": "duckduckgo"})
    record("POST /search/web (missing query → 422)", r2.status_code == 422, f"HTTP {r2.status_code}", time.time() - t0)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 32 — PPT: Async Background Job & File Download
# ══════════════════════════════════════════════════════════════════════════════
def test_ppt_extended(base_url: str, skip_slow: bool = False):
    section("SECTION 32 — PPT: Extended Validation")
    if skip_slow:
        log("Skipping (--skip-slow)", "WARN")
        return
    if not state.get("material_ready"):
        log("Material not ready — skipping PPT extended tests", "WARN")
        return

    tok = state["access_token"]
    mat_id = state["material_id"]
    nb_id = state["notebook_id"]

    # 32.1 PPT with all optional params — explicit slide count and custom instructions
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r = c.post("/presentation", json={
            "material_id": mat_id,
            "max_slides": 4,
            "theme": "dark blue gradient",
            "additional_instructions": "Include a title slide and a summary slide.",
        }, timeout=600)
    if check_response("POST /presentation (all options: slides+theme+instructions)", r, 200, t0):
        ppt = r.json()
        slides = ppt.get("slides") or ppt.get("data", {}).get("slides") or []
        html = ppt.get("html") or ppt.get("data", {}).get("html") or ""
        record("PPT all-options — has slides or HTML", len(slides) > 0 or len(html) > 100,
               f"slides={len(slides)} html_len={len(html)}")

    # 32.2 max_slides=2 → 422 (ge=3)
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r2 = c.post("/presentation", json={"material_id": mat_id, "max_slides": 2}, timeout=30)
    record("POST /presentation (max_slides=2 → 422)", r2.status_code == 422, f"HTTP {r2.status_code}", time.time() - t0)

    # 32.3 max_slides=61 → 422 (le=60)
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r3 = c.post("/presentation", json={"material_id": mat_id, "max_slides": 61}, timeout=30)
    record("POST /presentation (max_slides=61 → 422)", r3.status_code == 422, f"HTTP {r3.status_code}", time.time() - t0)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 33 — Flashcard & Quiz: Additional Validation
# ══════════════════════════════════════════════════════════════════════════════
def test_flashcard_quiz_validation(base_url: str, skip_slow: bool = False):
    section("SECTION 33 — Flashcard & Quiz: Boundary Validation")
    if skip_slow:
        log("Skipping (--skip-slow)", "WARN")
        return

    tok = state["access_token"]

    # 33.1 Flashcard card_count=0 → 422 (ge=1)
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r = c.post("/flashcard", json={
            "material_id": state.get("material_id", str(uuid.uuid4())),
            "card_count": 0,
        }, timeout=30)
    record("POST /flashcard (card_count=0 → 422)", r.status_code == 422, f"HTTP {r.status_code}", time.time() - t0)

    # 33.2 Flashcard card_count=151 → 422 (le=150)
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r2 = c.post("/flashcard", json={
            "material_id": state.get("material_id", str(uuid.uuid4())),
            "card_count": 151,
        }, timeout=30)
    record("POST /flashcard (card_count=151 → 422)", r2.status_code == 422, f"HTTP {r2.status_code}", time.time() - t0)

    # 33.3 Quiz mcq_count=0 → 422 (ge=1)
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r3 = c.post("/quiz", json={
            "material_id": state.get("material_id", str(uuid.uuid4())),
            "mcq_count": 0,
        }, timeout=30)
    record("POST /quiz (mcq_count=0 → 422)", r3.status_code == 422, f"HTTP {r3.status_code}", time.time() - t0)

    # 33.4 Quiz mcq_count=151 → 422 (le=150)
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r4 = c.post("/quiz", json={
            "material_id": state.get("material_id", str(uuid.uuid4())),
            "mcq_count": 151,
        }, timeout=30)
    record("POST /quiz (mcq_count=151 → 422)", r4.status_code == 422, f"HTTP {r4.status_code}", time.time() - t0)

    # 33.5 Flashcard with additional_instructions
    if state.get("material_ready"):
        t0 = time.time()
        with make_client(base_url, tok, state.get("cookies", {})) as c:
            r5 = c.post("/flashcard", json={
                "material_id": state["material_id"],
                "card_count": 3,
                "difficulty": "hard",
                "additional_instructions": "Focus on mathematical formulas only.",
            }, timeout=180)
        if check_response("POST /flashcard (hard + additional_instructions)", r5, 200, t0):
            cards = r5.json().get("flashcards") or r5.json().get("cards") or []
            record("Flashcard + instructions — returns cards", len(cards) > 0, f"count={len(cards)}")


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 34 — Upload: Edge Cases (YouTube, oversized, invalid type)
# ══════════════════════════════════════════════════════════════════════════════
def test_upload_edge_cases(base_url: str):
    section("SECTION 34 — Upload: Edge Cases")
    tok = state["access_token"]
    nb_id = state.get("notebook_id")

    # 34.1 YouTube URL upload
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r = c.post("/upload/url", json={
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "notebook_id": nb_id,
            "source_type": "youtube",
            "title": "YouTube test video",
        })
    record("POST /upload/url (YouTube)", r.status_code in (202, 400, 422, 500), f"HTTP {r.status_code}", time.time() - t0)
    if r.status_code == 202:
        state["yt_material_id"] = r.json().get("material_id")
        log(f"  YouTube material: {state['yt_material_id']}")

    # 34.2 Upload invalid file type (binary exe disguised)
    t0 = time.time()
    fake_exe = b"MZ\x90\x00" + b"\x00" * 100  # DOS/PE magic bytes
    with httpx.Client(
        base_url=base_url,
        headers={"Authorization": f"Bearer {tok}"},
        timeout=30,
        cookies=state.get("cookies", {}),
        follow_redirects=True,
    ) as c:
        r2 = c.post(
            "/upload",
            data={"notebook_id": nb_id},
            files={"file": ("malware.exe", fake_exe, "application/octet-stream")},
        )
    record("POST /upload (exe file → 400/422)", r2.status_code in (400, 422), f"HTTP {r2.status_code}", time.time() - t0)

    # 34.3 Text upload with empty text → 422
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r3 = c.post("/upload/text", json={
            "text": "",
            "title": "Empty text",
            "notebook_id": nb_id,
        })
    record("POST /upload/text (empty text → 422/400)", r3.status_code in (400, 422), f"HTTP {r3.status_code}", time.time() - t0)

    # 34.4 URL upload with invalid URL → 400/422
    t0 = time.time()
    with make_client(base_url, tok, state.get("cookies", {})) as c:
        r4 = c.post("/upload/url", json={
            "url": "not-a-valid-url",
            "notebook_id": nb_id,
        })
    record("POST /upload/url (invalid URL → 400/422)", r4.status_code in (400, 422), f"HTTP {r4.status_code}", time.time() - t0)


# ══════════════════════════════════════════════════════════════════════════════
#  SECTION 35 — Auth: Username Validation
# ══════════════════════════════════════════════════════════════════════════════
def test_auth_edge_cases(base_url: str):
    section("SECTION 35 — Auth: Username & Password Edge Cases")

    # 35.1 Username too short (1 char) → 422
    t0 = time.time()
    with httpx.Client(base_url=base_url, timeout=TIMEOUT) as c:
        r = c.post("/auth/signup", json={
            "email": f"short_{_RUN_ID}@test.com",
            "username": "x",
            "password": "ValidPass1!",
        })
    record("POST /auth/signup (username=1 char → 422)", r.status_code == 422, f"HTTP {r.status_code}", time.time() - t0)

    # 35.2 Username too long (51 chars) → 422
    t0 = time.time()
    with httpx.Client(base_url=base_url, timeout=TIMEOUT) as c:
        r2 = c.post("/auth/signup", json={
            "email": f"long_{_RUN_ID}@test.com",
            "username": "a" * 51,
            "password": "ValidPass1!",
        })
    record("POST /auth/signup (username=51 chars → 422)", r2.status_code == 422, f"HTTP {r2.status_code}", time.time() - t0)

    # 35.3 Password missing uppercase → 422
    t0 = time.time()
    with httpx.Client(base_url=base_url, timeout=TIMEOUT) as c:
        r3 = c.post("/auth/signup", json={
            "email": f"noupper_{_RUN_ID}@test.com",
            "username": "noupper",
            "password": "nouppercase1",
        })
    record("POST /auth/signup (no uppercase → 422)", r3.status_code == 422, f"HTTP {r3.status_code}", time.time() - t0)

    # 35.4 Password missing digit → 422
    t0 = time.time()
    with httpx.Client(base_url=base_url, timeout=TIMEOUT) as c:
        r4 = c.post("/auth/signup", json={
            "email": f"nodigit_{_RUN_ID}@test.com",
            "username": "nodigit",
            "password": "NoDigitAtAll!",
        })
    record("POST /auth/signup (no digit → 422)", r4.status_code == 422, f"HTTP {r4.status_code}", time.time() - t0)

    # 35.5 Login with non-existent email → 401
    t0 = time.time()
    with httpx.Client(base_url=base_url, timeout=TIMEOUT) as c:
        r5 = c.post("/auth/login", json={
            "email": f"ghost_{_RUN_ID}@nowhere.com",
            "password": "SomePass1!",
        })
    record("POST /auth/login (non-existent email → 401)", r5.status_code == 401, f"HTTP {r5.status_code}", time.time() - t0)


# ══════════════════════════════════════════════════════════════════════════════
#  FINAL REPORT
# ══════════════════════════════════════════════════════════════════════════════
def print_report():
    section("FINAL TEST REPORT")
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    failed = total - passed

    print()
    if HAS_RICH:
        table = Table(title="Test Results", show_lines=True)
        table.add_column("Test", style="cyan", no_wrap=False, max_width=60)
        table.add_column("Status", justify="center")
        table.add_column("Duration", justify="right", style="dim")
        table.add_column("Detail", style="dim", no_wrap=False, max_width=50)
        for r in results:
            status = "[green]PASS[/green]" if r.passed else "[red]FAIL[/red]"
            table.add_row(r.name, status, f"{r.duration:.2f}s", r.detail[:80])
        console.print(table)
    else:
        for r in results:
            icon = _green("PASS") if r.passed else _red("FAIL")
            print(f"  [{icon}] {r.name:<60} {r.detail[:50]}")

    print()
    print("─" * 60)
    print(f"  Total : {total}")
    print(f"  {_green('Passed')}: {passed}")
    if failed > 0:
        print(f"  {_red('Failed')}: {failed}")
    else:
        print(f"  {_green('Failed')}: {failed}")
    print("─" * 60)

    if failed > 0:
        print(_red(f"\n  ✘ {failed} test(s) FAILED\n"))
        print("  Failed tests:")
        for r in results:
            if not r.passed:
                print(f"    • {r.name}: {r.detail}")
    else:
        print(_green("\n  ✔ All tests PASSED!\n"))

    return failed == 0

# ══════════════════════════════════════════════════════════════════════════════
#  SECTION RUNNER — isolates each section so a timeout/crash doesn't abort all
# ══════════════════════════════════════════════════════════════════════════════
def _run_section(idx: int, fn):
    """Run one test section, recording a FAIL entry on unexpected exceptions."""
    try:
        fn()
    except KeyboardInterrupt:
        raise
    except SystemExit:
        raise
    except Exception as e:
        import traceback
        section_name = f"SECTION {idx}"
        record(
            f"{section_name} — unexpected crash",
            False,
            f"{type(e).__name__}: {e}",
        )
        log(f"{section_name} crashed: {type(e).__name__}: {e}", "FAIL")
        traceback.print_exc()


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="KeplerLab Full E2E Test Suite")
    parser.add_argument("--base", default=BASE_URL, help="Backend base URL")
    parser.add_argument("--skip-slow", action="store_true", help="Skip LLM-dependent tests")
    parser.add_argument("--section", type=int, default=0, help="Run specific section only (0=all)")
    args = parser.parse_args()

    base = args.base.rstrip("/")
    skip_slow = args.skip_slow

    print(_bold("\n╔══════════════════════════════════════════════════════════╗"))
    print(_bold("║   KeplerLab — Comprehensive End-to-End Test Suite        ║"))
    print(_bold("╚══════════════════════════════════════════════════════════╝"))
    print(f"  Backend  : {base}")
    print(f"  PDF      : {PDF_PATH}")
    print(f"  Run ID   : {_RUN_ID}")
    print(f"  Skip slow: {skip_slow}")
    print()

    try:
        all_sections = {
            0:  lambda: test_preflight(base),
            1:  lambda: test_auth(base),
            2:  lambda: test_health_and_models(base),
            3:  lambda: test_notebooks(base),
            4:  lambda: test_upload_and_processing(base),
            5:  lambda: test_url_upload(base),
            6:  lambda: test_flashcards(base, skip_slow),
            7:  lambda: test_quiz(base, skip_slow),
            8:  lambda: test_chat(base, skip_slow),
            9:  lambda: test_mindmap(base, skip_slow),
            10: lambda: test_ppt(base, skip_slow),
            11: lambda: test_notebook_content(base),
            12: lambda: test_podcast(base, skip_slow),
            13: lambda: test_explainer(base, skip_slow),
            14: lambda: test_search(base),
            15: lambda: test_material_delete(base),
            16: lambda: test_jobs(base),
            17: lambda: test_logout(base),
            18: lambda: test_input_validation(base),
            19: lambda: test_multi_material(base, skip_slow),
            # ── New sections ──────────────────────────────────────
            20: lambda: test_agent_execute(base, skip_slow),
            21: lambda: test_agent_analyze(base, skip_slow),
            22: lambda: test_agent_research(base, skip_slow),
            23: lambda: test_chat_intent_overrides(base, skip_slow),
            24: lambda: test_chat_block_followup(base, skip_slow),
            25: lambda: test_material_text(base),
            26: lambda: test_explainer_full(base, skip_slow),
            27: lambda: test_podcast_full(base, skip_slow),
            28: lambda: test_models_reload(base),
            29: lambda: test_mindmap_delete(base),
            30: lambda: test_notebook_pagination(base),
            31: lambda: test_search_enhanced(base),
            32: lambda: test_ppt_extended(base, skip_slow),
            33: lambda: test_flashcard_quiz_validation(base, skip_slow),
            34: lambda: test_upload_edge_cases(base),
            35: lambda: test_auth_edge_cases(base),
        }

        if args.section != 0 and args.section in all_sections:
            # If running a specific section, run auth first
            _run_section(0, all_sections[0])
            if args.section != 1:
                _run_section(1, all_sections[1])
            _run_section(args.section, all_sections[args.section])
        else:
            for idx in sorted(all_sections.keys()):
                _run_section(idx, all_sections[idx])

    except KeyboardInterrupt:
        print(_yellow("\n  Interrupted by user."))
    except SystemExit:
        raise
    except Exception as e:
        print(_red(f"\n  UNEXPECTED ERROR: {e}"))
        import traceback
        traceback.print_exc()

    success = print_report()

    # Write JSON report
    report_path = f"test_report_{_RUN_ID}.json"
    with open(report_path, "w") as f:
        json.dump({
            "run_id": _RUN_ID,
            "base_url": args.base,
            "skip_slow": skip_slow,
            "total": len(results),
            "passed": sum(1 for r in results if r.passed),
            "failed": sum(1 for r in results if not r.passed),
            "results": [
                {"name": r.name, "passed": r.passed, "detail": r.detail, "duration": round(r.duration, 3)}
                for r in results
            ],
        }, f, indent=2)
    print(f"  Report saved: {report_path}\n")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
