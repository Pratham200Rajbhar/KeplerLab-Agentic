#!/usr/bin/env python3
"""
=============================================================================
 KeplerLab — Agentic AI Pipeline Test Suite  (56 test cases)
=============================================================================
 Exhaustively tests the full agentic AI execution pipeline:
   • Intent detection + task classification
   • Execution plan generation
   • Python code generation + sandboxed execution
   • Artifact detection (charts, models, datasets, reports)
   • SSE streaming events + artifact downloading

 Output types covered:
   PNG charts, CSV datasets, Excel (.xlsx), PDF reports, PKL/joblib ML models,
   HTML reports, JSON summaries, generated Python code

 Test Groups:
   A  Visualizations     (T01–T12)  — pure code gen, every chart type
   B  Data Analysis      (T13–T19)  — uploaded real datasets
   C  Machine Learning   (T20–T29)  — train + save models, evaluation plots
   D  Time Series        (T30–T34)  — forecasting, decomposition, lags
   E  Statistics         (T35–T39)  — hypothesis tests, ANOVA, outliers
   F  Data Engineering   (T40–T44)  — cleaning, feature eng, Excel export
   G  Reports/Documents  (T45–T47)  — PDF, multi-sheet Excel, HTML
   H  Advanced Analytics (T48–T53)  — anomaly, association rules, NLP, PCA
   I  RAG & Corpus Q&A  (T54–T55)  — PDF + uploaded datasets
   J  Stress / Edge      (T56)      — large synthetic dataset pipeline

 Usage:
   python test_agent.py                          # run all 56 tests
   python test_agent.py --base http://localhost:8001
   python test_agent.py --group A               # run a group
   python test_agent.py --only 20,21,22         # run specific tests by number
   python test_agent.py --skip-upload           # no file uploads

 Requirements:
   pip install httpx rich
=============================================================================
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx

# ── Optional rich output ─────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich import print as rprint
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None


# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TEST_FILES = {
    "car_data":       SCRIPT_DIR / "car data (2).csv",
    "mall_customers": SCRIPT_DIR / "Mall_Customers (1).csv",
    "social_ads":     SCRIPT_DIR / "Social_Network_Ads (1).csv",
    "covid_excel":    SCRIPT_DIR / "Covid cases in India (1).xlsx",
    "intro_pdf":      SCRIPT_DIR / "Introduction.pdf",
}

# ── Configuration ─────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:8000"
TIMEOUT = 300          # seconds — agent pipeline can take a while
JOB_POLL_TIMEOUT = 180 # seconds to wait for material processing jobs
JOB_POLL_INTERVAL = 5  # seconds between polls
SSE_TIMEOUT = 600      # seconds for SSE stream

_RUN_ID = uuid.uuid4().hex[:8]
TEST_EMAIL    = f"agent_tester_{_RUN_ID}@testkepler.com"
TEST_USERNAME = f"agent_tester_{_RUN_ID}"
TEST_PASSWORD = "AgentTest1!"

# ── Result tracking ──────────────────────────────────────────────────────────
@dataclass
class TestResult:
    name: str
    passed: bool
    detail: str = ""
    duration: float = 0.0
    artifacts_saved: List[str] = field(default_factory=list)
    events_received: List[str] = field(default_factory=list)

results: List[TestResult] = []

# ── Colour helpers ────────────────────────────────────────────────────────────
def _green(s): return f"\033[92m{s}\033[0m"
def _red(s):   return f"\033[91m{s}\033[0m"
def _yellow(s):return f"\033[93m{s}\033[0m"
def _cyan(s):  return f"\033[96m{s}\033[0m"
def _bold(s):  return f"\033[1m{s}\033[0m"

def log(msg: str, level: str = "INFO"):
    icons = {"INFO": "ℹ", "PASS": "✔", "FAIL": "✘", "WARN": "⚠",
             "HEAD": "▶", "STEP": "→", "ART": "📁", "SSE": "📡"}
    icon = icons.get(level, " ")
    if level == "PASS":
        print(f"  {_green(icon)} {msg}")
    elif level == "FAIL":
        print(f"  {_red(icon)} {msg}")
    elif level == "WARN":
        print(f"  {_yellow(icon)} {msg}")
    elif level in ("HEAD", "STEP"):
        print(f"  {_cyan(icon)} {msg}")
    else:
        print(f"  {icon} {msg}")

def section(title: str):
    print(f"\n{'='*72}")
    print(f"  {_bold(title)}")
    print(f"{'='*72}")

def record(name: str, passed: bool, detail: str = "", duration: float = 0.0,
           artifacts: List[str] = None, events: List[str] = None):
    r = TestResult(name, passed, detail, duration,
                   artifacts or [], events or [])
    results.append(r)
    level = "PASS" if passed else "FAIL"
    det = f" — {detail}" if detail else ""
    log(f"{name}{det} [{duration:.1f}s]", level)


# ── HTTP helpers ─────────────────────────────────────────────────────────────
class APIClient:
    """Thin wrapper around httpx.Client with auth token management."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.token: Optional[str] = None
        self._client = httpx.Client(timeout=TIMEOUT, follow_redirects=True)

    def _headers(self) -> Dict[str, str]:
        h: Dict[str, str] = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def post(self, path: str, **kwargs) -> httpx.Response:
        return self._client.post(
            f"{self.base_url}{path}",
            headers=self._headers(),
            **kwargs,
        )

    def get(self, path: str, **kwargs) -> httpx.Response:
        return self._client.get(
            f"{self.base_url}{path}",
            headers=self._headers(),
            **kwargs,
        )

    def post_multipart(self, path: str, files=None, data=None) -> httpx.Response:
        h = {}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return self._client.post(
            f"{self.base_url}{path}",
            headers=h,
            files=files,
            data=data,
            timeout=120,
        )

    def stream_post(self, path: str, json_data: dict):
        """Yield (event, data) tuples from an SSE POST stream."""
        headers = {**self._headers(), "Accept": "text/event-stream"}
        # Remove Content-Type override so httpx sets it correctly for JSON
        headers["Content-Type"] = "application/json"

        with self._client.stream(
            "POST",
            f"{self.base_url}{path}",
            json=json_data,
            headers=headers,
            timeout=SSE_TIMEOUT,
        ) as resp:
            resp.raise_for_status()
            event_name = "message"
            for line in resp.iter_lines():
                line = line.strip()
                if not line:
                    event_name = "message"
                    continue
                if line.startswith("event:"):
                    event_name = line[len("event:"):].strip()
                elif line.startswith("data:"):
                    raw = line[len("data:"):].strip()
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        data = raw
                    yield event_name, data

    def close(self):
        self._client.close()


# ── Auth ──────────────────────────────────────────────────────────────────────
def register_and_login(client: APIClient) -> bool:
    """Register a fresh test user and store the access token."""
    log("Registering test user …", "STEP")
    resp = client.post("/auth/signup", json={
        "email": TEST_EMAIL,
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD,
    })
    if resp.status_code not in (200, 201):
        log(f"Signup failed: {resp.status_code} {resp.text[:200]}", "FAIL")
        return False
    log(f"Registered: {TEST_EMAIL}", "PASS")

    log("Logging in …", "STEP")
    resp = client.post("/auth/login", json={
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
    })
    if resp.status_code != 200:
        log(f"Login failed: {resp.status_code} {resp.text[:200]}", "FAIL")
        return False

    data = resp.json()
    client.token = data.get("access_token")
    if not client.token:
        log("No access_token in login response", "FAIL")
        return False

    log("Logged in — token obtained", "PASS")
    return True


# ── Notebook ──────────────────────────────────────────────────────────────────
def create_notebook(client: APIClient) -> Optional[str]:
    """Create a test notebook and return its ID."""
    resp = client.post("/notebooks", json={
        "name": f"Agent Test {_RUN_ID}",
        "description": "Auto-created for agentic AI pipeline testing",
    })
    if resp.status_code not in (200, 201):
        log(f"Notebook creation failed: {resp.status_code} {resp.text[:200]}", "FAIL")
        return None
    nb_id = resp.json().get("id")
    log(f"Notebook created: {nb_id}", "PASS")
    return nb_id


# ── Upload ────────────────────────────────────────────────────────────────────
def upload_files(
    client: APIClient,
    notebook_id: str,
    file_keys: List[str],
) -> Dict[str, str]:
    """Upload files and return {file_key: material_id} mapping."""
    material_ids: Dict[str, str] = {}

    for key in file_keys:
        path = TEST_FILES.get(key)
        if not path or not path.exists():
            log(f"File not found: {key} → {path}", "WARN")
            continue

        log(f"Uploading {path.name} …", "STEP")
        with open(path, "rb") as fh:
            resp = client.post_multipart(
                "/upload",
                files={"file": (path.name, fh)},
                data={"notebook_id": notebook_id},
            )

        if resp.status_code not in (200, 201, 202):
            log(f"Upload failed for {path.name}: {resp.status_code} {resp.text[:200]}", "WARN")
            continue

        body = resp.json()
        mat_id = body.get("material_id") or body.get("id")
        job_id = body.get("job_id")

        if mat_id:
            material_ids[key] = mat_id
            log(f"Uploaded {path.name} → material_id={mat_id}", "PASS")
        elif job_id:
            log(f"Uploaded {path.name} → job_id={job_id} (async processing)", "INFO")
            material_ids[key] = f"job:{job_id}"   # store for polling

    return material_ids


