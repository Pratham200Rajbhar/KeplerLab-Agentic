<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# KeplerLab — New Agentic System Design Document


***

## What This System Does

User types anything in chat — *"analyze my CSV and make a PDF report"* or *"train a model and export it"* — and the agent figures out the plan, executes it, installs what it needs, and delivers downloadable files. No slash commands required. No manual tool selection.

***

## Core Concepts

### Persistent Workspace

Every user gets a sandboxed container that lives for 30 minutes of idle time. Files written during one message are available in the next. The user's uploaded materials (CSV, Excel) are pre-mounted as read-only inside the container.

### Universal Output

Any file the Python code writes — PDF, DOCX, chart PNG, Excel, JSON, ML model — is automatically detected and surfaced as a downloadable artifact. No special instrumentation needed in the code.

### Dynamic Library Install

If code needs a library not pre-installed, the system checks an approved list, installs it with a pinned version inside the container, and continues. User sees a brief `📦 installing seaborn...` indicator.

***

## System Layers

### Layer 1 — Intent Router

Every chat message passes through a fast LLM classification call. It decides:

- What kind of task this is (analysis, generation, research, Q\&A)
- What output types are expected (chart, PDF, DOCX, data file)
- Whether materials are needed
- What tool sequence to plan

No slash commands needed. User just types naturally.

***

### Layer 2 — Workspace Container

A Docker container per user, created on first agent request, reused for the session.

**What's inside:**

- Full Python 3.11 environment
- Pre-installed: pandas, numpy, matplotlib, plotly, seaborn, scikit-learn, python-docx, reportlab, openpyxl, python-pptx, xgboost, lightgbm, pillow, networkx, sympy, and more
- User's data files mounted read-only at `/workspace/input/`
- Output directory at `/workspace/output/` — everything written here becomes an artifact
- No internet access during code execution
- Memory: 512MB cap, CPU: 1 core

**Lifecycle:**

- Created on first agent call for a user
- Stays alive 30 minutes after last use
- Automatically cleaned up when idle

***

### Layer 3 — Dependency Resolver

Runs before execution, not during.

1. Scans generated code for all `import` statements
2. Classifies each library as: **Pre-installed** / **Approved-on-demand** / **Blocked**
3. For approved-on-demand: installs with pinned version, emits `installing` event to UI
4. For blocked: rewrites code using an approved equivalent via LLM
5. Only then passes code to the container

**Approved-on-demand examples:** `cairosvg`, `missingno`, `folium`, `altair`, `pyvis`
**Blocked:** anything network-capable, filesystem-escaping, or not on the list

***

### Layer 4 — Execution \& File Watcher

Code runs inside the container. Simultaneously, a file watcher polls `/workspace/output/` every 500ms. Every new file triggers:

1. MIME type detection
2. Signed download URL generation (24hr expiry, stored in DB)
3. Immediate `artifact` SSE event to frontend

This means files appear in the UI as they are created — no waiting for execution to finish.

***

### Layer 5 — Self-Healing (3 Stages)

| Stage | Trigger | Action |
| :-- | :-- | :-- |
| Syntax repair | Code fails with stderr | LLM reads error, rewrites code (up to 3x) |
| Library fallback | `ModuleNotFoundError` at runtime | Install from approved list, or rewrite using available lib |
| Template pivot | 3 repair cycles all fail | Switch to pre-built generator (e.g. docx template, chart template) |

User sees only `↻ refining...` in the UI. Never sees a raw error unless all 3 stages fail.

***

### Layer 6 — Artifact Serving

Every generated file gets a record in the database:

- `filename`, `mimeType`, `sizeBytes`
- `downloadToken` — unique signed token
- `tokenExpiry` — 24 hours
- `workspacePath` — where the file lives on disk
- `sourceCode` — the Python that generated it

Files served at: `GET /api/v1/workspace/file/{filename}?token=...`
Auth token required as second factor (not just the signed URL).

***

## SSE Events (What Backend Sends to Frontend)

| Event | When | Data |
| :-- | :-- | :-- |
| `agentstart` | Plan created | plan steps array |
| `toolstart` | Tool begins | label, tool name |
| `installing` | Package install starts | package, version |
| `installed` | Package ready | package, success |
| `install_failed` | Install failed | package, fallback used |
| `codegenerated` | LLM wrote code | code, language |
| `codestdout` | Live output line | content |
| `artifact` | File detected | filename, mime, url, size |
| `repairattempt` | Repair started | attempt number |
| `repairsuccess` | Repair worked | fixed code |
| `pivot` | Template fallback | reason, fallback name |
| `toolresult` | Tool finished | summary, duration, success |
| `token` | Final response text | content chunk |
| `done` | All complete | iterations, artifact count |


***

## Frontend UI — Agent Disclosure Panel

Replaces all current agent UI components (`AgentStepsPanel`, `AgentThinkingBar`, `ArtifactPanel`, `ExecutionPanel`).

### While Executing — Collapsed (default)

```
◉  Analyzing  ∨
```

Single line. Pulsing dot. Current action label. Click to expand.

### While Executing — Expanded

```
◉  Running Python  ∧
────────────────────────────
<> Python  [24 lines]
────────────────────────────
📦 seaborn  ████████░  installing...
────────────────────────────
STDOUT/STDERR ▶
  Processing 1200 rows...
  Missing values handled...
```


### After Done — Collapsed (default)

```
Ran 4 commands, created 2 files  ∨
```


### After Done — Expanded

```
Ran 4 commands, created 2 files  ∧
│  🔍  Searched materials          Search
│  📊  Generated pie chart         Script
│  📦  Installed seaborn           Package
│  📄  Exported report.pdf         report.pdf
```


### Dot Color Meaning

- **Blue pulsing** — working normally
- **Amber pulsing** — repairing/retrying
- **Green static** — done (disappears after 2s)


### Artifacts (always visible above response)

Each file card shows: icon by file type, filename, size, download button. PDF shows page 1 thumbnail on hover.

***

## What Gets Removed

| Current Component | Replaced By |
| :-- | :-- |
| `AgentStepsPanel.jsx` | `AgentDisclosurePanel.jsx` |
| `AgentThinkingBar.jsx` | Pulsing dot in `AgentDisclosurePanel` |
| `AgentActionBlock.jsx` | Tool call rows in done-state list |
| `ArtifactPanel.jsx` | `ArtifactRenderer.jsx` |
| `ExecutionPanel.jsx` | Stdout section inside `AgentDisclosurePanel` |
| `ChartRenderer.jsx` (base64 only) | `ArtifactRenderer.jsx` (all types) |


***

## Database Changes

One new table: **`Artifact`**
Stores every generated file with its signed download token, MIME type, size, source code, and expiry. Linked to user, notebook, session, and message.

***

## Implementation Order

1. Build `kepler-sandbox` Docker image with all libraries pre-installed
2. `workspace_manager` — container create/reuse/cleanup
3. `workspace_watcher` — file detection + artifact DB record
4. `dependency_resolver` — import scan + approved install + blocked rewrite
5. Replace `sandbox.py` execution core with container-based execution
6. Add new SSE events to agent loop
7. Add `Artifact` model to database schema
8. Add new file-serving route
9. Add `agentPanel` state slice to frontend store
10. Wire new SSE handlers in `useChatStream.js`
11. Build `AgentDisclosurePanel.jsx`
12. Build `ArtifactRenderer.jsx`
13. Remove 5 old components
14. Wire disclosure panel into `ChatPanel.jsx`
