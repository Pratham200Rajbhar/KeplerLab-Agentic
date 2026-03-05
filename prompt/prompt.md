# Implementation Prompt — Agent Pipeline System

You are implementing a **complete redesign of the `/agent` execution pipeline** inside an existing AI learning platform backend.

The backend is built with:

* FastAPI
* PostgreSQL
* ChromaDB
* LangChain / LangGraph
* Python sandbox execution
* artifact storage system
* SSE streaming

Your task is to **implement the system described in `agent_pipeline_plan.md`**.

IMPORTANT RULES:

* Do NOT implement features from `unique_agent_capabilities.md`.
* Focus only on the **core agent execution pipeline**.
* Preserve compatibility with the current backend architecture.
* Follow the design described below.
* Do NOT expose internal filesystem paths to the frontend.
* Artifacts must be accessed via secure token endpoints.

---

# System Goals

The `/agent` mode should behave like a **true autonomous AI agent** that:

* analyzes the user request
* selects tools intelligently
* executes tasks in a Python sandbox
* generates artifacts (charts, datasets, models)
* automatically displays visual outputs
* allows secure download of generated files
* hides raw code by default
* streams execution steps to the frontend

The user should see **agent progress steps**, not raw code.

Example UI steps:

```
Understanding request
Analyzing dataset
Generating analysis code
Executing computation
Training model
Generating charts
Preparing results
```

Technical details (generated code and logs) must remain **hidden behind an expandable section**.

---

# Existing Backend Context

You are modifying the backend described in the documentation.

Important directories:

```
backend/app/routes/
backend/app/services/
backend/app/services/agent/
backend/app/services/code_execution/
backend/app/services/storage_service.py
backend/app/services/job_service.py
backend/app/services/ws_manager.py
```

Artifacts are already stored using the **Artifact database model**.

Workspace directories exist at:

```
data/workspaces/
```

Sandbox execution already exists in:

```
services/code_execution/
```

Reuse these systems where possible.

---

# New Agent Architecture

Implement a **structured agent pipeline** consisting of the following stages.

```
User Query
↓
Intent Detection
↓
Task Planning
↓
Tool Selection
↓
Execution Engine
↓
Artifact Detection
↓
Result Validation
↓
Response Generation
```

Each stage must update a shared **Agent State object**.

---

# Agent State System

Implement a persistent runtime state object.

The agent state should track:

* user query
* execution plan
* current step index
* tools used
* generated artifacts
* errors encountered
* retry attempts
* dataset metadata

This state must be used for:

* streaming progress
* decision making
* debugging

State must be serializable.

---

# Tool Selection System

The agent must determine which tool to use based on the task.

Example mappings:

Dataset analysis → Python sandbox
ML training → Python sandbox
Numerical computation → Python sandbox
Document questions → RAG retriever
Web information → web search tool

The tool selector must return:

* tool name
* reasoning for selection
* expected output type

Do not allow arbitrary tool execution.

---

# Python Sandbox Execution

All computational tasks must run inside the existing sandbox environment.

Capabilities expected:

* dataset analysis
* machine learning training
* statistics
* visualization
* report generation

Execution workflow:

```
Agent generates Python script
↓
Script runs inside sandbox
↓
Outputs written to workspace
↓
Workspace scanned for artifacts
```

Sandbox constraints:

* execution timeout
* memory limits
* restricted system access

---

# Artifact Detection System

After execution finishes, the workspace must be scanned for outputs.

Typical files include:

```
chart.png
model.pkl
report.pdf
dataset_summary.csv
```

Each file becomes an **artifact object**.

Artifacts must store:

* filename
* category
* mime type
* size
* workspace path
* download token
* expiration time

Artifacts must be saved using the existing database model.

---

# Artifact Categories

Classify artifacts automatically:

Charts
Tables
Models
Reports
Datasets
Files

Example classification:

```
PNG → Chart
CSV → Dataset/Table
PKL/PT → Model
PDF → Report
```

---

# Secure Artifact Download

Artifacts must not expose filesystem paths.

Files must be accessed using a secure endpoint:

```
GET /workspace/file/{artifact_id}?token={download_token}
```

The backend must:

1. validate the token
2. verify expiration
3. stream the file

Tokens should expire after a fixed duration.

---

# Visualization Handling

If the artifact is an image:

```
PNG
JPG
SVG
```

The frontend should display the image inline.

If the artifact is tabular data:

```
CSV
JSON
```

The frontend should render a table preview.

If the artifact is a binary file:

```
PKL
PT
ZIP
PDF
```

The frontend should show a download button.

---

# Agent Progress Streaming

The backend must stream agent execution steps using SSE.

Example events:

```
event: step
data: Understanding request

event: step
data: Analyzing dataset

event: step
data: Generating analysis code

event: step
data: Executing sandbox

event: step
data: Preparing results
```

The frontend uses these messages to display progress.

---

# Error Handling and Repair

If sandbox execution fails:

1. detect error
2. analyze error
3. generate corrected code
4. retry execution

Maximum retries:

```
3 attempts
```

If the same error repeats twice, stop retrying.

Return a clear error explanation.

---

# Result Summary

After execution finishes, generate a summary.

Example:

```
Dataset analyzed
Model trained using RandomForest
Accuracy: 91%

Artifacts generated:
confusion_matrix.png
feature_importance.png
model.pkl
```

This summary is displayed above the artifacts.

---

# Agent Awareness

The agent must remain aware of execution context.

Track:

* datasets loaded
* models trained
* charts generated
* artifacts produced

This allows follow-up queries like:

```
improve the model
generate more charts
```

The agent can reuse prior context.

---

# Expected Deliverables

Implement the following modules inside:

```
services/agent/
```

Required components:

* pipeline manager
* agent state object
* planner
* tool selector
* execution engine
* artifact detector
* result validator
* error repair system

Ensure all modules integrate with existing services.

---

# Implementation Constraints

The implementation must:

* maintain FastAPI compatibility
* integrate with existing job system
* support SSE streaming
* reuse sandbox execution
* reuse artifact database model
* avoid breaking existing endpoints

---

# Final Output Behavior

Example user request:

```
/agent train ML model on this dataset
```

Expected user-visible output:

```
Agent Execution

Understanding request
Analyzing dataset
Cleaning data
Training model
Evaluating performance
Generating charts
Preparing results

Accuracy: 91%

Charts:
[confusion matrix image]

Downloads:
model.pkl
analysis_report.pdf
```

Code and execution logs remain hidden unless expanded.

---

# Implementation Instructions

1. Analyze the current codebase.
2. Identify existing components that can be reused.
3. Implement missing modules.
4. Integrate the new pipeline with `/agent` requests.
5. Ensure artifacts are detected and returned.
6. Ensure streaming works correctly.
7. Write clean modular code.
8. Avoid breaking current API behavior.

Focus on **robust architecture, clarity, and maintainability**.