def poll_jobs(client: APIClient, material_ids: Dict[str, str]) -> Dict[str, str]:
    """Poll job-backed material IDs until done, return updated {key: material_id}."""
    resolved: Dict[str, str] = {}
    pending: Dict[str, str] = {}   # key → job_id

    for key, val in material_ids.items():
        if val.startswith("job:"):
            pending[key] = val[4:]
        else:
            resolved[key] = val

    if not pending:
        return material_ids

    log(f"Waiting for {len(pending)} upload job(s) to complete …", "STEP")
    deadline = time.time() + JOB_POLL_TIMEOUT
    job_material: Dict[str, str] = {}   # job_id → material_id

    while pending and time.time() < deadline:
        for key, job_id in list(pending.items()):
            resp = client.get(f"/jobs/{job_id}")
            if resp.status_code != 200:
                continue
            body = resp.json()
            status = body.get("status", "")
            if status in ("done", "completed", "success"):
                mat_id = body.get("result", {}).get("material_id") or body.get("material_id")
                if mat_id:
                    resolved[key] = mat_id
                    pending.pop(key)
                    log(f"Job {job_id} done → material_id={mat_id}", "PASS")
                else:
                    resolved[key] = job_id  # fallback
                    pending.pop(key)
            elif status in ("failed", "error"):
                log(f"Job {job_id} failed: {body.get('error', '')}", "WARN")
                pending.pop(key)
        if pending:
            time.sleep(JOB_POLL_INTERVAL)

    if pending:
        log(f"{len(pending)} job(s) did not complete in time — proceeding without them", "WARN")

    return {**material_ids, **resolved}


# ── SSE stream runner ─────────────────────────────────────────────────────────
def run_agent_task(
    client: APIClient,
    notebook_id: str,
    message: str,
    material_ids: List[str],
    output_subdir: str,
    token: Optional[str] = None,
) -> Tuple[bool, str, List[str], List[str]]:
    """
    Call POST /agent/execute and stream the SSE response.

    Returns:
        (success, summary_text, saved_file_paths, events_received)
    """
    out_dir = OUTPUT_DIR / output_subdir
    out_dir.mkdir(parents=True, exist_ok=True)

    log(f"→ Task: {message[:80]}…" if len(message) > 80 else f"→ Task: {message}", "STEP")

    saved_files: List[str] = []
    events_seen: List[str] = []
    summary_text = ""
    final_text = ""
    artifacts_meta: List[dict] = []
    had_error = False

    try:
        for evt, data in client.stream_post("/agent/execute", {
            "message": message,
            "notebook_id": notebook_id,
            "material_ids": material_ids,
        }):
            events_seen.append(evt)

            if evt == "step":
                status_msg = data.get("status", "") if isinstance(data, dict) else str(data)
                log(f"  [step] {status_msg}", "SSE")

            elif evt == "intent":
                if isinstance(data, dict):
                    log(f"  [intent] {data.get('task_type')} "
                        f"(confidence={data.get('confidence', 0):.2f})", "SSE")

            elif evt == "agent_start":
                if isinstance(data, dict):
                    plan = data.get("plan", [])
                    log(f"  [plan] {len(plan)} step(s) planned", "SSE")

            elif evt == "code_generated":
                if isinstance(data, dict):
                    code_len = len(data.get("code", ""))
                    log(f"  [code] Generated {code_len} chars of Python", "SSE")
                    # Save generated code
                    code_path = out_dir / "generated_code.py"
                    with open(code_path, "w") as f:
                        f.write(data.get("code", ""))
                    saved_files.append(str(code_path))

            elif evt == "artifact":
                if isinstance(data, dict):
                    artifacts_meta.append(data)
                    fname = data.get("filename") or data.get("name", "unknown")
                    log(f"  [artifact] {fname} ({data.get('category', '?')})", "ART")

            elif evt == "tool_result":
                if isinstance(data, dict):
                    tool = data.get("tool", "?")
                    success = data.get("success", False)
                    log(f"  [tool_result] {tool} → {'ok' if success else 'failed'}", "SSE")

            elif evt == "summary":
                if isinstance(data, dict):
                    summary_text = data.get("text") or data.get("summary") or ""
                    metrics = data.get("metrics", {})
                    steps_ok = metrics.get("steps_succeeded", "?")
                    total_steps = metrics.get("total_steps", "?")
                    log(f"  [summary] {steps_ok}/{total_steps} steps succeeded", "SSE")

            elif evt == "token":
                if isinstance(data, dict):
                    final_text += data.get("content", "")
                elif isinstance(data, str):
                    final_text += data

            elif evt == "done":
                if isinstance(data, dict):
                    elapsed = data.get("elapsed_seconds", 0)
                    log(f"  [done] elapsed={elapsed:.1f}s", "PASS")

            elif evt == "error":
                err = data.get("error", str(data)) if isinstance(data, dict) else str(data)
                log(f"  [error] {err}", "FAIL")
                had_error = True

    except httpx.ReadTimeout:
        log("SSE stream timed out", "WARN")
        had_error = True
    except Exception as exc:
        log(f"SSE stream error: {exc}", "FAIL")
        had_error = True

    # ── Download artifacts ────────────────────────────────────────────────
    for art in artifacts_meta:
        art_files = _download_artifact(client, art, out_dir)
        saved_files.extend(art_files)

    # Save summary / final response as text
    combined_text = summary_text or final_text
    if combined_text:
        txt_path = out_dir / "agent_response.txt"
        with open(txt_path, "w") as f:
            f.write(combined_text)
        saved_files.append(str(txt_path))

    # Save raw events log
    events_path = out_dir / "events_log.json"
    with open(events_path, "w") as f:
        json.dump({"events": events_seen, "artifacts": artifacts_meta}, f, indent=2)
    saved_files.append(str(events_path))

    success = not had_error and bool(events_seen)
    if saved_files:
        log(f"  Saved {len(saved_files)} file(s) → {out_dir}", "ART")

    return success, combined_text, saved_files, events_seen


def _download_artifact(
    client: APIClient,
    art: dict,
    out_dir: Path,
) -> List[str]:
    """Download a single artifact using its token or direct workspace path."""
    saved: List[str] = []

    filename  = art.get("filename") or art.get("name") or "artifact"
    mime      = art.get("mime_type") or art.get("mimeType") or art.get("mime", "")
    url_path  = art.get("url", "")
    workspace_path = art.get("workspace_path") or art.get("workspacePath")

    # ── Strategy 1: parse URL field to get /agent/file/{id}?token={t} ─────
    art_id: Optional[str] = art.get("id") or art.get("artifact_id")
    token:  Optional[str] = art.get("download_token") or art.get("token")

    if url_path and "/agent/file/" in url_path:
        # url_path like "/agent/file/{id}?token={t}"
        try:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(url_path)
            # Extract id from path
            parts = parsed.path.split("/")
            if len(parts) >= 4:
                art_id = art_id or parts[-1]
            qs = parse_qs(parsed.query)
            token = token or (qs.get("token", [None])[0])
        except Exception:
            pass

    if art_id and token:
        try:
            resp = client.get(f"/agent/file/{art_id}?token={token}")
            if resp.status_code == 200:
                dest = out_dir / _safe_filename(filename)
                dest.write_bytes(resp.content)
                saved.append(str(dest))
                log(f"  ↓ Downloaded {filename} ({len(resp.content)} bytes)", "ART")
                return saved
        except Exception as e:
            log(f"  Token download failed for {filename}: {e}", "WARN")

    # ── Strategy 2: file is on the local filesystem (same machine) ────────
    if workspace_path and os.path.isfile(workspace_path):
        dest = out_dir / _safe_filename(filename)
        shutil.copy2(workspace_path, dest)
        saved.append(str(dest))
        log(f"  ↓ Copied {filename} from workspace ({os.path.getsize(workspace_path)} bytes)", "ART")
        return saved

    # ── Strategy 3: artefact carries a base64-encoded image ───────────────
    if art.get("preview_base64"):
        b64 = art["preview_base64"]
        import base64
        try:
            raw = base64.b64decode(b64)
            ext = ".png" if "png" in mime else ".jpg" if "jpg" in mime else ".bin"
            dest = out_dir / (_safe_filename(filename, ext))
            dest.write_bytes(raw)
            saved.append(str(dest))
            log(f"  ↓ Saved base64 preview {filename}", "ART")
        except Exception as e:
            log(f"  base64 decode failed for {filename}: {e}", "WARN")

    return saved


