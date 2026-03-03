#!/usr/bin/env python3
"""
KeplerLab Pipeline Health Check
================================
Tests every core API pipeline to verify they are working end-to-end.

Usage:
  python check_pipeline.py [--url URL] [--email EMAIL] [--password PASSWORD]

Environment variables (fallbacks):
  KEPLER_URL      Base URL of the backend  (default: http://localhost:8000)
  KEPLER_EMAIL    Registered user email
  KEPLER_PASSWORD Registered user password

Flags:
  --skip-heavy    Skip slow generation tests (mindmap, quiz, flashcard)
  --notebook-id   Use an existing notebook ID instead of creating a new one
  --material-id   Use an existing material ID instead of uploading
  --no-cleanup    Don't delete test notebook/material at the end
"""

import argparse
import json
import os
import sys
import time
import textwrap
from typing import Any, Optional

try:
    import requests
except ImportError:
    print("ERROR: 'requests' is not installed. Run: pip install requests")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Colour helpers (ANSI, disabled on Windows or when not a TTY)
# ─────────────────────────────────────────────────────────────────────────────
_USE_COLOUR = sys.stdout.isatty() and os.name != "nt"

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOUR else text

def OK(s="OK"):    return _c("32;1", f"✓ {s}")
def FAIL(s="FAIL"): return _c("31;1", f"✗ {s}")
def WARN(s):       return _c("33;1", f"⚠ {s}")
def BOLD(s):       return _c("1", s)
def DIM(s):        return _c("2", s)

# ─────────────────────────────────────────────────────────────────────────────
# Result accumulator
# ─────────────────────────────────────────────────────────────────────────────
results: list[dict] = []

