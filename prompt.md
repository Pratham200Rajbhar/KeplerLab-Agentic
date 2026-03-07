Below is a **clear, structured prompt you can give to your AI coding tool** (Cursor / Claude Code / Windsurf / Copilot) to implement the UI and functionality you described.

This prompt focuses on:

* fixing `/agent` UI execution visualization
* rendering agent artifacts (images/files)
* implementing `/code` interactive coding environment
* adding collapsible execution steps
* improving productivity like a real **Agentic platform**

---

# Prompt — Fix `/agent` UI + Implement `/code` Interactive Coding

````markdown
# ROLE

You are a senior full-stack engineer building an **Agentic AI workspace UI**.

The project uses:

Frontend:
Next.js App Router
React
Zustand
TailwindCSS
SSE streaming

Backend:
FastAPI
Agent pipeline
Python execution sandbox
Streaming tool events

The chat UI exists but **agent execution and code tools are not displayed correctly in the frontend**.

Your task is to **fix the agent UI and implement an interactive coding interface**.

---

# TASK 1 — Fix `/agent` Execution Visualization

Currently when `/agent` is used, the execution stages are streamed but **they are not properly visualized in the UI**.

We need a structured execution UI similar to:

Cursor
Perplexity Labs
OpenAI tools

---

## Implement Agent Execution Steps

When the backend streams execution events:

Example events:

event: step_start  
event: code_generated  
event: tool_result  
event: artifact  
event: summary  

The frontend must display them as **collapsible execution stages**.

---

## UI Design

Each agent step must appear as a **collapsible card**.

Example layout:

Agent Execution

Step 1 — Planning  
Step 2 — Generating Code  
Step 3 — Running Tool  
Step 4 — Producing Output  

Each step:

collapsed by default  
expandable when clicked  

When expanded it shows:

generated code  
tool output  
logs  

---

## Example UI

Step Card:

▶ Step 2 — Generate Visualization Code

Click expands:

```python
import pandas as pd
import matplotlib.pyplot as plt
...
````

---

# TASK 2 — Display Agent Generated Artifacts

Agents can generate files or images.

Examples:

PNG charts
CSV files
JSON outputs
HTML files

The frontend must detect artifact type and render correctly.

---

## Image Rendering

If artifact is image:

png
jpg
jpeg
svg

Show image preview directly inside chat.

Example:

AI generated chart
[IMAGE PREVIEW]

---

## File Rendering

If artifact is not an image:

Show a **file card with download button**.

Example UI:

Generated File
data_analysis.csv

Download

---

# TASK 3 — Implement `/code` Interactive Coding Mode

When the user types:

/code write python code to calculate fibonacci

The AI should generate code and display a **code workspace UI**.

---

## Code Block UI

Code must appear inside a **code editor container**.

Features:

syntax highlighting
copy button
run button

Example UI:

Python Code

```python
def fibonacci(n):
    ...
```

Run Code

---

# TASK 4 — Run Code Button

When user clicks **Run Code**:

Send code to backend Python execution API.

Example endpoint:

POST /agent/execute-code

Request:

{
"code": "print('hello')"
}

Response:

stdout
stderr
execution time

---

## Console Output UI

Display result in a console panel.

Example:

Console Output

hello

---

# TASK 5 — Editable Code

User must be able to edit code before running.

Use editable code editor.

Allow direct typing.

---

# TASK 6 — AI Code Editing Box

Under the code editor, add a **small AI instruction input box**.

Purpose:

User can request changes to the code.

Example:

User writes:

add error handling

Send request to backend:

{
"code": "...current code...",
"instruction": "add error handling"
}

Backend returns updated code.

Replace code in editor.

---

# TASK 7 — UI Structure

Create components:

components/chat/

AgentExecutionPanel.jsx
AgentStepCard.jsx
ArtifactViewer.jsx
CodeWorkspace.jsx
ConsoleOutput.jsx

---

# TASK 8 — Streaming Integration

Frontend must support new events:

step_start
code_generated
tool_result
artifact
summary
token
done

Unknown events should not break the UI.

---

# TASK 9 — UX Requirements

Execution steps must be:

collapsible
easy to read
progressive

Artifacts must render automatically.

Code execution must feel like a **mini IDE**.

---

# OUTPUT

Implement:

Agent execution step UI
Collapsible step cards
Artifact rendering system
Interactive code editor UI
Run code functionality
Console output panel
AI code editing input

Ensure everything integrates with the existing chat streaming system.

```

---

# What This Prompt Will Build

Your platform will now support:

### `/agent`

Execution UI like:

```

Agent Execution

▶ Step 1 Planning
▶ Step 2 Generate Code
▶ Step 3 Run Tool
▶ Step 4 Output

```

Click → expand to see details.

---

### Agent Generated Image

Example:

```

Generated Chart
[Image Preview]

```

---

### Generated File

Example:

```

Generated File
sales_analysis.csv
[Download]

```

---

### `/code`

Interactive coding workspace:

```

## Python Code Editor

def fibonacci(n):
...

[Run Code]

## Console

...

```

---

### AI Code Modification

```

Modify Code With AI:
[ add error handling ]

[Apply]

```

---

# Result

Your platform will start behaving like a **real agentic AI development workspace**, similar to:

- Cursor
- OpenAI Code Interpreter
- Perplexity Labs
- Claude Artifacts

---

If you want, I can also give you **one more advanced prompt** that upgrades your `/agent` system into a **full visual agent timeline UI (like OpenAI’s internal tools)** which is much more powerful for debugging and execution tracking.
```