def _safe_filename(name: str, ext: str = "") -> str:
    """Sanitize a filename for local storage."""
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)
    if ext and not safe.endswith(ext):
        safe += ext
    return safe or "artifact"


# ═══════════════════════════════════════════════════════════════════════════
# GROUP A — Visualizations (pure code generation, no uploads needed)
# ═══════════════════════════════════════════════════════════════════════════

def t01_bar_chart(client, nb, mids):
    """Grouped and stacked bar charts."""
    section("T01 — Bar Charts (grouped + stacked)")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate Python code that creates two bar chart figures: "
        "(1) A grouped bar chart comparing sales across Q1-Q4 for 3 products (Product A, B, C), "
        "(2) A stacked bar chart of market share across 5 regions. "
        "Use matplotlib with a professional style. Save as bar_grouped.png and bar_stacked.png."
    ), [], "T01_bar_charts")
    record("T01 Bar Charts", s, f"{len(f)} files", time.time()-t0, f, e)


def t02_histogram_kde(client, nb, mids):
    """Histograms + KDE overlays."""
    section("T02 — Histograms + KDE Density Plots")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate Python code to create a 2×2 subplot figure with histograms overlaid with KDE curves "
        "for four synthetic numerical features: height, weight, age, and income (500 samples each, normally distributed). "
        "Add mean/std annotations. Save as histograms_kde.png."
    ), [], "T02_histograms_kde")
    record("T02 Histograms + KDE", s, f"{len(f)} files", time.time()-t0, f, e)


def t03_box_violin(client, nb, mids):
    """Box plots and violin plots side by side."""
    section("T03 — Box Plots + Violin Plots")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate Python code that creates a side-by-side comparison figure: "
        "left panel is box plots for salary by department (5 departments, 100 samples each), "
        "right panel is violin plots for the same data. "
        "Include individual data points as swarm overlay on the violin plots. "
        "Save as box_violin_comparison.png."
    ), [], "T03_box_violin")
    record("T03 Box + Violin Plots", s, f"{len(f)} files", time.time()-t0, f, e)


def t04_scatter_matrix(client, nb, mids):
    """Pair plot / scatter matrix."""
    section("T04 — Scatter Matrix (Pair Plot)")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate Python code to create a scatter matrix (pair plot) for a synthetic dataset "
        "with 4 features (sepal_length, sepal_width, petal_length, petal_width) and 3 classes. "
        "Colour points by class. Show correlation coefficients in upper triangle. "
        "Save as scatter_matrix.png."
    ), [], "T04_scatter_matrix")
    record("T04 Scatter Matrix", s, f"{len(f)} files", time.time()-t0, f, e)


def t05_heatmap_annotated(client, nb, mids):
    """Annotated correlation heatmap."""
    section("T05 — Annotated Correlation Heatmap")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate Python code to create an annotated correlation heatmap for a synthetic "
        "10-feature dataset (500 rows). Use seaborn with a diverging color palette. "
        "Annotate each cell with the correlation coefficient rounded to 2 decimal places. "
        "Save as correlation_heatmap_annotated.png."
    ), [], "T05_heatmap_annotated")
    record("T05 Annotated Heatmap", s, f"{len(f)} files", time.time()-t0, f, e)


def t06_pie_donut(client, nb, mids):
    """Pie + donut charts."""
    section("T06 — Pie Chart + Donut Chart")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate Python code to create two charts side by side: "
        "(1) A pie chart of market share for 6 companies with percentage labels and explode effect on the largest slice, "
        "(2) A donut chart of the same data with a total label in the centre. "
        "Save as pie_donut_charts.png."
    ), [], "T06_pie_donut")
    record("T06 Pie + Donut Charts", s, f"{len(f)} files", time.time()-t0, f, e)


def t07_line_area(client, nb, mids):
    """Multi-line + area / filled line charts."""
    section("T07 — Line Chart + Area Chart")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate Python code to create two synthetic time-series charts: "
        "(1) A multi-line chart of monthly revenue for 4 products over 24 months with markers, "
        "(2) A stacked area chart of the same data. "
        "Add a legend and grid. Save as line_chart.png and area_chart.png."
    ), [], "T07_line_area")
    record("T07 Line + Area Charts", s, f"{len(f)} files", time.time()-t0, f, e)


def t08_bubble_chart(client, nb, mids):
    """Bubble chart with size and colour encoding."""
    section("T08 — Bubble Chart")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate Python code to create a bubble chart where: "
        "x=GDP, y=Life Expectancy, bubble size=Population, colour=Continent "
        "for 80 synthetic countries. Add country labels for the largest 5 bubbles. "
        "Save as bubble_chart.png."
    ), [], "T08_bubble_chart")
    record("T08 Bubble Chart", s, f"{len(f)} files", time.time()-t0, f, e)


def t09_3d_plots(client, nb, mids):
    """3D scatter plot and 3D surface plot."""
    section("T09 — 3D Scatter + 3D Surface Plot")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate Python code to create two 3D matplotlib figures: "
        "(1) A 3D scatter plot of 200 synthetic points with 3 coloured clusters, "
        "(2) A 3D surface plot of z = sin(sqrt(x²+y²)) over a grid. "
        "Save as scatter_3d.png and surface_3d.png."
    ), [], "T09_3d_plots")
    record("T09 3D Plots", s, f"{len(f)} files", time.time()-t0, f, e)


def t10_radar_chart(client, nb, mids):
    """Radar / spider chart."""
    section("T10 — Radar / Spider Chart")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate Python code to create a radar (spider) chart comparing 3 products "
        "across 7 attributes: Quality, Price, Design, Support, Speed, Reliability, Innovation. "
        "Each product gets its own coloured polygon with 30% alpha fill. "
        "Save as radar_chart.png."
    ), [], "T10_radar_chart")
    record("T10 Radar Chart", s, f"{len(f)} files", time.time()-t0, f, e)


def t11_candlestick(client, nb, mids):
    """Financial candlestick chart."""
    section("T11 — Candlestick Chart (Financial)")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate Python code to create a financial candlestick chart for synthetic daily stock data "
        "over 60 trading days (realistic OHLCV values with random walk). "
        "Add a 20-day moving average line and volume bars below. "
        "Use mplfinance or matplotlib. Save as candlestick_chart.png."
    ), [], "T11_candlestick")
    record("T11 Candlestick Chart", s, f"{len(f)} files", time.time()-t0, f, e)


def t12_word_cloud(client, nb, mids):
    """Word cloud from text."""
    section("T12 — Word Cloud")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate Python code to create a word cloud from a synthetic tech-themed paragraph "
        "(200+ words about machine learning, AI, data science, Python, neural networks). "
        "Use a custom mask shape (circle) if possible, otherwise rectangular. "
        "Save as word_cloud.png. If wordcloud package is unavailable, simulate with a frequency bar chart."
    ), [], "T12_word_cloud")
    record("T12 Word Cloud", s, f"{len(f)} files", time.time()-t0, f, e)


# ═══════════════════════════════════════════════════════════════════════════
# GROUP B — Data Analysis with Uploaded Real Datasets
# ═══════════════════════════════════════════════════════════════════════════

def t13_car_eda(client, nb, mids):
    """Full EDA on car sales dataset."""
    section("T13 — Car Data EDA (distribution + correlation + stats CSV)")
    t0 = time.time()
    mat = _m(mids, "car_data")
    s, _, f, e = run_agent_task(client, nb, (
        "Perform a comprehensive exploratory data analysis on the uploaded car sales dataset. "
        "Include: summary statistics table, distribution plots for price and engine size, "
        "a correlation heatmap, a bar chart of average price by fuel type, "
        "a scatter plot of mileage vs price, and a box plot of price by transmission. "
        "Save all charts as PNG files and produce a detailed statistics CSV."
    ), mat, "T13_car_eda")
    record("T13 Car Data EDA", s, f"{len(f)} files", time.time()-t0, f, e)


def t14_car_regression(client, nb, mids):
    """Regression model on car price prediction."""
    section("T14 — Car Price Prediction (Regression)")
    t0 = time.time()
    mat = _m(mids, "car_data")
    s, _, f, e = run_agent_task(client, nb, (
        "Using the car sales dataset, build a regression model to predict car price. "
        "Steps: load data, encode categorical features, split 80/20 train/test, "
        "train Linear Regression and Random Forest Regressor, compare R², MAE, RMSE. "
        "Generate: residuals plot, predicted vs actual scatter plot, feature importance chart. "
        "Save both models as car_lr_model.pkl and car_rf_model.pkl. "
        "Save evaluation metrics as regression_metrics.csv."
    ), mat, "T14_car_regression")
    record("T14 Car Price Regression", s, f"{len(f)} files", time.time()-t0, f, e)


