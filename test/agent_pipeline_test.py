#!/usr/bin/env python3
"""
KeplerLab Agent Pipeline Test Suite
====================================
10 end-to-end test cases covering all major agent capabilities:
  - Web search → file generation
  - Dataset analysis, ML training, visualization
  - Deep research → PDF
  - Math / code execution
  - Multi-step compound tasks

Usage:
  python test/agent_pipeline_test.py [--base-url URL] [--email EMAIL] [--password PASS]

Outputs are saved to ./test/output/<test-name>/
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import io
import json
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

# ── Config ────────────────────────────────────────────────────────────
DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_EMAIL    = os.getenv("TEST_EMAIL",    "test@keplerlab.ai")
DEFAULT_PASSWORD = os.getenv("TEST_PASSWORD", "TestPass1")
OUTPUT_ROOT      = Path(__file__).parent / "output"
STREAM_TIMEOUT   = 600   # seconds per test
MATERIAL_POLL_INTERVAL = 3   # seconds between material-status polls
MATERIAL_POLL_MAX      = 40  # maximum poll attempts (≈ 2 minutes)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("kepler_test")


# ── Result container ──────────────────────────────────────────────────
@dataclass
class TestResult:
    name: str
    passed: bool = False
    error:  str  = ""
    elapsed: float = 0.0
    artifacts: List[str] = field(default_factory=list)
    response_preview: str = ""
    finish_reason: str = ""
    steps_executed: int = 0


# ── SSE stream parser ────────────────────────────────────────────────
def _parse_sse_line(line: str) -> Optional[Tuple[str, dict]]:
    """Return (event_type, data_dict) or None."""
    line = line.strip()
    if not line or line.startswith(":"):
        return None
    if line.startswith("data:"):
        # bare data line without event: prefix — treat as token
        raw = line[5:].strip()
        try:
            return "data", json.loads(raw)
        except json.JSONDecodeError:
            return "data", {"content": raw}
    return None


async def stream_agent(
    client: httpx.AsyncClient,
    token: str,
    notebook_id: str,
    message: str,
    material_ids: Optional[List[str]] = None,
    timeout: int = STREAM_TIMEOUT,
) -> Dict[str, Any]:
    """
    POST /chat with the agent prefix and consume the SSE stream.
    Returns a dict with: response_text, artifacts, meta, finish_reason, steps_executed.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "text/event-stream",
    }
    payload = {
        "message": f"/agent {message}",
        "notebook_id": notebook_id,
        "material_ids": material_ids or [],
        "session_id": str(uuid.uuid4()),
    }

    response_tokens: List[str] = []
    artifacts: List[Dict] = []
    meta: Dict = {}
    finish_reason = "unknown"
    steps_executed = 0
    plan_steps: List[Dict] = []

    # Buffer for reassembling multi-line SSE events
    event_type = "message"
    data_lines: List[str] = []

    async with client.stream(
        "POST",
        "/chat",
        json=payload,
        headers=headers,
        timeout=httpx.Timeout(timeout, connect=15),
    ) as resp:
        resp.raise_for_status()
        async for raw_line in resp.aiter_lines():
            raw_line = raw_line.rstrip("\r")

            if raw_line.startswith("event:"):
                event_type = raw_line[6:].strip()
                continue

            if raw_line.startswith("data:"):
                data_lines.append(raw_line[5:].strip())
                continue

            if raw_line == "" and data_lines:
                # End of one SSE event — process it
                raw_data = "\n".join(data_lines)
                data_lines = []
                try:
                    data = json.loads(raw_data)
                except json.JSONDecodeError:
                    data = {"content": raw_data}

                if event_type == "token":
                    response_tokens.append(data.get("content", ""))

                elif event_type == "agent_artifact":
                    artifacts.append(data)
                    log.info("    ↳ artifact: %s", data.get("filename", "?"))

                elif event_type == "meta":
                    meta = data
                    finish_reason   = data.get("finish_reason", "unknown")
                    steps_executed  = data.get("steps_executed", 0)

                elif event_type == "agent_plan":
                    plan_steps = data.get("steps", [])
                    log.info("    Plan: %d steps → %s",
                             len(plan_steps),
                             " → ".join(s.get("description","")[:40] for s in plan_steps[:3]))

                elif event_type == "agent_status":
                    phase = data.get("phase", "")
                    msg   = data.get("message", "")
                    if phase and msg:
                        log.info("    [%s] %s", phase, msg)

                elif event_type == "done":
                    break

                event_type = "message"

    return {
        "response_text": "".join(response_tokens),
        "artifacts": artifacts,
        "meta": meta,
        "finish_reason": finish_reason,
        "steps_executed": steps_executed,
    }


