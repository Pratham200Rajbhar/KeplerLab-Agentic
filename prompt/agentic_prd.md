# Agent System Implementation Plan

## Overview

This document defines the full redesign plan for the `/agent` pipeline.
The goal is to transform the system into a **true autonomous AI agent** capable of:

* intelligent tool selection
* sandbox code execution
* artifact generation
* automatic visualization
* ML model training
* secure file downloads
* step-based UI updates

The agent should focus on **results instead of exposing raw code**, while still allowing technical users to inspect details through expandable sections.

---

# 1. Agent Execution Lifecycle

The agent workflow should follow a structured execution lifecycle.

User request example:

```
/agent analyze this dataset and train a model
```

Execution pipeline:

```
User Query
   ↓
Intent Detection
   ↓
Task Planner
   ↓
Tool Selector
   ↓
Execution Engine
   ↓
Artifact Detection
   ↓
Result Validator
   ↓
Response Generation
   ↓
Frontend Visualization
```

Each stage maintains a shared **agent state** so the system remains aware of progress and outputs.

---

# 2. Agent State Management

Agent state stores all contextual information during execution.

Tracked elements:

* user query
* execution plan
* current step
* tools used
* generated artifacts
* detected errors
* retry attempts
* dataset metadata

Example state snapshot:

```
Step 1: analyze dataset
Step 2: generate python code
Step 3: run sandbox
Step 4: create charts
Step 5: generate results
```

This state is streamed to the frontend to show real-time progress.

---

# 3. Intelligent Tool Selection

Instead of random tool invocation, the agent must classify tasks.

Examples:

Dataset analysis → Python sandbox
ML training → Python sandbox
Web information → Web search tool
Document questions → RAG retrieval
Diagram generation → Visualization tool

The agent should return structured reasoning explaining why a tool is selected.

---

# 4. Python Sandbox Execution

All computation tasks must run in a secure sandbox environment.

Capabilities:

* numerical computation
* data analysis
* ML model training
* chart generation
* report creation

Execution process:

```
Agent generates Python script
   ↓
Script executed inside sandbox
   ↓
Outputs saved into workspace
   ↓
Workspace scanned for artifacts
```

The sandbox should enforce limits:

* execution timeout
* memory limits
* restricted system access

---

# 5. Artifact Detection

After execution, the system scans the workspace directory.

Typical outputs:

```
chart.png
model.pkl
report.pdf
dataset_summary.csv
```

Each file becomes an **artifact object**.

Metadata stored:

* filename
* file type
* size
* category
* workspace path
* creation timestamp

Artifacts are registered in the database and returned to the frontend.

---

# 6. Artifact Categories

Artifacts should be grouped for easier viewing.

Recommended categories:

Charts
Tables
Models
Reports
Datasets
Files

Example UI structure:

```
Charts
 └ confusion_matrix.png

Models
 └ model.pkl

Reports
 └ analysis_report.pdf
```

---

# 7. Secure File Download System

Artifacts must never expose raw filesystem paths.

Download flow:

```
Frontend requests artifact
   ↓
Secure API endpoint called
   ↓
Token validated
   ↓
File streamed to browser
```

Each artifact includes a **temporary access token**.

Benefits:

* prevents unauthorized downloads
* protects server filesystem
* allows token expiration

---

# 8. Image and Chart Rendering

Images should automatically display inside the chat interface.

Supported formats:

```
PNG
JPG
SVG
```

When an artifact is identified as an image:

* show preview directly in chat
* allow fullscreen viewer
* allow download

Example UI:

```
Chart: Confusion Matrix

[ image preview ]

Download
```

---

# 9. Table Visualization

If the agent produces structured data:

```
CSV
JSON
Parquet
```

The frontend should show a **table preview**.

Example:

```
Dataset Summary

| column | mean | std |
| age | 32 | 8 |
| income | 45000 | 9000 |
```

Users can still download the full dataset.

---

# 10. ML Model Artifact Support

The system should support downloadable machine learning models.

Supported formats:

```
.pkl
.pt
.pth
.joblib
.onnx
.h5
```

Example frontend output:

```
Trained Model

model.pkl
Download
```

---

# 11. Agent Progress Visualization

Instead of showing raw code, the UI should show **agent actions**.

Example:

```
Agent Execution

Understanding request
Analyzing dataset
Generating analysis code
Executing computation
Training model
Generating charts
Preparing results
```

This improves usability for non-technical users.

---

# 12. Expandable Technical Details

Technical users can inspect execution details.

Collapsed section:

```
Technical Details ▼
```

Inside:

* generated code
* tool outputs
* execution logs

This keeps the main UI clean while preserving transparency.

---

# 13. Error Detection and Repair

If execution fails, the agent attempts repair.

Workflow:

```
Execute code
   ↓
Detect error
   ↓
Analyze failure
   ↓
Generate fix
   ↓
Retry execution
```

Retry attempts should be limited.

Recommended limit:

```
maximum retries = 3
```

If failure persists, the agent explains the issue.

---

# 14. Preventing Infinite Retries

The system must detect repeated errors.

Example:

```
same error detected twice
```

The agent should stop retries and return a clear explanation.

---

# 15. Result Summary Generation

After execution completes, the agent produces a structured summary.

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

This summary appears above the artifact list.

---

# 16. Agent Awareness

The agent must remain aware of its working context.

Tracked information:

* datasets loaded
* models trained
* charts generated
* files created

Example memory state:

```
dataset: customer_data.csv
model: RandomForest
accuracy: 91%
```

Future queries can reuse this information.

---

# 17. Example Full Execution

User request:

```
/agent train ML model on this dataset
```

Execution steps:

```
Analyze dataset
Clean data
Train model
Evaluate accuracy
Generate charts
Prepare results
```

Final response includes:

* performance metrics
* charts
* downloadable model
* downloadable report