def t15_mall_segmentation(client, nb, mids):
    """K-Means customer segmentation on Mall Customers."""
    section("T15 — Mall Customer Segmentation (K-Means)")
    t0 = time.time()
    mat = _m(mids, "mall_customers")
    s, _, f, e = run_agent_task(client, nb, (
        "Perform K-Means customer segmentation on the Mall Customers dataset. "
        "Use Annual Income and Spending Score features. "
        "Find optimal K with the elbow method (plot elbow curve). "
        "Cluster with K=5, produce a scatter plot coloured by cluster, "
        "compute per-cluster statistics, and save customers with cluster labels as CSV. "
        "Also produce a 3D scatter plot adding Age as the third dimension. "
        "Save all plots as PNG and statistics as CSV."
    ), mat, "T15_mall_segmentation")
    record("T15 Mall Segmentation", s, f"{len(f)} files", time.time()-t0, f, e)


def t16_mall_advanced_eda(client, nb, mids):
    """Advanced EDA on Mall Customers."""
    section("T16 — Mall Customers Advanced EDA")
    t0 = time.time()
    mat = _m(mids, "mall_customers")
    s, _, f, e = run_agent_task(client, nb, (
        "Perform advanced EDA on the Mall Customers dataset. "
        "Include: age distribution histogram, income vs spending scatter coloured by gender, "
        "box plots of income and spending score by gender, "
        "violin plot of age by gender, pair plot of all numeric features coloured by gender. "
        "Save summary statistics split by gender as gender_stats.csv. Save all charts as PNG."
    ), mat, "T16_mall_advanced_eda")
    record("T16 Mall Advanced EDA", s, f"{len(f)} files", time.time()-t0, f, e)


def t17_classification_rf(client, nb, mids):
    """Random Forest classification on Social Network Ads."""
    section("T17 — Social Ads RF Classification")
    t0 = time.time()
    mat = _m(mids, "social_ads")
    s, _, f, e = run_agent_task(client, nb, (
        "Train a Random Forest classification model on the Social Network Ads dataset "
        "to predict whether a user will purchase. "
        "Steps: encode features, split 80/20 train-test, train Random Forest, "
        "evaluate accuracy, precision, recall, F1. "
        "Generate: confusion matrix PNG, feature importance bar chart PNG, ROC curve PNG. "
        "Save classification report as classification_report.csv. Save model as rf_model.pkl."
    ), mat, "T17_classification_rf")
    record("T17 RF Classification", s, f"{len(f)} files", time.time()-t0, f, e)


def t18_social_feature_eng(client, nb, mids):
    """Feature engineering on Social Ads dataset."""
    section("T18 — Social Ads Feature Engineering")
    t0 = time.time()
    mat = _m(mids, "social_ads")
    s, _, f, e = run_agent_task(client, nb, (
        "Perform feature engineering on the Social Network Ads dataset. "
        "Create: age groups (bins), income quartiles, age×income interaction, "
        "log-transformed income, age squared. "
        "Compare model performance (Logistic Regression) before vs after feature engineering. "
        "Plot feature importance comparison bar chart. "
        "Save the engineered dataset as engineered_features.csv and performance comparison as feature_eng_results.csv."
    ), mat, "T18_feature_engineering")
    record("T18 Feature Engineering", s, f"{len(f)} files", time.time()-t0, f, e)


def t19_covid_trends(client, nb, mids):
    """Time-series analysis on Covid India Excel."""
    section("T19 — Covid India Time-Series Trends")
    t0 = time.time()
    mat = _m(mids, "covid_excel")
    s, _, f, e = run_agent_task(client, nb, (
        "Analyse the Covid cases in India Excel dataset. "
        "Produce: a time-series line chart of daily new cases, "
        "a 7-day rolling average overlay, a bar chart of total cases by state (top 10), "
        "a cumulative cases trend line, and a heatmap of monthly cases by state. "
        "Save all charts as PNG and aggregate statistics as covid_stats.csv."
    ), mat, "T19_covid_trends")
    record("T19 Covid Trends", s, f"{len(f)} files", time.time()-t0, f, e)


# ═══════════════════════════════════════════════════════════════════════════
# GROUP C — Machine Learning Models
# ═══════════════════════════════════════════════════════════════════════════

def t20_linear_regression(client, nb, mids):
    """Linear Regression + save model + residual analysis."""
    section("T20 — Linear Regression (Boston-style synthetic)")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate a synthetic housing dataset (1000 rows): size_sqft, bedrooms, bathrooms, "
        "age_years, distance_city_km → price. "
        "Train a Linear Regression model, produce: "
        "residuals plot, Q-Q plot of residuals, predicted vs actual scatter, "
        "coefficient bar chart. Save model as linear_regression.pkl and "
        "evaluation metrics (R², MAE, RMSE) as lr_metrics.csv."
    ), [], "T20_linear_regression")
    record("T20 Linear Regression", s, f"{len(f)} files", time.time()-t0, f, e)


def t21_gradient_boosting(client, nb, mids):
    """Gradient Boosting Classifier."""
    section("T21 — Gradient Boosting Classifier")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate a synthetic binary classification dataset (1000 rows, 8 features). "
        "Train a Gradient Boosting Classifier, tune n_estimators with cross-validation, "
        "plot learning curve (train vs val error vs n_estimators), "
        "confusion matrix, ROC-AUC curve. "
        "Save model as gb_classifier.pkl and metrics as gb_metrics.csv."
    ), [], "T21_gradient_boosting")
    record("T21 Gradient Boosting", s, f"{len(f)} files", time.time()-t0, f, e)


def t22_svm_classifier(client, nb, mids):
    """SVM with decision boundary visualisation."""
    section("T22 — SVM Classifier + Decision Boundary")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate a 2D binary classification dataset (300 points, make_moons shape). "
        "Train an SVM with RBF kernel, plot the decision boundary with support vectors highlighted. "
        "Also compare Linear vs RBF vs Poly kernel accuracies as a bar chart. "
        "Save model as svm_model.pkl, decision boundary as svm_boundary.png, "
        "kernel comparison as svm_kernels.png."
    ), [], "T22_svm_classifier")
    record("T22 SVM Classifier", s, f"{len(f)} files", time.time()-t0, f, e)


def t23_decision_tree(client, nb, mids):
    """Decision Tree with tree visualisation."""
    section("T23 — Decision Tree + Tree Diagram")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate a synthetic 3-class classification dataset (600 rows, 4 features). "
        "Train a Decision Tree classifier (max_depth=4), "
        "visualise the tree using plot_tree (save as decision_tree.png), "
        "plot feature importances as a bar chart, "
        "show confusion matrix (3×3). "
        "Save model as decision_tree.pkl and metrics as dt_metrics.csv."
    ), [], "T23_decision_tree")
    record("T23 Decision Tree", s, f"{len(f)} files", time.time()-t0, f, e)


def t24_logistic_regression(client, nb, mids):
    """Logistic Regression + coefficient analysis."""
    section("T24 — Logistic Regression + Coefficients")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate a synthetic binary classification dataset (800 rows, 6 named features). "
        "Train Logistic Regression, produce: "
        "coefficient importance bar chart (sorted), calibration curve, "
        "precision-recall curve, ROC curve. "
        "Save model as logistic_model.pkl, coefficients as lr_coefficients.csv."
    ), [], "T24_logistic_regression")
    record("T24 Logistic Regression", s, f"{len(f)} files", time.time()-t0, f, e)


def t25_knn(client, nb, mids):
    """KNN with accuracy vs K plot."""
    section("T25 — KNN + Accuracy vs K")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate a synthetic binary classification dataset (500 rows, 2 features for easy plotting). "
        "Train KNN for K=1 to 20, plot: "
        "(1) accuracy vs K (train and test curves), "
        "(2) decision boundary for best K, "
        "(3) confusion matrix for best K. "
        "Save model as knn_model.pkl and k_accuracy_results.csv."
    ), [], "T25_knn")
    record("T25 KNN", s, f"{len(f)} files", time.time()-t0, f, e)


def t26_neural_network(client, nb, mids):
    """MLP Neural Network classifier."""
    section("T26 — Neural Network (MLP) Classifier")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate a synthetic multi-class classification dataset (1000 rows, 10 features, 3 classes). "
        "Train an MLPClassifier (hidden layers: 128, 64, 32), plot: "
        "(1) training loss curve, "
        "(2) confusion matrix, "
        "(3) ROC curves for each class (one-vs-rest). "
        "Save model as mlp_model.pkl and training_history.csv."
    ), [], "T26_neural_network")
    record("T26 Neural Network MLP", s, f"{len(f)} files", time.time()-t0, f, e)


