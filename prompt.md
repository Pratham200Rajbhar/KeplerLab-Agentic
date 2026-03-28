You are a senior AI systems architect and backend engineer. Your task is to refactor and upgrade an existing FastAPI-based RAG + Agent system into a fully production-grade, secure, scalable architecture comparable to GPT/Claude.

The system currently includes:

* FastAPI backend
* ChromaDB (vector database)
* LangGraph agent system
* Tools: rag, web_search, research, python_auto
* Multi-modal ingestion pipeline
* Background processing
* Frontend using Next.js

The system has major issues in:

* retrieval quality
* agent behavior
* ingestion reliability
* unsafe code execution
* lack of observability
* weak system robustness

---

# 🎯 CORE OBJECTIVES

1. Make RAG the PRIMARY system (always runs when materials exist)
2. Convert agent into a CONTROLLED execution layer
3. Implement hybrid retrieval (dense + keyword)
4. Build a secure, production-grade Python sandbox
5. Ensure ingestion is reliable and idempotent
6. Enable real agent capabilities:

   * file generation
   * data analysis
   * workflows
7. Add full observability, logging, and monitoring
8. Ensure system is fault-tolerant and scalable

---

# 🔐 PART 0 — SECURE PYTHON SANDBOX (CRITICAL)

Redesign code execution system completely.

Requirements:

## Execution Isolation

* DO NOT use raw exec() in main process
* Execute code in isolated environment:

  * subprocess with restricted permissions OR
  * containerized sandbox (Docker preferred)

## Security Restrictions

* Disable dangerous modules:

  * os, sys, subprocess, socket, shutil
* Restrict file system access:

  * allow only /data/artifacts/
* Block network access

## Resource Limits

* CPU time limit (e.g. 5–10 seconds)
* Memory limit (e.g. 256–512MB)
* File size limit

## Execution Model

* Write code to temp file
* Run via subprocess:
  python sandbox_script.py
* Capture:

  * stdout
  * stderr
  * generated files

## Validation Layer

* Validate generated code BEFORE execution:

  * AST parsing
  * block unsafe imports
  * limit complexity

## Output Contract

All executions must return:

{
"stdout": "...",
"stderr": "...",
"files": ["file1.pdf", "chart.png"]
}

## Artifact Handling

* Save all files in /data/artifacts/
* Register in database
* generate download tokens

---

# 🔴 PART 1 — INGESTION PIPELINE (ROBUST)

Enhance ingestion with production guarantees:

* deterministic chunking
* idempotent processing
* retry mechanism

Rules:

if stored_chunks != expected_chunks:
mark as FAILED
else:
COMPLETED

Add:

* retry queue for failed jobs
* delete stale embeddings before re-index
* version embeddings (embedding_version)

---

# 🟠 PART 2 — CHUNKING SYSTEM

Upgrade to token-based chunking:

* chunk_size: 300–400 tokens
* overlap: 60–80 tokens

Enhancements:

* semantic boundaries (headings, sections)
* structured data chunking
* metadata enrichment:

  * section_path
  * page
  * offsets

---

# 🟡 PART 3 — HYBRID RETRIEVAL

Implement:

Dense (Chroma) → k=80
Keyword (BM25/Postgres FTS) → k=80

Fusion:

* Reciprocal Rank Fusion

Enhancements:

* query rewriting (2 variants)
* adaptive K based on query complexity

Filtering:

* enforce user isolation
* drop low scores (<0.5)

Diversity:

* apply MMR

---

# 🟢 PART 4 — RERANKING

* input: top 30 candidates
* output: top 8–12

Fix:

* trim chunks before reranking (max 200 tokens)
* handle reranker failure gracefully

---

# 🔵 PART 5 — CONTEXT BUILDER

Strict token control:

* max tokens: ~2000
* structured format (no raw dump)

Prevent:

* duplication
* low-signal chunks
* oversized context

---

# 🟣 PART 6 — AGENT SYSTEM (PRODUCTION MODEL)

## HARD RULES

1. If materials exist:
   → ALWAYS run RAG first

2. Agent is ONLY used for:

   * file generation
   * computation
   * workflows
   * external data

---

## EXECUTION MODEL

Goal → Plan → Execute → Observe → Reflect → Repeat

Planner must produce structured plan:

{
"goal": "...",
"steps": [
{"tool": "rag", "task": "..."},
{"tool": "python_auto", "task": "..."}
]
}

Executor:

* step-by-step execution
* persistent state
* error handling + retries

---

# 🧰 PART 7 — ADVANCED TOOLS

Implement:

1. file_generator_tool
2. chart_generator_tool
3. dataset_query_tool
4. secure_code_interpreter (sandbox)
5. workflow_engine
6. summarization_tool
7. semantic_cache_tool

Each tool must:

* have strict input/output schema
* be independently testable

---

# 🟤 PART 8 — ROUTING SYSTEM

Replace heuristic routing with classifier:

Types:

* factual
* analytical
* computational
* generative
* external

Rules:

* factual → RAG
* computational → RAG + python
* generative → agent
* external → web_search

---

# ⚫ PART 9 — OBSERVABILITY

Add structured logs:

{
"query": "...",
"retrieval_stats": {...},
"rerank_stats": {...},
"context_tokens": 1800,
"agent_used": true,
"execution_time_ms": 1200
}

Add:

* tracing (per request ID)
* error tracking
* performance metrics

---

# ⚪ PART 10 — FAULT TOLERANCE

Implement:

* retry logic (ingestion + agent steps)

* fallback mechanisms:

  * reranker failure → skip rerank
  * empty retrieval → fallback answer

* timeout handling

* circuit breakers for tools

---

# 🧪 PART 11 — TESTING

Add:

* ingestion validation tests
* retrieval recall tests
* sandbox security tests
* agent workflow tests
* load testing

---

# ⚡ FINAL OUTPUT REQUIREMENTS

Provide:

1. Refactored modules:

   * chunker.py
   * embedder.py
   * secure_retriever.py
   * context_builder.py
   * agent system
   * sandbox execution system

2. New modules:

   * sandbox_runner.py
   * hybrid_retrieval.py
   * planner.py
   * executor.py
   * tool_registry.py

3. Config updates

4. Security considerations

---

# 🚀 SUCCESS CRITERIA

* Retrieval is accurate and stable
* Agent performs real-world tasks
* Code execution is fully secure
* System is scalable and fault-tolerant
* No unsafe execution possible
* Logs allow full debugging

Focus ONLY on practical, production-grade implementation.
