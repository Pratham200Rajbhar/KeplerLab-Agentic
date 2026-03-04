<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# now give me prompt.md to instreuct this changes need and also tell remove current agentic pipeline give short prompt not too long i use vibe code tools

Here's your `prompt.md`:

***

```md
# KeplerLab — Agentic System Rebuild

## Remove Completely
- `services/agent/agenticloop.py` — delete, replace with new execution pipeline
- `services/codeexecution/sandbox.py` — delete, replace with Docker workspace
- `services/codeexecution/security.py` — delete, replace with dependency_resolver
- Components: `AgentStepsPanel.jsx`, `AgentThinkingBar.jsx`, `AgentActionBlock.jsx`,
  `ArtifactPanel.jsx`, `ExecutionPanel.jsx`, `ChartRenderer.jsx`

---

## Backend — Build These

### 1. `services/agent/workspace_manager.py`
- Per-user Docker container using Docker SDK
- Container has Python 3.11 with pre-installed: pandas, numpy, matplotlib, seaborn,
  plotly, scikit-learn, python-docx, reportlab, fpdf2, openpyxl, python-pptx,
  xgboost, lightgbm, pillow, networkx, sympy, statsmodels, pyarrow, scipy
- Volumes: user materials mounted read-only at `/workspace/input/`,
  output at `/workspace/output/`
- Network disabled during code execution
- 512MB memory limit, 1 CPU
- Container reused per user for 30min idle TTL, then auto-killed
- In-memory registry: `{userId: {container_id, last_used}}`

### 2. `services/agent/workspace_watcher.py`
- asyncio.Task that polls `/workspace/{userId}/output/` every 500ms
- On new file: detect MIME type, generate signed download token (uuid),
  save `Artifact` record to DB, emit SSE `artifact` event
- Stops when execution ends

### 3. `services/agent/dependency_resolver.py`
- Regex scan generated code for all `import` / `from X import` statements
- Three tiers: PRE_INSTALLED (always available), APPROVED_ON_DEMAND
  (install with pinned version), BLOCKED (rewrite with LLM)
- APPROVED_ON_DEMAND: `{"seaborn":"0.13.2", "wordcloud":"1.9.3",
  "missingno":"0.5.2", "folium":"0.15.1", "altair":"5.2.0", "pyvis":"0.3.2"}`
- For approved: run `pip install pkg==version --quiet --no-deps` inside container,
  emit SSE `installing` → `installed` or `install_failed`
- For blocked: LLM structured call — rewrite code using approved alternatives
- Install timeout: 30s hard cap

### 4. Replace `sandbox.py` execution core
- Use `workspace_manager` to get/create container
- Run `dependency_resolver` before execution
- Execute code via `docker exec` with streaming stdout
- Each stdout line → SSE `codestdout` event
- Start `workspace_watcher` task alongside execution
- Stop watcher after execution ends

### 5. Self-healing — 3 stages in `reflection.py`
- Stage 1 (existing): syntax repair via `coderepairprompt.txt`, max 3 retries
- Stage 2: if `ModuleNotFoundError` → install from approved list or LLM rewrite
- Stage 3: if all repair stages fail → fall back to existing template generators
  (flashcard_generator, quiz_generator etc.), emit SSE `pivot` event

### 6. New SSE events — add to agent loop
```

installing     {package, version}
installed      {package, success, elapsed_ms}
install_failed {package, fallback}
pivot          {reason, fallback_used}
artifact       {filename, mime, url, size}
step_timing    {step, elapsed_ms}

```

### 7. New DB model `Artifact` in `schema.prisma`
```

id, userId, notebookId, sessionId, messageId
filename, mimeType, sizeBytes
downloadToken (unique), tokenExpiry (24hr)
workspacePath, sourceCode, createdAt

```

### 8. New route `GET /api/v1/workspace/file/{filename}?token=`
- Validate token in Artifact table, not expired
- Validate artifact.userId == currentUser.id
- Stream file bytes with correct Content-Type

---

## Frontend — Build These

### 9. Add `agentPanel` slice to `useChatStore.js`
```

status: "idle" | "executing" | "done"
collapsed: true
currentLabel: ""
dotColor: "blue" | "amber" | "green"
currentCode: "", currentLanguage: "python"
stdoutLines: []        // max 50, FIFO
installPills: []       // {package, progress, status}
toolCalls: []          // {type, label, tag, filename?}
artifacts: []          // {filename, mime, url, size}
commandCount: 0, artifactCount: 0

```

### 10. Add handlers to `useChatStream.js`
Map these new SSE events to agentPanel store actions:
- `agentstart` → status="executing", reset panel
- `toolstart` → setCurrentLabel from tool name
- `installing` → addInstallPill
- `installed` / `install_failed` → resolveInstallPill
- `codegenerated` → setCode
- `codestdout` → appendStdout (shift if >50 lines)
- `toolresult` → addToolCall
- `artifact` → addArtifact
- `repairattempt` → dotColor="amber", label="Fixing..."
- `repairsuccess` → dotColor="blue", update code
- `done` → status="done", dotColor="green"

Tool label map:
```

ragSearch→"Searching materials", webSearch→"Searching web",
pythonExecutor→"Running Python", fileGenerator→"Generating file",
dataprofiler→"Analyzing dataset", codeRepair→"Fixing error"

```

### 11. New component `AgentDisclosurePanel.jsx`
Two modes driven by `agentPanel.status`:

**Executing mode (collapsed default):**
`◉ [currentLabel]  ∨`
Expanded shows: syntax-highlighted code block (collapsible),
inline install pills, STDOUT/STDERR collapsible section with live lines.

**Done mode (collapsed default):**
`Ran {N} commands, created {M} files  ∨`
Expanded shows left-border list of tool calls, each with:
icon + label + tag pill (Script / Search / Package / filename)

Dot colors: blue pulsing=working, amber pulsing=repairing, green static=done.
Use pure CSS keyframe animation for pulse. CSS opacity transition for label change.

### 12. New component `ArtifactRenderer.jsx`
Replaces `ChartRenderer.jsx`. Handles:
- `image/*` → inline image
- `application/pdf` → PDF icon + download + preview link
- `.docx / .xlsx` → file icon + download
- `text/csv` → CSV icon + row count + download
- fallback → generic file icon + download

### 13. Wire into `ChatPanel.jsx`
For assistant messages with agent intent, render above response text:
`<AgentDisclosurePanel />` then `<MarkdownRenderer />` then `<ArtifactRenderer />`
During active streaming, `AgentDisclosurePanel` lives directly in `ChatPanel`,
moves into the message on `done` event.
```