def t27_pca(client, nb, mids):
    """PCA dimensionality reduction + explained variance."""
    section("T27 — PCA Dimensionality Reduction")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate a synthetic dataset (500 rows, 15 features, 3 classes). "
        "Apply PCA, produce: "
        "(1) scree plot (explained variance per component), "
        "(2) cumulative explained variance curve, "
        "(3) 2D PCA scatter plot coloured by class, "
        "(4) biplot of first two principal components with feature arrows. "
        "Save PCA loadings as pca_loadings.csv and transformed data as pca_transformed.csv."
    ), [], "T27_pca")
    record("T27 PCA", s, f"{len(f)} files", time.time()-t0, f, e)


def t28_tsne(client, nb, mids):
    """t-SNE 2D embedding visualisation."""
    section("T28 — t-SNE Visualisation")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate a synthetic high-dimensional dataset (300 rows, 20 features, 4 classes). "
        "Apply t-SNE (perplexity=30, n_iter=1000) to reduce to 2D. "
        "Create: (1) t-SNE scatter coloured by class with legend, "
        "(2) same plot but marker size represents within-class distance. "
        "Save as tsne_plot.png and tsne_coordinates.csv."
    ), [], "T28_tsne")
    record("T28 t-SNE", s, f"{len(f)} files", time.time()-t0, f, e)


def t29_model_comparison(client, nb, mids):
    """Ensemble model comparison (multiple classifiers)."""
    section("T29 — Multi-Model Comparison (LR, RF, GB, SVM, KNN)")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate a synthetic binary classification dataset (800 rows, 8 features). "
        "Train 5 classifiers: Logistic Regression, Random Forest, Gradient Boosting, SVM, KNN. "
        "Compare using 5-fold cross-validation: accuracy, precision, recall, F1, AUC. "
        "Produce: (1) grouped bar chart of all metrics by model, "
        "(2) box plot of CV accuracy distributions, "
        "(3) ROC curves for all models on a single plot. "
        "Save comparison table as model_comparison.csv."
    ), [], "T29_model_comparison")
    record("T29 Model Comparison", s, f"{len(f)} files", time.time()-t0, f, e)


# ═══════════════════════════════════════════════════════════════════════════
# GROUP D — Time Series Analysis
# ═══════════════════════════════════════════════════════════════════════════

def t30_moving_averages(client, nb, mids):
    """Moving averages + trend line."""
    section("T30 — Moving Averages + Trend Analysis")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate synthetic daily sales data for 2 years (730 days) with trend, seasonality, and noise. "
        "Compute 7-day, 30-day, and 90-day moving averages. "
        "Plot: (1) raw data with all three MAs overlaid, "
        "(2) trend component using polynomial fit, "
        "(3) year-over-year comparison bar chart by month. "
        "Save as moving_averages.png, trend_comparison.png and monthly_yoy.png. "
        "Save aggregated statistics as moving_avg_stats.csv."
    ), [], "T30_moving_averages")
    record("T30 Moving Averages", s, f"{len(f)} files", time.time()-t0, f, e)


def t31_arima_forecast(client, nb, mids):
    """ARIMA/SARIMA forecasting."""
    section("T31 — ARIMA Time Series Forecasting")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate synthetic monthly retail sales data (60 months, with trend + seasonal pattern). "
        "Fit a SARIMA or ARIMA model (if statsmodels not available use exponential smoothing). "
        "Forecast the next 12 months. "
        "Plot: (1) historical + forecast with confidence interval shading, "
        "(2) ACF and PACF plots, "
        "(3) residuals diagnostic plot. "
        "Save forecast values as arima_forecast.csv."
    ), [], "T31_arima_forecast")
    record("T31 ARIMA Forecast", s, f"{len(f)} files", time.time()-t0, f, e)


def t32_seasonal_decompose(client, nb, mids):
    """Seasonal decomposition (trend, seasonal, residual)."""
    section("T32 — Seasonal Decomposition")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate 3 years of synthetic weekly data (156 points) with clear trend, weekly seasonality, and noise. "
        "Apply additive seasonal decomposition (statsmodels). "
        "Plot the four components (observed, trend, seasonal, residual) in a 4-panel figure. "
        "Also plot: seasonality strength by week-of-year as a bar chart. "
        "Save as seasonal_decomposition.png and decomposition_components.csv."
    ), [], "T32_seasonal_decompose")
    record("T32 Seasonal Decomposition", s, f"{len(f)} files", time.time()-t0, f, e)


def t33_rolling_statistics(client, nb, mids):
    """Rolling statistics and Bollinger Bands."""
    section("T33 — Rolling Statistics + Bollinger Bands")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate synthetic daily stock price data for 1 year (252 trading days) using random walk. "
        "Compute: 20-day rolling mean, rolling std, Bollinger Bands (upper/lower), "
        "daily returns distribution. "
        "Plot: (1) price with Bollinger Bands, "
        "(2) rolling volatility (30-day std), "
        "(3) daily returns histogram with fit. "
        "Save as bollinger_bands.png, volatility.png, returns_dist.png and rolling_stats.csv."
    ), [], "T33_rolling_statistics")
    record("T33 Rolling Statistics", s, f"{len(f)} files", time.time()-t0, f, e)


def t34_lag_correlation(client, nb, mids):
    """Lag analysis + autocorrelation."""
    section("T34 — Lag Correlation + Autocorrelation")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate 2 synthetic time series: X (advertising spend) and Y (sales) where Y lags X by 2 weeks, "
        "both over 104 weeks. "
        "Compute: cross-correlation at lags -10 to +10, ACF and PACF for each series. "
        "Plot: (1) CCF plot showing peak at lag 2, "
        "(2) ACF/PACF side-by-side for both series. "
        "Save lag_correlation.csv with CCF values and plots as PNG."
    ), [], "T34_lag_correlation")
    record("T34 Lag Correlation", s, f"{len(f)} files", time.time()-t0, f, e)


# ═══════════════════════════════════════════════════════════════════════════
# GROUP E — Statistical Analysis
# ═══════════════════════════════════════════════════════════════════════════

def t35_hypothesis_tests(client, nb, mids):
    """T-test, Mann-Whitney, chi-square."""
    section("T35 — Hypothesis Testing (t-test, Mann-Whitney, Chi-square)")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate synthetic data for hypothesis testing. "
        "(1) Two-sample t-test: compare mean salary between Group A and Group B (50 each). "
        "(2) Mann-Whitney U test: same groups but non-normal. "
        "(3) Chi-square test: gender vs product preference contingency table (4×2). "
        "For each test: state H0/H1, give test statistic, p-value, conclusion. "
        "Plot: distributions for groups A+B, annotated contingency heatmap. "
        "Save all test results as hypothesis_test_results.csv."
    ), [], "T35_hypothesis_tests")
    record("T35 Hypothesis Tests", s, f"{len(f)} files", time.time()-t0, f, e)


def t36_anova(client, nb, mids):
    """One-way ANOVA + Tukey HSD post-hoc."""
    section("T36 — ANOVA + Post-Hoc Analysis")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate synthetic data for 5 groups (treatment types) with 30 samples each, "
        "measuring response variable (e.g. recovery time). "
        "Perform one-way ANOVA. If significant (p<0.05), apply Tukey HSD post-hoc test. "
        "Plot: (1) box plots with group means marked, "
        "(2) heatmap of pairwise p-values from Tukey test. "
        "Save results as anova_results.csv and tukey_results.csv."
    ), [], "T36_anova")
    record("T36 ANOVA", s, f"{len(f)} files", time.time()-t0, f, e)


def t37_correlation_analysis(client, nb, mids):
    """Pearson + Spearman correlation deep-dive."""
    section("T37 — Pearson vs Spearman Correlation Analysis")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate a synthetic dataset (200 rows, 8 numeric features) with varying correlation structures "
        "(linear, monotonic, non-linear, near-zero). "
        "Compute both Pearson and Spearman correlation matrices. "
        "Plot: (1) Pearson heatmap, (2) Spearman heatmap, "
        "(3) scatter plots for top 4 correlated pairs. "
        "Save both matrices as pearson_corr.csv and spearman_corr.csv."
    ), [], "T37_correlation")
    record("T37 Correlation Analysis", s, f"{len(f)} files", time.time()-t0, f, e)


def t38_outlier_detection(client, nb, mids):
    """Outlier detection with IQR, Z-score, Isolation Forest."""
    section("T38 — Outlier Detection (IQR + Z-score + Isolation Forest)")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate a synthetic dataset (500 rows, 4 features) with ~5% injected outliers. "
        "Detect outliers using: IQR method, Z-score (|z|>3), and Isolation Forest. "
        "Plot: (1) scatter matrix with outliers highlighted in red by each method, "
        "(2) Venn diagram of outlier overlap across methods, "
        "(3) box plots before/after outlier removal. "
        "Save outlier analysis as outlier_report.csv."
    ), [], "T38_outlier_detection")
    record("T38 Outlier Detection", s, f"{len(f)} files", time.time()-t0, f, e)