# ── API helpers ───────────────────────────────────────────────────────
async def login(client: httpx.AsyncClient, email: str, password: str) -> str:
    r = await client.post("/auth/login", json={"email": email, "password": password})
    if r.status_code == 404:
        # Auto-register the test user
        reg = await client.post("/auth/signup", json={
            "email": email, "username": "testrunner", "password": password,
        })
        reg.raise_for_status()
        r = await client.post("/auth/login", json={"email": email, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


async def create_notebook(client: httpx.AsyncClient, token: str, name: str) -> str:
    r = await client.post(
        "/notebooks",
        json={"name": name, "description": "auto-created by test runner"},
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()
    return r.json()["id"]


async def upload_csv(
    client: httpx.AsyncClient,
    token: str,
    notebook_id: str,
    filename: str,
    csv_content: str,
) -> str:
    """Upload a CSV file and return the material_id."""
    files = {"file": (filename, csv_content.encode(), "text/csv")}
    data  = {"notebook_id": notebook_id}
    r = await client.post(
        "/upload",
        files=files,
        data=data,
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()
    return r.json()["material_id"]


async def wait_for_material(
    client: httpx.AsyncClient,
    token: str,
    material_id: str,
    notebook_id: str,
) -> bool:
    """Poll until material processing is completed or failed. Returns True on success."""
    for attempt in range(MATERIAL_POLL_MAX):
        r = await client.get(
            "/materials",
            params={"notebook_id": notebook_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
        for m in r.json():
            if m["id"] == material_id:
                status = m.get("status", "pending")
                log.info("    Material status: %s (attempt %d)", status, attempt + 1)
                if status == "completed":
                    return True
                if status in ("failed", "error"):
                    log.error("    Material processing failed: %s", m.get("error", ""))
                    return False
        await asyncio.sleep(MATERIAL_POLL_INTERVAL)
    log.error("    Material never completed after %d polls", MATERIAL_POLL_MAX)
    return False


async def download_artifact(
    client: httpx.AsyncClient,
    token: str,
    artifact: Dict,
    dest_dir: Path,
) -> Optional[Path]:
    """Download an artifact file to dest_dir. Returns local path."""
    artifact_id = artifact.get("id") or artifact.get("artifact_id")
    filename    = artifact.get("filename", "artifact")
    if not artifact_id:
        return None
    r = await client.get(
        f"/artifacts/{artifact_id}",
        headers={"Authorization": f"Bearer {token}"},
        follow_redirects=True,
    )
    if r.status_code != 200:
        log.warning("    Could not download artifact %s: HTTP %d", filename, r.status_code)
        return None
    dest = dest_dir / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.content)
    return dest


# ── Synthetic data generators ─────────────────────────────────────────
def _titanic_csv() -> str:
    """Small Titanic-like survival dataset (100 rows)."""
    import random
    random.seed(42)
    rows = [["PassengerId","Survived","Pclass","Sex","Age","SibSp","Parch","Fare","Embarked"]]
    for i in range(1, 101):
        pclass = random.choice([1,1,2,3,3,3])
        sex    = random.choice(["male","female"])
        age    = round(random.gauss(30, 14), 1)
        age    = max(1, min(80, age))
        fare   = round(random.uniform(5, 200 if pclass == 1 else 50), 2)
        sibsp  = random.randint(0, 3)
        parch  = random.randint(0, 2)
        emb    = random.choice(["S","C","Q"])
        # Simple survival rule: women and first class survive more
        p_surv = (0.7 if sex == "female" else 0.2) * (1.4 if pclass == 1 else 0.9 if pclass == 2 else 0.7)
        survived = 1 if random.random() < p_surv else 0
        rows.append([i, survived, pclass, sex, age, sibsp, parch, fare, emb])
    out = io.StringIO()
    csv.writer(out).writerows(rows)
    return out.getvalue()


def _sales_csv() -> str:
    """Monthly sales dataset (36 months, 4 product lines)."""
    import random, math
    random.seed(7)
    rows = [["Month","Year","Product","Units","Revenue","Cost","Profit","Region"]]
    products = ["Alpha","Beta","Gamma","Delta"]
    regions  = ["North","South","East","West"]
    for yr in range(2023, 2026):
        for mo in range(1, 13):
            for prod in products:
                base   = {"Alpha":500,"Beta":300,"Gamma":800,"Delta":150}[prod]
                trend  = 1 + (yr - 2023) * 0.08
                season = 1 + 0.3 * math.sin((mo - 3) * math.pi / 6)
                units  = max(10, int(base * trend * season * random.uniform(0.9, 1.1)))
                price  = {"Alpha":99,"Beta":199,"Gamma":49,"Delta":299}[prod]
                rev    = units * price
                cost   = int(rev * random.uniform(0.4, 0.6))
                rows.append([f"{yr}-{mo:02d}", yr, prod, units, rev, cost, rev-cost,
                              random.choice(regions)])
    out = io.StringIO()
    csv.writer(out).writerows(rows)
    return out.getvalue()


def _heart_disease_csv() -> str:
    """Heart disease risk factors dataset (150 rows)."""
    import random, math
    random.seed(99)
    rows = [["age","sex","chest_pain_type","resting_bp","cholesterol","fasting_bs",
             "resting_ecg","max_hr","exercise_angina","oldpeak","st_slope","heart_disease"]]
    for _ in range(150):
        age  = random.randint(30, 75)
        sex  = random.randint(0, 1)
        cp   = random.randint(0, 3)
        rbp  = random.randint(90, 180)
        chol = random.randint(150, 350)
        fbs  = 1 if random.random() < 0.15 else 0
        recg = random.randint(0, 2)
        mhr  = max(70, int(220 - age - random.gauss(0, 12)))
        ea   = 1 if random.random() < 0.3 else 0
        op   = round(random.uniform(0, 5), 1)
        sts  = random.randint(0, 2)
        risk = (age > 55) * 0.3 + (sex == 1) * 0.2 + (cp > 1) * 0.2 + fbs * 0.1 + ea * 0.2
        hd   = 1 if random.random() < min(0.9, risk + 0.1) else 0
        rows.append([age,sex,cp,rbp,chol,fbs,recg,mhr,ea,op,sts,hd])
    out = io.StringIO()
    csv.writer(out).writerows(rows)
    return out.getvalue()


# ── Test cases ────────────────────────────────────────────────────────
@dataclass
class TestCase:
    id: int
    name: str
    message: str
    dataset: Optional[Tuple[str,str]] = None   # (filename, csv_content)
    description: str = ""


TEST_CASES: List[TestCase] = [
    TestCase(
        id=1,
        name="t01_websearch_pdf_report",
        description="Web search → generate PDF report",
        message=(
            "Search the web for the top 5 AI model releases of early 2026 "
            "(GPT-5, Gemini Ultra 2, Claude 4, DeepSeek V3, LLaMA 4 or whatever is latest). "
            "Compile findings into a professionally formatted PDF report with sections: "
            "Executive Summary, Model Comparisons table, Key Capabilities, and Conclusion. "
            "Save as ai_models_report.pdf"
        ),
    ),
    TestCase(
        id=2,
        name="t02_dataset_ml_training",
        description="Dataset → train ML classifier → save metrics + confusion matrix",
        dataset=("titanic_survival.csv", _titanic_csv()),
        message=(
            "Using the uploaded titanic_survival.csv dataset, "
            "train a Random Forest classifier to predict survival. "
            "Perform feature engineering (encode Sex, Embarked), handle missing values. "
            "Split 80/20 train/test. Report accuracy, precision, recall, F1-score. "
            "Save a confusion matrix heatmap as confusion_matrix.png "
            "and a feature importance bar chart as feature_importance.png."
        ),
    ),
    TestCase(
        id=3,
        name="t03_dataset_full_eda",
        description="Dataset → full EDA with 5 charts + summary CSV",
        dataset=("sales_data.csv", _sales_csv()),
        message=(
            "Perform a complete Exploratory Data Analysis on the uploaded sales_data.csv. "
            "Generate: (1) monthly revenue trend line chart, "
            "(2) product revenue comparison bar chart, "
            "(3) profit margin distribution histogram, "
            "(4) region-wise sales heatmap, "
            "(5) correlation matrix of numeric columns. "
            "Also save a summary statistics CSV as eda_summary.csv."
        ),
    ),
    TestCase(
        id=4,
        name="t04_research_ai_news_pdf",
        description="Deep research on recent AI news → structured PDF",
        message=(
            "Research the latest breakthroughs in large language models and AI agents in 2025-2026. "
            "Focus on: model architecture innovations, reasoning improvements, multimodal capabilities, "
            "and real-world deployment case studies. "
            "Save a comprehensive research report as ai_research_2026.pdf with proper citations, "
            "sections: Introduction, Key Developments, Technical Analysis, Industry Impact, and References."
        ),
    ),
    TestCase(
        id=5,
        name="t05_math_computation_plots",
        description="Math computation → solve + visualize differential equations",
        message=(
            "Solve the Lorenz system of differential equations numerically: "
            "dx/dt = σ(y-x), dy/dt = x(ρ-z)-y, dz/dt = xy-βz "
            "with σ=10, ρ=28, β=8/3 and initial conditions (1,1,1) over t=[0,50]. "
            "Generate: (1) 3D Lorenz attractor plot as lorenz_3d.png, "
            "(2) time series of x,y,z as lorenz_timeseries.png, "
            "(3) phase space plots (x-y, x-z, y-z) as lorenz_phase.png. "
            "Print the Lyapunov exponent estimate."
        ),
    ),
    TestCase(
        id=6,
        name="t06_advanced_visualization_dashboard",
        description="Sales dataset → advanced multi-panel dashboard PNG",
        dataset=("sales_dashboard.csv", _sales_csv()),
        message=(
            "Using sales_dashboard.csv, create a professional executive dashboard as a single "
            "high-resolution PNG (1600×1200). "
            "Include 6 panels: (1) YoY revenue growth waterfall chart, "
            "(2) product market share donut chart for 2025, "
            "(3) region performance grouped bar chart, "
            "(4) monthly units sold with 3-month rolling average, "
            "(5) profit margin by product box plot, "
            "(6) revenue forecast for next 6 months using linear regression. "
            "Use a dark theme with professional colors. Save as executive_dashboard.png."
        ),
    ),
    TestCase(
        id=7,
        name="t07_ml_heart_disease_excel",
        description="Heart disease dataset → gradient boosting + report Excel",
        dataset=("heart_disease.csv", _heart_disease_csv()),
        message=(
            "Load heart_disease.csv and build a Gradient Boosting classifier to predict heart disease. "
            "Steps: (1) EDA — print class balance and feature distributions, "
            "(2) train GradientBoostingClassifier with cross-validation (5-fold), "
            "(3) compute ROC-AUC, accuracy, F1, (4) plot ROC curve as roc_curve.png, "
            "(5) save all results — per-fold metrics, best params, classification report — "
            "into an Excel workbook heart_disease_report.xlsx with separate sheets."
        ),
    ),
    TestCase(
        id=8,
        name="t08_code_fractal_generation",
        description="Generate Mandelbrot + Julia set fractals as high-res PNG",
        message=(
            "Write and execute Python code to generate: "
            "(1) A high-resolution Mandelbrot set fractal (1200×900) with colormap 'inferno', "
            "    max_iter=256, saved as mandelbrot.png. "
            "(2) A Julia set fractal for c=-0.7+0.27015j (1200×900) with colormap 'plasma', "
            "    saved as julia_set.png. "
            "(3) A side-by-side comparison image (2400×900) saved as fractals_comparison.png. "
            "Use numpy for vectorized computation — no loops over pixels."
        ),
    ),
    TestCase(
        id=9,
        name="t09_websearch_excel_report",
        description="Web search on tech stocks → structured Excel + chart",
        message=(
            "Search the web for the latest stock performance and analyst ratings for "
            "NVIDIA, Microsoft, Google, Apple, and Meta (as of early 2026). "
            "Build an Excel workbook stock_analysis.xlsx with: "
            "Sheet 1 - raw data table (company, price, 52w-high, 52w-low, PE ratio, analyst rating), "
            "Sheet 2 - formatted summary with conditional formatting, "
            "and separately save a bar chart comparison PNG as stock_comparison.png."
        ),
    ),
    TestCase(
        id=10,
        name="t10_data_statistics_docx",
        description="Generate synthetic statistical dataset → full analysis DOCX",
        message=(
            "Generate a synthetic dataset with 500 rows representing customer transactions: "
            "columns: customer_id, age (18-75, normal dist), income (log-normal), "
            "purchase_amount (correlated with income), product_category (5 cats), "
            "satisfaction_score (1-5), churned (binary, correlated with satisfaction). "
            "Then perform: (1) descriptive statistics, (2) Pearson correlation matrix, "
            "(3) chi-square test of independence (category vs churn), "
            "(4) logistic regression to predict churn (report odds ratios), "
            "(5) K-means clustering (k=3) with silhouette score. "
            "Save full analysis as customer_analysis.docx with embedded charts, "
            "and save the generated dataset as synthetic_customers.csv."
        ),
    ),
]


# ── Test runner ───────────────────────────────────────────────────────
async def run_test(
    tc: TestCase,
    client: httpx.AsyncClient,
    token: str,
) -> TestResult:
    result = TestResult(name=tc.name)
    t0 = time.perf_counter()

    out_dir = OUTPUT_ROOT / tc.name
    out_dir.mkdir(parents=True, exist_ok=True)

    log.info("=" * 70)
    log.info("TEST %d/%d  %s", tc.id, len(TEST_CASES), tc.description)
    log.info("=" * 70)

    try:
        # Create isolated notebook per test
        nb_id = await create_notebook(client, token, f"[Test] {tc.description}")

        # Upload dataset if needed
        material_ids: List[str] = []
        if tc.dataset:
            fname, content = tc.dataset
            log.info("  Uploading dataset: %s …", fname)
            mat_id = await upload_csv(client, token, nb_id, fname, content)
            log.info("  Material ID: %s — waiting for processing…", mat_id)
            ok = await wait_for_material(client, token, mat_id, nb_id)
            if not ok:
                raise RuntimeError(f"Material '{fname}' failed to process")
            material_ids.append(mat_id)
            log.info("  Dataset ready.")

        # Run the agent
        log.info("  Sending task to agent…")
        response = await stream_agent(
            client, token, nb_id, tc.message, material_ids,
        )

        finish_reason   = response["finish_reason"]
        steps_executed  = response["steps_executed"]
        response_text   = response["response_text"]
        artifacts       = response["artifacts"]

        log.info("  Finish reason: %s  |  Steps: %d  |  Artifacts: %d",
                 finish_reason, steps_executed, len(artifacts))
        log.info("  Response preview: %s…", response_text[:120].replace("\n", " "))

        # Download artifacts
        downloaded: List[str] = []
        for art in artifacts:
            local_path = await download_artifact(client, token, art, out_dir)
            if local_path:
                size_kb = local_path.stat().st_size / 1024
                log.info("  Saved: %s  (%.1f KB)", local_path.name, size_kb)
                downloaded.append(str(local_path))

        # Save response text
        (out_dir / "response.txt").write_text(response_text, encoding="utf-8")

        # Save full SSE metadata
        (out_dir / "meta.json").write_text(
            json.dumps(response["meta"], indent=2, default=str), encoding="utf-8",
        )

        # Save test summary
        summary = {
            "test_id": tc.id,
            "name": tc.name,
            "description": tc.description,
            "finish_reason": finish_reason,
            "steps_executed": steps_executed,
            "artifacts_count": len(artifacts),
            "artifacts_downloaded": len(downloaded),
            "downloaded_files": [os.path.basename(p) for p in downloaded],
            "response_length": len(response_text),
        }
        (out_dir / "summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )

        # Determine pass/fail
        has_useful_response = len(response_text.strip()) > 20
        has_artifacts_if_expected = (
            len(artifacts) > 0
            if any(kw in tc.message.lower() for kw in [".png", ".pdf", ".xlsx", ".csv", ".docx"])
            else True
        )

        result.passed           = has_useful_response and has_artifacts_if_expected
        result.artifacts        = downloaded
        result.response_preview = response_text[:200]
        result.finish_reason    = finish_reason
        result.steps_executed   = steps_executed

        if not result.passed:
            result.error = (
                f"No useful response (len={len(response_text)})"
                if not has_useful_response
                else f"Expected artifacts but got 0 (finish_reason={finish_reason})"
            )

    except Exception as exc:
        result.error = f"{type(exc).__name__}: {exc}"
        log.error("  FAILED: %s", result.error)
        # Save error log
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "error.txt").write_text(result.error, encoding="utf-8")
        except Exception:
            pass

    result.elapsed = round(time.perf_counter() - t0, 2)
    status = "✓ PASS" if result.passed else "✗ FAIL"
    log.info("  %s  (%.1fs)", status, result.elapsed)
    return result


# ── Main ──────────────────────────────────────────────────────────────
async def main(args: argparse.Namespace) -> None:
    base_url = args.base_url.rstrip("/")
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    log.info("KeplerLab Agent Pipeline Test")
    log.info("Base URL : %s", base_url)
    log.info("Output   : %s", OUTPUT_ROOT)
    log.info("Tests    : %d cases", len(TEST_CASES))

    async with httpx.AsyncClient(
        base_url=base_url,
        timeout=httpx.Timeout(30, connect=15),
        follow_redirects=True,
    ) as client:
        # --- Authenticate ---
        log.info("\nAuthenticating as %s …", args.email)
        try:
            token = await login(client, args.email, args.password)
            log.info("Authenticated OK.\n")
        except Exception as exc:
            log.error("Authentication failed: %s", exc)
            sys.exit(1)

        # --- Select tests ---
        tests_to_run = TEST_CASES
        if args.tests:
            ids = set(int(x) for x in args.tests.split(","))
            tests_to_run = [t for t in TEST_CASES if t.id in ids]
            log.info("Running selected tests: %s\n", [t.id for t in tests_to_run])

        # --- Run tests ---
        results: List[TestResult] = []
        for tc in tests_to_run:
            result = await run_test(tc, client, token)
            results.append(result)
            # brief pause between tests
            await asyncio.sleep(2)

    # --- Final report ---
    total   = len(results)
    passed  = sum(1 for r in results if r.passed)
    failed  = total - passed
    elapsed = sum(r.elapsed for r in results)

    log.info("\n" + "=" * 70)
    log.info("FINAL REPORT")
    log.info("=" * 70)
    log.info("  Passed: %d / %d   Failed: %d   Total time: %.1fs", passed, total, failed, elapsed)
    log.info("─" * 70)

    for r in results:
        icon = "✓" if r.passed else "✗"
        arts = f"  [{len(r.artifacts)} files]" if r.artifacts else ""
        log.info("  %s  %-38s  %5.1fs  %s%s",
                 icon, r.name[:38], r.elapsed, r.finish_reason[:15], arts)
        if not r.passed and r.error:
            log.info("       Error: %s", r.error[:90])
    log.info("─" * 70)
    log.info("  Output directory: %s", OUTPUT_ROOT)

    # Save machine-readable final report
    report = {
        "summary": {
            "total": total, "passed": passed, "failed": failed,
            "elapsed_total": elapsed,
            "pass_rate": f"{passed/total*100:.1f}%" if total else "0%",
        },
        "results": [
            {
                "id": r.name,
                "passed": r.passed,
                "elapsed": r.elapsed,
                "finish_reason": r.finish_reason,
                "steps_executed": r.steps_executed,
                "artifacts": [os.path.basename(p) for p in r.artifacts],
                "error": r.error,
                "response_preview": r.response_preview[:300],
            }
            for r in results
        ],
    }
    report_path = OUTPUT_ROOT / "report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    log.info("  Report saved: %s", report_path)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="KeplerLab Agent Pipeline Test Suite")
    parser.add_argument("--base-url",  default=DEFAULT_BASE_URL, help="API base URL")
    parser.add_argument("--email",     default=DEFAULT_EMAIL,    help="Test user email")
    parser.add_argument("--password",  default=DEFAULT_PASSWORD, help="Test user password")
    parser.add_argument("--tests",     default="",               help="Comma-separated test IDs to run (default: all)")
    args = parser.parse_args()
    asyncio.run(main(args))
