# Frontend Implementation Prompt — Agent Pipeline UI

You are implementing frontend support for a redesigned **/agent pipeline**.

The frontend is a **Next.js + React application** that communicates with a FastAPI backend using:

* REST APIs
* SSE streaming
* WebSocket updates
* artifact download endpoints

Your task is to implement **all UI changes required for the new agent execution pipeline**.

Do NOT implement features from the **unique agent capabilities roadmap**.

Only implement support for the **core agent pipeline execution system**.

---

# Goal of the New Agent UI

The agent should feel like a **real AI system performing tasks step-by-step**.

Users should see:

* agent thinking
* progress steps
* generated visualizations
* downloadable artifacts
* result summaries

Users should **NOT see raw code by default**.

Technical details must be hidden behind an **expandable section**.

---

# Example User Experience

User input:

```
/agent train ML model on this dataset
```

Chat response should show:

```
Agent Execution

Understanding request
Analyzing dataset
Cleaning data
Training model
Evaluating performance
Generating charts
Preparing results
```

Then show:

* charts
* tables
* downloadable files

---

# Existing Frontend Architecture

Important directories:

```
src/components/chat/
src/components/studio/
src/hooks/
src/stores/
src/lib/api/
```

Existing components:

```
ChatPanel
ChatMessage
ChatMessageList
OutputRenderer
CodePanel
AgentStatusStrip
```

You must extend these components to support the new agent pipeline.

---

# Core Features To Implement

Frontend must support:

1. agent progress streaming
2. artifact visualization
3. secure file downloads
4. chart rendering
5. table previews
6. result summaries
7. collapsible technical details

---

# Agent Progress Streaming

The backend will stream execution events using SSE.

Example event stream:

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

The frontend must display these events as **live progress updates**.

Implement a component:

```
AgentExecutionView
```

This component should display:

```
Agent Execution

✔ Understanding request
✔ Analyzing dataset
✔ Generating analysis code
✔ Executing sandbox
✔ Preparing results
```

Completed steps should show a checkmark.

Current step should show a spinner.

---

# Result Summary Section

After execution completes, the backend returns a summary.

Example summary:

```
Dataset analyzed
Model trained using RandomForest
Accuracy: 91%
```

The summary must appear above the artifacts.

---

# Artifact Rendering System

Artifacts will be returned as metadata objects.

Example artifact structure:

```
{
  id,
  filename,
  mimeType,
  displayType,
  downloadUrl
}
```

Display behavior depends on artifact type.

---

# Image Rendering

If artifact type is:

```
png
jpg
svg
```

Render an image preview.

Example UI:

```
Chart: Confusion Matrix

[ image preview ]

Download
```

Image should be clickable for fullscreen preview.

---

# Table Preview

If artifact is structured data:

```
csv
json
```

Display a table preview.

Show:

* first 10 rows
* scrollable table

Also provide download button.

---

# File Downloads

For artifacts like:

```
pkl
pt
zip
pdf
```

Display a download card.

Example:

```
Generated Files

model.pkl      Download
analysis.pdf   Download
dataset.csv    Download
```

Clicking download must call the secure backend endpoint.

Do NOT expose raw file paths.

---

# Artifact Grouping

Group artifacts visually by category.

Example layout:

```
Charts
 └ confusion_matrix.png

Datasets
 └ cleaned_dataset.csv

Models
 └ model.pkl

Reports
 └ analysis_report.pdf
```

Categories must be determined from artifact metadata.

---

# Expandable Technical Details

Code execution details should be hidden by default.

Add a collapsible section:

```
Technical Details ▼
```

Inside show:

* generated code
* execution logs
* tool outputs

Only render this if backend provides details.

---

# Chat Message Layout

Agent responses should follow this layout:

```
Agent Execution

[progress steps]

Result Summary

[summary text]

Charts

[image previews]

Tables

[data preview]

Downloads

[file download list]

Technical Details ▼
```

Ensure layout works well on both desktop and mobile.

---

# Streaming Message Handling

The chat streaming system must support three types of events:

```
step
artifact
final
```

Behavior:

step → update progress UI
artifact → add artifact to artifact list
final → finalize response

---

# State Management

Use Zustand stores.

Extend the chat store to track:

```
agentSteps
agentArtifacts
agentSummary
agentLogs
```

Ensure state resets when a new agent execution starts.

---

# Agent Status Component

Create a new component:

```
AgentExecutionView
```

Responsibilities:

* display progress steps
* update step status
* render spinner for current step
* show completion state

---

# Artifact Rendering Component

Create:

```
ArtifactGallery
```

Responsibilities:

* group artifacts by category
* render charts
* render tables
* render download cards

---

# Table Viewer Component

Create:

```
ArtifactTablePreview
```

Features:

* show limited rows
* allow scrolling
* display column headers
* handle large datasets gracefully

---

# File Download Component

Create:

```
ArtifactDownloadCard
```

Features:

* file icon
* filename
* download button
* file size display

---

# UI Design Guidelines

Design should match existing UI style.

Use:

* card layouts
* subtle borders
* clear grouping
* consistent spacing

Avoid clutter.

---

# Performance Considerations

Ensure:

* large artifact lists do not freeze UI
* image previews lazy load
* tables paginate if large

---

# Mobile Behavior

On mobile:

* artifacts stack vertically
* images scale to screen width
* downloads remain accessible

---

# Integration Requirements

The implementation must:

* reuse existing chat streaming logic
* integrate with chat messages
* support multiple agent runs per session
* avoid breaking existing chat features

---

# Final Expected Behavior

User runs:

```
/agent analyze this dataset
```

Chat shows:

```
Agent Execution

Understanding request
Analyzing dataset
Cleaning data
Training model
Generating charts
Preparing results
```

Then displays:

Charts
Tables
Downloads

Technical Details (collapsed).

This creates a **clean, interactive agent experience**.