def t39_distribution_fitting(client, nb, mids):
    """Distribution fitting (Normal, Log-normal, Exponential)."""
    section("T39 — Distribution Fitting + Goodness of Fit")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate 3 samples (300 each): one from normal, one from log-normal, one from exponential distribution. "
        "For each sample, fit Normal, Log-normal, and Exponential distributions using MLE. "
        "Plot: (1) histogram with fitted PDF overlays for each sample, "
        "(2) QQ plots for each fitted distribution. "
        "Compute AIC/BIC for each fit. Save fit results as distribution_fit_results.csv."
    ), [], "T39_distribution_fitting")
    record("T39 Distribution Fitting", s, f"{len(f)} files", time.time()-t0, f, e)


# ═══════════════════════════════════════════════════════════════════════════
# GROUP F — Data Engineering & Export
# ═══════════════════════════════════════════════════════════════════════════

def t40_data_cleaning(client, nb, mids):
    """Data cleaning pipeline with before/after report."""
    section("T40 — Data Cleaning Pipeline")
    t0 = time.time()
    mat = _m(mids, "car_data")
    s, _, f, e = run_agent_task(client, nb, (
        "Using the uploaded car dataset (or generate a synthetic dirty dataset if no file): "
        "perform a full data cleaning pipeline: "
        "(1) identify and report missing values — bar chart of missing % per column, "
        "(2) impute missing numerics with median, missing categoricals with mode, "
        "(3) detect and cap outliers at 1.5×IQR, "
        "(4) remove duplicate rows. "
        "Plot before/after distributions for 3 key numeric columns. "
        "Save cleaned data as cleaned_data.csv and cleaning_report.csv."
    ), mat, "T40_data_cleaning")
    record("T40 Data Cleaning", s, f"{len(f)} files", time.time()-t0, f, e)


def t41_feature_engineering(client, nb, mids):
    """Feature engineering + encoding + scaling."""
    section("T41 — Feature Engineering (encoding + scaling + new features)")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate a synthetic e-commerce dataset (500 rows): "
        "order_value, customer_age, purchase_category, days_since_last_order, total_orders, country. "
        "Apply: one-hot encoding, ordinal encoding, log transform on skewed features, "
        "min-max scaling, polynomial features (degree 2) for order_value × total_orders. "
        "Compare model accuracy (Logistic Regression predicting high-value customer) "
        "before vs after engineering. "
        "Save engineered dataset as feature_engineered.csv and comparison as eng_comparison.csv."
    ), [], "T41_feature_engineering")
    record("T41 Feature Engineering", s, f"{len(f)} files", time.time()-t0, f, e)


def t42_pivot_table_excel(client, nb, mids):
    """Pivot table generation → Excel output."""
    section("T42 — Pivot Tables → Excel Export")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate a synthetic sales dataset (500 rows): "
        "salesperson, region, product, quarter, year, units_sold, revenue. "
        "Create pivot tables: "
        "(1) revenue by region × quarter, "
        "(2) units by product × salesperson (top 5 salespersons), "
        "(3) year-over-year revenue comparison by product. "
        "Save all three pivot tables as separate sheets in pivot_tables.xlsx. "
        "Also save raw data as sales_raw.csv."
    ), [], "T42_pivot_excel")
    record("T42 Pivot Tables Excel", s, f"{len(f)} files", time.time()-t0, f, e)


def t43_multi_sheet_excel(client, nb, mids):
    """Multi-sheet Excel with summary + data + charts."""
    section("T43 — Multi-Sheet Excel Report")
    t0 = time.time()
    mat = _m(mids, "mall_customers")
    s, _, f, e = run_agent_task(client, nb, (
        "Using the Mall Customers dataset (or generate synthetic if unavailable), "
        "create a comprehensive multi-sheet Excel workbook (use openpyxl or xlsxwriter): "
        "Sheet 1: 'Summary' — key statistics table with formatting, "
        "Sheet 2: 'Raw Data' — full dataset with auto-filter and frozen header, "
        "Sheet 3: 'By Gender' — pivot of income/spending by gender, "
        "Sheet 4: 'Age Groups' — binned age group analysis. "
        "Apply conditional formatting (red/green) on numeric columns. "
        "Save as customer_report.xlsx."
    ), mat, "T43_multi_sheet_excel")
    record("T43 Multi-Sheet Excel", s, f"{len(f)} files", time.time()-t0, f, e)


def t44_data_profiling(client, nb, mids):
    """Automated data profiling report → CSV + PNG."""
    section("T44 — Automated Data Profiling Report")
    t0 = time.time()
    mat = _m(mids, "social_ads")
    s, _, f, e = run_agent_task(client, nb, (
        "Profile the Social Network Ads dataset (or use synthetic if unavailable). "
        "Generate a complete profiling dashboard: "
        "(1) missing values heatmap, "
        "(2) data types summary table, "
        "(3) univariate stats for all columns (mean, std, min, 25th, 50th, 75th, max, skew, kurtosis), "
        "(4) correlation matrix, "
        "(5) target variable (Purchased) class balance pie chart. "
        "Save profile as data_profile.csv and all charts as PNG images."
    ), mat, "T44_data_profiling")
    record("T44 Data Profiling", s, f"{len(f)} files", time.time()-t0, f, e)


# ═══════════════════════════════════════════════════════════════════════════
# GROUP G — Reports & Documents
# ═══════════════════════════════════════════════════════════════════════════

def t45_pdf_report(client, nb, mids):
    """Full PDF report with matplotlib figures."""
    section("T45 — PDF Report Generation (matplotlib figures)")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate Python code to produce a multi-page PDF report using matplotlib PdfPages. "
        "The report should contain at least 5 pages: "
        "Page 1: Title page with report title, date, and summary statistics table, "
        "Page 2: Bar chart + line chart side by side, "
        "Page 3: Heatmap of correlations, "
        "Page 4: Scatter plots (2×2 grid), "
        "Page 5: Summary metrics table. "
        "Use a synthetic customer dataset (300 rows). "
        "Save as data_analysis_report.pdf."
    ), [], "T45_pdf_report")
    record("T45 PDF Report", s, f"{len(f)} files", time.time()-t0, f, e)


def t46_html_report(client, nb, mids):
    """Interactive HTML report with embedded charts."""
    section("T46 — HTML Report with Embedded Charts")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate Python code to produce a standalone HTML report (no external CDN dependencies). "
        "The report should include: "
        "(1) a styled summary table of statistics (CSS formatted), "
        "(2) base64-embedded PNG charts (bar, line, scatter), "
        "(3) a simple JavaScript sorting table for data, "
        "(4) a section with key insights as bullet points. "
        "Use a synthetic e-commerce dataset (200 rows). "
        "Save as analysis_report.html."
    ), [], "T46_html_report")
    record("T46 HTML Report", s, f"{len(f)} files", time.time()-t0, f, e)


def t47_excel_report_formatted(client, nb, mids):
    """Fully formatted Excel report with charts."""
    section("T47 — Formatted Excel Report (openpyxl)")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate Python code using openpyxl to create a professionally formatted Excel report. "
        "Include: header row with bold styling and background colour, "
        "alternating row colours, number formatting (currency, %, 2dp), "
        "a bar chart embedded on a Chart sheet, conditional formatting (data bars) "
        "on revenue column, auto-column widths. "
        "Use synthetic monthly KPI data (12 months × 6 KPIs). "
        "Save as kpi_report_formatted.xlsx."
    ), [], "T47_formatted_excel")
    record("T47 Formatted Excel", s, f"{len(f)} files", time.time()-t0, f, e)


# ═══════════════════════════════════════════════════════════════════════════
# GROUP H — Advanced Analytics
# ═══════════════════════════════════════════════════════════════════════════

def t48_anomaly_detection(client, nb, mids):
    """Anomaly detection with Isolation Forest + LOF."""
    section("T48 — Anomaly Detection (Isolation Forest + LOF)")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate a synthetic sensor dataset (500 rows, 3 features) with ~5% injected anomalies. "
        "Apply: Isolation Forest and Local Outlier Factor (LOF). "
        "Plot: "
        "(1) scatter plots with normal/anomaly points coloured differently for each method, "
        "(2) anomaly score distributions, "
        "(3) agreement heatmap between methods. "
        "Save anomaly labels as anomaly_predictions.csv and both plots as PNG."
    ), [], "T48_anomaly_detection")
    record("T48 Anomaly Detection", s, f"{len(f)} files", time.time()-t0, f, e)