def record(name: str, passed: bool, duration: float, detail: str = ""):
    results.append({"name": name, "passed": passed, "duration": duration, "detail": detail})
    status = OK() if passed else FAIL()
    row = f"  {status}  {name:<45} {duration:>6.2f}s"
    if detail:
        row += f"  {DIM(detail[:80])}"
    print(row)


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helpers
# ─────────────────────────────────────────────────────────────────────────────
class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers["Content-Type"] = "application/json"
        self.token: Optional[str] = None

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _auth(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def get(self, path: str, **kw) -> requests.Response:
        return self.session.get(self._url(path), headers=self._auth(), **kw)

    def post(self, path: str, payload: Any = None, files=None, **kw) -> requests.Response:
        if files:
            # multipart — don't use JSON content-type
            hdrs = {k: v for k, v in self._auth().items()}
            return self.session.post(self._url(path), headers=hdrs, files=files, **kw)
        return self.session.post(
            self._url(path), headers=self._auth(),
            data=json.dumps(payload) if payload is not None else None,
            **kw,
        )

    def delete(self, path: str, **kw) -> requests.Response:
        return self.session.delete(self._url(path), headers=self._auth(), **kw)


# ─────────────────────────────────────────────────────────────────────────────
# Individual test functions
# ─────────────────────────────────────────────────────────────────────────────

def test_health(client: APIClient) -> bool:
    t0 = time.perf_counter()
    try:
        r = client.get("/health/simple", timeout=10)
        ok = r.status_code == 200
        record("GET /health/simple", ok, time.perf_counter() - t0,
               f"HTTP {r.status_code}" if not ok else "")
        return ok
    except Exception as e:
        record("GET /health/simple", False, time.perf_counter() - t0, str(e))
        return False


def test_login(client: APIClient, email: str, password: str) -> bool:
    t0 = time.perf_counter()
    try:
        r = client.post("/login", {"email": email, "password": password}, timeout=15)
        if r.status_code == 200:
            client.token = r.json().get("access_token")
            ok = bool(client.token)
        else:
            ok = False
        record("POST /login", ok, time.perf_counter() - t0,
               f"HTTP {r.status_code}" if not ok else "token acquired")
        return ok
    except Exception as e:
        record("POST /login", False, time.perf_counter() - t0, str(e))
        return False


def test_list_notebooks(client: APIClient) -> Optional[str]:
    """Returns the first notebook id found, or None."""
    t0 = time.perf_counter()
    try:
        r = client.get("/notebooks", timeout=10)
        ok = r.status_code == 200
        notebooks = r.json() if ok else []
        first_id = notebooks[0]["id"] if notebooks else None
        record("GET /notebooks", ok, time.perf_counter() - t0,
               f"{len(notebooks)} notebooks found" if ok else f"HTTP {r.status_code}")
        return first_id if ok else None
    except Exception as e:
        record("GET /notebooks", False, time.perf_counter() - t0, str(e))
        return None


def create_test_notebook(client: APIClient) -> Optional[str]:
    """Creates a temporary test notebook and returns its id."""
    t0 = time.perf_counter()
    try:
        r = client.post("/notebooks", {"name": "__pipeline_check__"}, timeout=10)
        ok = r.status_code == 201
        nb_id = r.json().get("id") if ok else None
        record("POST /notebooks (create test)", ok, time.perf_counter() - t0,
               nb_id or f"HTTP {r.status_code}")
        return nb_id
    except Exception as e:
        record("POST /notebooks (create test)", False, time.perf_counter() - t0, str(e))
        return None


def upload_test_material(client: APIClient, notebook_id: str) -> Optional[str]:
    """Uploads a minimal text snippet as material and returns the material id."""
    t0 = time.perf_counter()
    tiny_text = (
        "Photosynthesis is the process by which green plants convert sunlight into "
        "chemical energy (glucose) using carbon dioxide and water. The reaction "
        "produces oxygen as a by-product. Chlorophyll is the pigment responsible "
        "for absorbing light energy. The Calvin Cycle is the light-independent "
        "stage that fixes CO2 into sugars."
    )
    try:
        files = {
            "file": ("pipeline_check.txt", tiny_text.encode(), "text/plain"),
            "notebook_id": (None, notebook_id),
        }
        r = client.post("/upload", files=files, timeout=60)
        if r.status_code == 200:
            data = r.json()
            mat_id = data.get("id") or (data.get("materials", [{}])[0].get("id"))
            ok = bool(mat_id)
        else:
            ok, mat_id = False, None
        record("POST /upload (test material)", ok, time.perf_counter() - t0,
               mat_id or f"HTTP {r.status_code} {r.text[:80]}")
        return mat_id
    except Exception as e:
        record("POST /upload (test material)", False, time.perf_counter() - t0, str(e))
        return None


def test_flashcard(client: APIClient, material_id: str) -> bool:
    t0 = time.perf_counter()
    payload = {
        "material_ids": [material_id],
        "card_count": 3,
        "difficulty": "easy",
    }
    try:
        r = client.post("/flashcard", payload, timeout=180)
        ok = r.status_code == 200
        if ok:
            data = r.json()
            cards = data.get("flashcards") or data.get("cards") or []
            ok = bool(cards)
            detail = f"{len(cards)} cards" if ok else "empty flashcards list"
        else:
            detail = f"HTTP {r.status_code}: {r.text[:120]}"
        record("POST /flashcard", ok, time.perf_counter() - t0, detail)
        return ok
    except Exception as e:
        record("POST /flashcard", False, time.perf_counter() - t0, str(e))
        return False


def test_quiz(client: APIClient, material_id: str) -> bool:
    t0 = time.perf_counter()
    payload = {
        "material_ids": [material_id],
        "mcq_count": 3,
        "difficulty": "easy",
    }
    try:
        r = client.post("/quiz", payload, timeout=180)
        ok = r.status_code == 200
        if ok:
            data = r.json()
            questions = data.get("questions") or []
            ok = bool(questions)
            detail = f"{len(questions)} questions" if ok else "empty questions list"
        else:
            detail = f"HTTP {r.status_code}: {r.text[:120]}"
        record("POST /quiz", ok, time.perf_counter() - t0, detail)
        return ok
    except Exception as e:
        record("POST /quiz", False, time.perf_counter() - t0, str(e))
        return False


def test_mindmap(client: APIClient, notebook_id: str, material_id: str) -> bool:
    t0 = time.perf_counter()
    payload = {"notebook_id": notebook_id, "material_ids": [material_id]}
    try:
        r = client.post("/mindmap", payload, timeout=300)
        ok = r.status_code == 200
        if ok:
            data = r.json()
            nodes = data.get("nodes") or data.get("children") or []
            ok = bool(nodes) or bool(data.get("title"))
            detail = f"{len(nodes)} nodes" if nodes else ("has title" if ok else "empty response")
        else:
            detail = f"HTTP {r.status_code}: {r.text[:120]}"
        record("POST /mindmap", ok, time.perf_counter() - t0, detail)
        return ok
    except Exception as e:
        record("POST /mindmap", False, time.perf_counter() - t0, str(e))
        return False


def test_presentation_async(client: APIClient, material_id: str) -> bool:
    """Fires the async endpoint, polls the job until done or 5 min timeout."""
    t0 = time.perf_counter()
    payload = {
        "material_ids": [material_id],
        "slide_count": 3,
        "theme": "professional",
    }
    try:
        r = client.post("/presentation/async", payload, timeout=30)
        if r.status_code not in (200, 201, 202):
            record("POST /presentation/async + poll", False, time.perf_counter() - t0,
                   f"HTTP {r.status_code}: {r.text[:120]}")
            return False

        job_id = r.json().get("job_id")
        if not job_id:
            record("POST /presentation/async + poll", False, time.perf_counter() - t0,
                   "No job_id in response")
            return False

        deadline = t0 + 300  # 5 min
        while time.perf_counter() < deadline:
            time.sleep(5)
            jr = client.get(f"/jobs/{job_id}", timeout=10)
            if jr.status_code != 200:
                continue
            jdata = jr.json()
            status = jdata.get("status")
            if status == "completed":
                result = jdata.get("result")
                ok = bool(result)
                record("POST /presentation/async + poll", ok, time.perf_counter() - t0,
                       "completed" if ok else "empty result")
                return ok
            if status == "failed":
                record("POST /presentation/async + poll", False, time.perf_counter() - t0,
                       jdata.get("error", "job failed"))
                return False
            # still pending/processing — keep polling

        record("POST /presentation/async + poll", False, time.perf_counter() - t0,
               "timed out after 5 minutes")
        return False
    except Exception as e:
        record("POST /presentation/async + poll", False, time.perf_counter() - t0, str(e))
        return False


def test_chat(client: APIClient, notebook_id: str, material_id: str) -> bool:
    """Calls the SSE chat endpoint and reads the first streamed chunk."""
    t0 = time.perf_counter()
    payload = {
        "message": "Summarise the uploaded text in one sentence.",
        "notebook_id": notebook_id,
        "material_ids": [material_id],
        "session_id": None,
    }
    try:
        r = client.post("/chat", payload, timeout=60)
        ok = r.status_code == 200
        # SSE — just check we get bytes back
        content = b""
        for chunk in r.iter_content(chunk_size=256):
            content += chunk
            if len(content) > 200:
                break
        ok = ok and bool(content)
        record("POST /chat (SSE first chunk)", ok, time.perf_counter() - t0,
               f"{len(content)} bytes received" if ok else f"HTTP {r.status_code} empty")
        return ok
    except Exception as e:
        record("POST /chat (SSE first chunk)", False, time.perf_counter() - t0, str(e))
        return False


def cleanup(client: APIClient, notebook_id: str):
    t0 = time.perf_counter()
    try:
        r = client.delete(f"/notebooks/{notebook_id}", timeout=10)
        ok = r.status_code in (200, 204)
        record("DELETE /notebooks/{id} (cleanup)", ok, time.perf_counter() - t0,
               "cleaned up" if ok else f"HTTP {r.status_code}")
    except Exception as e:
        record("DELETE /notebooks/{id} (cleanup)", False, time.perf_counter() - t0, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="KeplerLab pipeline health check",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(__doc__ or ""),
    )
    parser.add_argument("--url", default=os.getenv("KEPLER_URL", "http://localhost:8000"))
    parser.add_argument("--email", default=os.getenv("KEPLER_EMAIL", ""))
    parser.add_argument("--password", default=os.getenv("KEPLER_PASSWORD", ""))
    parser.add_argument("--notebook-id", default=None, help="Reuse an existing notebook ID")
    parser.add_argument("--material-id", default=None, help="Reuse an existing material ID")
    parser.add_argument("--skip-heavy", action="store_true",
                        help="Skip slow LLM generation tests (flashcard, quiz, mindmap, ppt, chat)")
    parser.add_argument("--test-ppt", action="store_true",
                        help="Also run the slow async presentation test (disabled by default)")
    parser.add_argument("--no-cleanup", action="store_true",
                        help="Don't delete the test notebook at the end")
    args = parser.parse_args()

    if not args.email or not args.password:
        print(FAIL("ERROR") + "  --email and --password (or KEPLER_EMAIL / KEPLER_PASSWORD env vars) are required.")
        sys.exit(1)

    client = APIClient(args.url)
    created_notebook_id: Optional[str] = None

    print()
    print(BOLD(f"KeplerLab Pipeline Health Check"))
    print(BOLD(f"Target: {args.url}"))
    print("─" * 75)

    # ── 1. Health ──────────────────────────────────────────────────────────
    if not test_health(client):
        print(WARN("Backend is not reachable — aborting."))
        _print_summary()
        sys.exit(1)

    # ── 2. Auth ────────────────────────────────────────────────────────────
    if not test_login(client, args.email, args.password):
        print(WARN("Login failed — check credentials."))
        _print_summary()
        sys.exit(1)

    # ── 3. Notebooks ───────────────────────────────────────────────────────
    notebook_id = args.notebook_id
    if not notebook_id:
        # Try to reuse the first existing notebook to avoid creating lots of test data
        notebook_id = test_list_notebooks(client)
    if not notebook_id:
        notebook_id = create_test_notebook(client)
        created_notebook_id = notebook_id  # mark for cleanup

    if not notebook_id:
        print(WARN("Could not obtain a notebook — aborting generation tests."))
        _print_summary()
        sys.exit(1)

    # ── 4. Material ────────────────────────────────────────────────────────
    material_id = args.material_id
    if not material_id:
        material_id = upload_test_material(client, notebook_id)

    if not material_id:
        print(WARN("Could not obtain a material — aborting generation tests."))
        _print_summary()
        sys.exit(1)

    if args.skip_heavy:
        print(DIM("  [Skipping heavy generation tests per --skip-heavy]"))
    else:
        print("─" * 75)
        print(BOLD("  Generation tests (each may take 1–5 minutes)…"))
        print("─" * 75)

        # ── 5. Flashcard ───────────────────────────────────────────────────
        test_flashcard(client, material_id)

        # ── 6. Quiz ────────────────────────────────────────────────────────
        test_quiz(client, material_id)

        # ── 7. Mind Map ────────────────────────────────────────────────────
        test_mindmap(client, notebook_id, material_id)

        # ── 8. Presentation (opt-in because it's very slow) ────────────────
        if args.test_ppt:
            test_presentation_async(client, material_id)
        else:
            print(DIM("  [Skipping presentation test — use --test-ppt to enable]"))

        # ── 9. Chat ────────────────────────────────────────────────────────
        test_chat(client, notebook_id, material_id)

    # ── 10. Cleanup ────────────────────────────────────────────────────────
    if created_notebook_id and not args.no_cleanup:
        print("─" * 75)
        cleanup(client, created_notebook_id)

    _print_summary()


def _print_summary():
    if not results:
        return
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    elapsed_total = sum(r["duration"] for r in results)

    print()
    print("─" * 75)
    print(BOLD(f"Summary: {passed}/{total} passed  |  {elapsed_total:.1f}s total"))
    if failed:
        print()
        print(BOLD("Failed tests:"))
        for r in results:
            if not r["passed"]:
                print(f"  {FAIL()}  {r['name']}")
                if r["detail"]:
                    print(f"           {DIM(r['detail'])}")
    print("─" * 75)
    print()
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
