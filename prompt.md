# Fix /agent Agentic Pipeline (General Purpose Autonomous Agent)

Refactor and improve the current **/agent pipeline** so the agent works as a **general-purpose autonomous assistant**, not only for coding tasks.

The agent must understand **any user goal** and choose the correct capability automatically (RAG, research, dataset analysis, file generation, coding, etc.).

The implementation must remove unnecessary steps, simplify the reasoning flow, and ensure the agent **only performs actions required to complete the user request**.

---

# 1. Core Objective

The `/agent` system must:

* handle **any type of task**
* dynamically choose the best tool
* avoid unnecessary searches or steps
* return exactly what the user asked for
* stop execution when the goal is completed

The agent should behave similar to **ChatGPT / Claude tool agents**.

---

# 2. Agent Decision Logic

Before executing any step, the agent must analyze the user request and determine the **task type**.

Possible task categories:

```
knowledge_query
document_analysis
dataset_analysis
web_research
file_generation
coding_task
visualization
general_chat
```

Example routing:

```
PDF / documents → RAG
CSV / Excel → Python analysis
Web knowledge → web search
Report generation → document generation
Charts → python visualization
Coding → code generation
```

The agent must automatically select the correct tool.

---

# 3. Remove Unnecessary Actions

Fix current problems where the agent:

* runs unnecessary web searches
* generates unrelated explanations
* performs extra reasoning steps
* continues execution after goal completion

Add rule:

```
If the user request is already solvable with available data,
do not perform additional searches.
```

The agent must stop execution immediately when the goal is achieved.

---

# 4. Simplified Agent Execution Flow

Rewrite the pipeline as:

```
User Request
     ↓
Intent Analysis
     ↓
Task Planning
     ↓
Tool Selection
     ↓
Tool Execution
     ↓
Observation
     ↓
Goal Completed?
     ↓
Return Result
```

Avoid deep recursive reasoning loops.

Maximum steps:

```
MAX_AGENT_STEPS = 8
```

---

# 5. Tool Selection Rules

Available tools:

```
rag_search
web_search
research
python
artifact_generation
```

The agent must choose tools based on task type.

Examples:

```
Analyze dataset → python
Summarize document → rag
Find latest information → web_search
Generate report → artifact_generation
```

Do not call tools unnecessarily.

---

# 6. Output Policy

The agent must **only return what the user requested**.

Rules:

* no unnecessary explanations
* no unrelated information
* concise responses
* produce files when requested
* avoid filler text

Example:

User request:

```
give top 10 cities in india as pdf
```

Correct output:

```
PDF file generated
```

No extra discussion.

---

# 7. Agent Prompt Improvement

Rewrite the system prompt controlling the agent.

Example:

```
You are an autonomous task-solving AI agent.

Your goal is to complete the user's request using the most efficient method.

Rules:
- Understand the user's objective clearly.
- Select the correct tool for the task.
- Avoid unnecessary reasoning or searches.
- Only execute steps required to achieve the goal.
- Stop immediately when the goal is completed.
- Return only the requested output.

Do not generate irrelevant explanations or additional information.
```

---

# 8. Error Handling

If a tool fails:

1. retry once
2. choose alternative tool if possible
3. return clear error message

Do not enter infinite retry loops.

---

# 9. UI Behavior

While the agent is working:

Show only **high-level steps** in the UI:

```
Planning task
Collecting information
Processing data
Generating result
```

Do not expose internal reasoning logs.

---

# 10. Production Requirements

The new agent pipeline must be:

* modular
* deterministic
* efficient
* async-safe
* production ready

Ensure the agent can handle **all user tasks**, not only coding workflows.