def t49_association_rules(client, nb, mids):
    """Market basket association rules (Apriori/FP-Growth)."""
    section("T49 — Association Rules (Market Basket)")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate a synthetic transaction dataset (300 transactions, 15 items, basket analysis). "
        "Apply the Apriori algorithm (use mlxtend or implement manually if not available). "
        "Find rules with min_support=0.1, min_confidence=0.5. "
        "Plot: (1) support vs confidence scatter (size = lift), "
        "(2) top 10 rules by lift as a horizontal bar chart. "
        "Save all rules as association_rules.csv and plots as PNG."
    ), [], "T49_association_rules")
    record("T49 Association Rules", s, f"{len(f)} files", time.time()-t0, f, e)


def t50_nlp_text_analysis(client, nb, mids):
    """NLP: TF-IDF + word frequency + word cloud."""
    section("T50 — NLP Text Analysis (TF-IDF + Frequencies)")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate a synthetic corpus of 50 short documents on 3 topics: "
        "technology, sports, politics (use lorem-ipsum style sentences with domain keywords). "
        "Perform: TF-IDF vectorisation, top-15 terms per topic bar chart, "
        "overall word frequency bar chart (top 30), word cloud of all documents. "
        "Also compute cosine similarity matrix between documents (show as heatmap). "
        "Save TF-IDF matrix as tfidf_matrix.csv, top terms as top_terms.csv, "
        "similarity matrix as doc_similarity.csv, and all charts as PNG."
    ), [], "T50_nlp_analysis")
    record("T50 NLP Text Analysis", s, f"{len(f)} files", time.time()-t0, f, e)


def t51_pca_biplot(client, nb, mids):
    """PCA biplot with loadings on real uploaded data."""
    section("T51 — PCA Biplot on Mall Customers")
    t0 = time.time()
    mat = _m(mids, "mall_customers")
    s, _, f, e = run_agent_task(client, nb, (
        "Using the Mall Customers dataset, apply PCA on numeric features. "
        "Produce: "
        "(1) biplot showing PC1 vs PC2 with feature loading arrows, "
        "(2) explained variance scree plot, "
        "(3) cumulative variance plot, "
        "(4) scatter of PC1 vs PC2 coloured by gender. "
        "Save PC scores as pca_scores.csv and loadings as pca_loadings.csv."
    ), mat, "T51_pca_biplot")
    record("T51 PCA Biplot", s, f"{len(f)} files", time.time()-t0, f, e)


def t52_multi_class_classification(client, nb, mids):
    """Multi-class (4-class) classification with full evaluation."""
    section("T52 — Multi-Class Classification (4 classes)")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate a synthetic 4-class dataset (800 rows, 6 features) — "
        "product quality rating: Poor, Average, Good, Excellent. "
        "Train Random Forest multi-class classifier. "
        "Produce: 4×4 confusion matrix heatmap, per-class precision/recall/F1 bar chart, "
        "macro and weighted average metrics, multi-class ROC curves (one-vs-rest). "
        "Save model as multiclass_rf.pkl and full metrics as multiclass_metrics.csv."
    ), [], "T52_multiclass")
    record("T52 Multi-Class Classification", s, f"{len(f)} files", time.time()-t0, f, e)


def t53_regression_comparison(client, nb, mids):
    """Compare Linear, Ridge, Lasso, ElasticNet, SVR."""
    section("T53 — Regression Model Comparison (5 models)")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate a synthetic regression dataset (600 rows, 10 features, some irrelevant). "
        "Train: Linear Regression, Ridge (α=1), Lasso (α=0.1), ElasticNet, SVR (RBF). "
        "Compare with 5-fold CV: R², MAE, RMSE. "
        "Plot: (1) grouped bar chart of all models × all metrics, "
        "(2) coefficient paths for Ridge/Lasso vs alpha (regularisation path), "
        "(3) predicted vs actual for best model. "
        "Save comparison as regression_comparison.csv and all best models as pkl files."
    ), [], "T53_regression_comparison")
    record("T53 Regression Comparison", s, f"{len(f)} files", time.time()-t0, f, e)


# ═══════════════════════════════════════════════════════════════════════════
# GROUP I — RAG & Corpus Q&A
# ═══════════════════════════════════════════════════════════════════════════

def t54_pdf_rag_qa(client, nb, mids):
    """RAG Q&A on Introduction PDF."""
    section("T54 — PDF RAG Q&A")
    t0 = time.time()
    mat = _m(mids, "intro_pdf")
    s, _, f, e = run_agent_task(client, nb, (
        "Using the uploaded Introduction PDF, answer the following questions: "
        "1) What is the main topic or purpose described? "
        "2) What are the key concepts or features mentioned? "
        "3) What technologies or tools are discussed? "
        "4) What are the stated benefits or outcomes mentioned? "
        "Provide a detailed structured answer with direct quotes where possible."
    ), mat, "T54_pdf_rag")
    record("T54 PDF RAG Q&A", s, f"{len(f)} files", time.time()-t0, f, e)


def t55_rag_with_data_analysis(client, nb, mids):
    """RAG + data analysis combined (PDF + CSV together)."""
    section("T55 — RAG + Dataset Combined Analysis")
    t0 = time.time()
    mat = _m(mids, "intro_pdf") + _m(mids, "mall_customers")
    s, _, f, e = run_agent_task(client, nb, (
        "Using both the uploaded PDF document and the Mall Customers dataset together: "
        "1) Summarise the key points from the PDF in 3 bullet points. "
        "2) Analyse the customer dataset: compute top-level statistics and produce "
        "a summary bar chart of average spending by age group. "
        "3) Write a short paragraph connecting insights from the PDF with the customer data patterns. "
        "Save the combined insight as combined_analysis.txt and the chart as spending_by_age.png."
    ), mat, "T55_rag_data_combined")
    record("T55 RAG + Data Combined", s, f"{len(f)} files", time.time()-t0, f, e)


# ═══════════════════════════════════════════════════════════════════════════
# GROUP J — Stress / Edge Cases
# ═══════════════════════════════════════════════════════════════════════════

def t56_large_pipeline(client, nb, mids):
    """Large-scale synthetic pipeline: 2000-row dataset, full end-to-end."""
    section("T56 — Large-Scale Full Pipeline (2000 rows, 15 features)")
    t0 = time.time()
    s, _, f, e = run_agent_task(client, nb, (
        "Generate a large synthetic retail customer dataset: 2000 rows, 15 features "
        "(customer_id, age, gender, income, education, region, purchase_count, avg_order_value, "
        "days_active, preferred_channel, churn, nps_score, support_tickets, product_category, lifetime_value). "
        "Run a complete end-to-end pipeline: "
        "Step 1: EDA — missing values, distributions (3×5 subplot), correlation heatmap. "
        "Step 2: Feature engineering — encode categoricals, create interaction features. "
        "Step 3: Train 3 models to predict churn — LR, RF, GB. "
        "Step 4: Evaluate all models, plot ROC curves and confusion matrices. "
        "Step 5: Segment customers into 4 clusters using KMeans on RFM features. "
        "Step 6: Generate summary Excel report with 4 sheets. "
        "Save: eda_dashboard.png, model_comparison.png, cluster_scatter.png, "
        "customer_segments.csv, model_metrics.csv, full_report.xlsx."
    ), [], "T56_large_pipeline")
    record("T56 Large-Scale Pipeline", s, f"{len(f)} files", time.time()-t0, f, e)


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _m(mids: Dict[str, str], *keys: str) -> List[str]:
    """Get list of resolved material IDs for given keys."""
    out = []
    for k in keys:
        v = mids.get(k, "")
        if v and not v.startswith("job:"):
            out.append(v)
    return out


# ── Ordered test registry ─────────────────────────────────────────────────────
ALL_TESTS = [
    # number, group, function, short-name
    (1,  "A", t01_bar_chart,             "bar"),
    (2,  "A", t02_histogram_kde,         "histogram"),
    (3,  "A", t03_box_violin,            "boxviolin"),
    (4,  "A", t04_scatter_matrix,        "scattermatrix"),
    (5,  "A", t05_heatmap_annotated,     "heatmap"),
    (6,  "A", t06_pie_donut,             "pie"),
    (7,  "A", t07_line_area,             "linearea"),
    (8,  "A", t08_bubble_chart,          "bubble"),
    (9,  "A", t09_3d_plots,             "3d"),
    (10, "A", t10_radar_chart,           "radar"),
    (11, "A", t11_candlestick,           "candlestick"),
    (12, "A", t12_word_cloud,            "wordcloud"),
    (13, "B", t13_car_eda,               "car"),
    (14, "B", t14_car_regression,        "carregression"),
    (15, "B", t15_mall_segmentation,     "segmentation"),
    (16, "B", t16_mall_advanced_eda,     "malleda"),
    (17, "B", t17_classification_rf,     "classification"),
    (18, "B", t18_social_feature_eng,    "featureeng"),
    (19, "B", t19_covid_trends,          "covid"),
    (20, "C", t20_linear_regression,     "linreg"),
    (21, "C", t21_gradient_boosting,     "gb"),
    (22, "C", t22_svm_classifier,        "svm"),
    (23, "C", t23_decision_tree,         "dtree"),
    (24, "C", t24_logistic_regression,   "logreg"),
    (25, "C", t25_knn,                   "knn"),
    (26, "C", t26_neural_network,        "mlp"),
    (27, "C", t27_pca,                   "pca"),
    (28, "C", t28_tsne,                  "tsne"),
    (29, "C", t29_model_comparison,      "modelcomp"),
    (30, "D", t30_moving_averages,       "movingavg"),
    (31, "D", t31_arima_forecast,        "arima"),
    (32, "D", t32_seasonal_decompose,    "seasonal"),
    (33, "D", t33_rolling_statistics,    "rolling"),
    (34, "D", t34_lag_correlation,       "lag"),
    (35, "E", t35_hypothesis_tests,      "hypothesis"),
    (36, "E", t36_anova,                 "anova"),
    (37, "E", t37_correlation_analysis,  "corranalysis"),
    (38, "E", t38_outlier_detection,     "outlier"),
    (39, "E", t39_distribution_fitting,  "distfit"),
    (40, "F", t40_data_cleaning,         "cleaning"),
    (41, "F", t41_feature_engineering,   "feateng"),
    (42, "F", t42_pivot_table_excel,     "pivot"),
    (43, "F", t43_multi_sheet_excel,     "multiexcel"),
    (44, "F", t44_data_profiling,        "profiling"),
    (45, "G", t45_pdf_report,            "pdfreport"),
    (46, "G", t46_html_report,           "htmlreport"),
    (47, "G", t47_excel_report_formatted,"xlsxreport"),
    (48, "H", t48_anomaly_detection,     "anomaly"),
    (49, "H", t49_association_rules,     "apriori"),
    (50, "H", t50_nlp_text_analysis,     "nlp"),
    (51, "H", t51_pca_biplot,            "pcabiplot"),
    (52, "H", t52_multi_class_classification, "multiclass"),
    (53, "H", t53_regression_comparison, "regcomp"),
    (54, "I", t54_pdf_rag_qa,            "rag"),
    (55, "I", t55_rag_with_data_analysis,"ragdata"),
    (56, "J", t56_large_pipeline,        "largepipeline"),
]


# ── Report ────────────────────────────────────────────────────────────────────
def print_final_report():
    section("FINAL REPORT")
    passed = sum(1 for r in results if r.passed)
    total  = len(results)

    # Group summary
    group_stats: Dict[str, List[bool]] = {}
    for num, grp, fn, _ in ALL_TESTS:
        name = f"T{num:02d} {fn.__doc__ or ''}"
        for r in results:
            if r.name.startswith(f"T{num:02d}") or r.name == fn.__doc__:
                group_stats.setdefault(grp, []).append(r.passed)

    print(f"\n  {'#':<4} {'Test Name':<42} {'Status':<8} {'Dur':>6}  {'Files'}")
    print(f"  {'-'*4} {'-'*42} {'-'*8} {'-'*6}  {'-'*25}")
    for r in results:
        status = _green("PASS") if r.passed else _red("FAIL")
        art = ", ".join(Path(f).name for f in r.artifacts_saved[:2])
        if len(r.artifacts_saved) > 2:
            art += f" +{len(r.artifacts_saved)-2}"
        print(f"       {r.name:<42} {status:<17} {r.duration:>5.0f}s  {art}")

    print()
    # Group pass rate
    groups: Dict[str, Dict] = {}
    for num, grp, fn, _ in ALL_TESTS:
        groups.setdefault(grp, {"label": grp, "pass": 0, "total": 0})
    for r in results:
        for num, grp, fn, _ in ALL_TESTS:
            tname = fn.__doc__ or ""
            if r.name.startswith(f"T{num:02d}"):
                groups[grp]["total"] += 1
                if r.passed:
                    groups[grp]["pass"] += 1

    print(f"  {'Group':<6} {'Name':<30} {'Pass Rate'}")
    grp_names = {"A":"Visualizations","B":"Data Analysis","C":"Machine Learning",
                 "D":"Time Series","E":"Statistics","F":"Data Engineering",
                 "G":"Reports","H":"Advanced Analytics","I":"RAG & Corpus","J":"Stress"}
    for g, stats in sorted(groups.items()):
        p, t = stats["pass"], stats["total"]
        if t == 0:
            continue
        bar = _green("█"*p) + _red("░"*(t-p))
        print(f"  {g:<6} {grp_names.get(g,''):<30} {p}/{t}  {bar}")

    print()
    if passed == total:
        print(f"  {_green(_bold(f'All {total} tests passed! ✔'))}")
    else:
        print(f"  {_yellow(_bold(f'{passed}/{total} tests passed'))}")
        failed = [r.name for r in results if not r.passed]
        print(f"  {_red('Failed: ')} {', '.join(failed[:8])}{'…' if len(failed)>8 else ''}")

    print(f"\n  Output files saved in: {OUTPUT_DIR}")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    global BASE_URL

    all_groups  = sorted(set(g for _,g,_,_ in ALL_TESTS))
    all_shorts  = [s for _,_,_,s in ALL_TESTS]
    all_nums    = [str(n) for n,_,_,_ in ALL_TESTS]

    parser = argparse.ArgumentParser(description="KeplerLab Agentic AI Test Suite (56 tests)")
    parser.add_argument("--base", default=BASE_URL, help="Backend base URL")
    parser.add_argument(
        "--group",
        choices=all_groups + ["all"],
        default="all",
        help="Run all tests in a lettered group (A–J) or 'all'",
    )
    parser.add_argument(
        "--only",
        default="",
        help="Comma-separated test numbers to run, e.g. --only 1,5,20",
    )
    parser.add_argument(
        "--name",
        default="",
        help="Comma-separated short names, e.g. --name bar,svm,arima",
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Skip file uploads (datasets become empty). Good for quick smoke tests.",
    )
    args = parser.parse_args()

    BASE_URL = args.base
    client = APIClient(BASE_URL)

    section("KeplerLab — Agentic AI Pipeline Test Suite  (56 tests)")
    log(f"Backend:    {BASE_URL}", "INFO")
    log(f"Output dir: {OUTPUT_DIR}", "INFO")
    log(f"Run ID:     {_RUN_ID}", "INFO")

    # ── Health check ─────────────────────────────────────────────────────
    try:
        resp = client.get("/health")
        if resp.status_code in (200, 401, 403):
            log(f"Backend reachable (HTTP {resp.status_code})", "PASS")
        else:
            log(f"Unexpected /health response: {resp.status_code}", "WARN")
    except Exception as e:
        log(f"Cannot reach backend at {BASE_URL}: {e}", "FAIL")
        log("Start backend: cd backend && uvicorn app.main:app --reload", "INFO")
        sys.exit(1)

    # ── Auth ─────────────────────────────────────────────────────────────
    section("Setup — Authentication & Notebook")
    if not register_and_login(client):
        log("Auth failed — aborting.", "FAIL")
        sys.exit(1)

    notebook_id = create_notebook(client)
    if not notebook_id:
        log("Notebook creation failed — aborting.", "FAIL")
        sys.exit(1)

    # ── Uploads ──────────────────────────────────────────────────────────
    mat_ids: Dict[str, str] = {}
    if not args.skip_upload:
        section("Setup — Uploading Test Datasets")
        raw = upload_files(client, notebook_id,
                           ["car_data", "mall_customers", "social_ads", "covid_excel", "intro_pdf"])
        mat_ids = poll_jobs(client, raw)
        ready = [k for k, v in mat_ids.items() if not v.startswith("job:")]
        log(f"Materials ready: {ready}", "INFO")
    else:
        log("Skipping uploads (--skip-upload)", "WARN")

    # ── Filter tests ─────────────────────────────────────────────────────
    to_run = list(ALL_TESTS)  # default: all

    if args.only:
        nums = {int(x.strip()) for x in args.only.split(",") if x.strip()}
        to_run = [t for t in ALL_TESTS if t[0] in nums]

    elif args.name:
        names = {x.strip() for x in args.name.split(",")}
        to_run = [t for t in ALL_TESTS if t[3] in names]

    elif args.group != "all":
        to_run = [t for t in ALL_TESTS if t[1] == args.group]

    log(f"Running {len(to_run)} / {len(ALL_TESTS)} test(s)", "INFO")

    # ── Execute ───────────────────────────────────────────────────────────
    for num, grp, fn, short in to_run:
        try:
            fn(client, notebook_id, mat_ids)
        except Exception as exc:
            log(f"Test T{num:02d} ({short}) raised unexpected exception: {exc}", "FAIL")
            record(f"T{num:02d} {fn.__doc__ or short}", False,
                   str(exc)[:120], 0.0)

    # ── Report ────────────────────────────────────────────────────────────
    print_final_report()
    client.close()
    sys.exit(0 if all(r.passed for r in results) else 1)


if __name__ == "__main__":
    main()
