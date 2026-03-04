You are a senior backend engineer working on KeplerLab — a FastAPI + LangGraph AI learning platform.
Reference: backend.md (current state), problem.md (known issues).
Apply every fix and feature change below. Do not skip any section.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 1 — INTENT ROUTING (remove LLM classification)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DELETE `services/agent/intent.py` entirely.
DELETE any LLM-based intent classification calls from `routes/chat.py` and `services/agent/graph.py`.

Replace with pure direct routing in `routes/chat.py`:

ROUTING LOGIC (strict, no inference):
  - Request has `intent_override: "AGENT"`       → route to agentic loop (Section 5)
  - Request has `intent_override: "WEB_RESEARCH"` → route to deep research pipeline (Section 6)
  - Request has `intent_override: "CODE_EXECUTION"` → route to python sandbox directly
  - Request has `intent_override: "WEB_SEARCH"`  → quick web search + LLM summarize
  - No `intent_override` field at all             → RAG pipeline (Section 7) — default, fastest path

RULE: Intent is ALWAYS set explicitly by the frontend slash command.
The backend NEVER calls an LLM to guess or classify intent.
Remove all keyword matching, LLM routing prompts, and fallback classifiers.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 2 — CRITICAL BUG FIXES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FIX 1 — MISSING PROMPT TEMPLATE FILES (will crash at runtime)
Create the following files in `app/prompts/` with appropriate content:
- `presentation_intent_prompt.txt`
- `presentation_strategy_prompt.txt`
- `slide_content_prompt.txt`
Add loader functions with `@lru_cache` for all three in `prompts/__init__.py`.
While you are there: add loaders for `podcast_script_prompt.txt`, `podcast_qa_prompt.txt`,
`code_generation_prompt.txt`, `code_repair_prompt.txt`, `data_analysis_prompt.txt` —
they currently have no loader and are loaded via raw `open()` in services.
Standardize ALL prompt loading through `prompts/__init__.py`. Delete all raw `open()` calls in services.

FIX 2 — GPU MANAGER DUAL LOCK (CUDA race condition)
Rewrite `gpu_manager.py`:
- Use a single `asyncio.Lock` as the only GPU gate
- Sync callers must acquire via: `asyncio.run_coroutine_threadsafe(lock.acquire(), loop).result()`
- No sync threading.Lock anywhere — one lock, one path
- Add `gpu_session()` as async-only context manager; remove the dead sync version

FIX 3 — ASYNC PPT DROPS EXTRA MATERIALS
Fix `generate_ppt_async` in `routes/ppt.py`:
- Accept `material_ids: List[str]` (not just single `material_id`)
- Process all provided material IDs, identical to sync version
- Remove the duplicate `/api/presentation/slides/...` route registration
  Fix the Next.js rewrite in `next.config.mjs` proxy config instead

FIX 4 — NOTEBOOK DELETE LEAVES ORPHANED CHAT DATA
In `notebook_service.py:delete_notebook()`, before deleting materials add:
  prisma transaction that deletes in order:
  1. ResponseBlock (where chatMessage.chatSession.notebookId = id)
  2. ChatMessage (where chatSession.notebookId = id)
  3. ChatSession (where notebookId = id)
  Then delete materials, generated content, and notebook record — all in one transaction.

FIX 5 — MATERIAL DELETE IS NOT ATOMIC
Wrap the full deletion sequence in `material_service.py` in a try/except:
  Step 1: Delete ChromaDB vectors (thread pool)
  Step 2: Delete file from disk
  Step 3: Delete DB record
On any step failure: log the exact step that failed, attempt reverse compensation,
and return a clear error — never silently leave partial state.

FIX 6 — UPLOAD SIZE MISMATCH
In `main.py` middleware setup, derive body size limit from config:
  `limit = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024`
Remove hardcoded 100MB value. Config is the single source of truth.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 3 — PERFORMANCE FIXES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PERF 1 — PARALLELIZE MATERIAL TEXT LOADING
In `routes/utils.py:require_materials_text()`:
  Before: sequential for-loop over material IDs
  After:  `texts = await asyncio.gather(*[require_material_text(mid, uid) for mid in material_ids])`

PERF 2 — TOKEN USAGE: SQL AGGREGATION NOT PYTHON SUM
In `token_counter.py:get_user_monthly_usage()`:
  Replace fetch-all + Python sum with:
  `result = await prisma.usertokenusage.aggregate(where={...}, _sum={"tokensUsed": True})`

PERF 3 — UNIFY EMBEDDING MODELS (fixes retrieval accuracy bug)
Currently: ChromaDB stores all-MiniLM-L6-v2 (384-dim) vectors,
           RAG pipeline queries with bge-m3 (1024-dim) vectors.
These are different vector spaces — similarity scores are semantically meaningless.
Fix:
  - Remove all-MiniLM-L6-v2 from ChromaDB EmbeddingFunction config
  - Configure ChromaDB collection to use BAAI/bge-m3 as its EmbeddingFunction
  - Update `cli/reindex.py` to re-embed all existing materials using bge-m3
  - Remove all-MiniLM-L6-v2 from startup warmup and requirements.txt

PERF 4 — DB INDEXES ON HOT TABLES
Add to `prisma/schema.prisma`:
  On ChatMessage:      @@index([notebookId])
                       @@index([notebookId, createdAt])
  On GeneratedContent: @@index([notebookId, userId, contentType])
Run `prisma migrate dev` after.

PERF 5 — BULK CHROMADB DELETE ON NOTEBOOK DELETION
In `notebook_service.py:delete_notebook()`, delete all material vectors in a single
ChromaDB batch call (`collection.delete(where={"notebook_id": id})`) instead of
N individual thread pool calls.

PERF 6 — JOB TABLE CLEANUP CRON
Add a periodic asyncio task to `worker.py` that runs every 24 hours:
  Delete BackgroundJob records where:
    status IN ('completed', 'failed') AND createdAt < (now - 30 days)
Log count of deleted records.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 4 — DATABASE SCHEMA FIXES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SCHEMA 1 — ADD MISSING FOREIGN KEYS
Add Prisma FK relations with `onDelete: Cascade` for `notebookId` field in:
  - AgentExecutionLog
  - CodeExecutionSession
  - ResearchSession
  - PodcastSession
These currently store notebookId as a plain string with no referential integrity.

SCHEMA 2 — REPLACE MATERIALIDS STRING ARRAYS WITH JOIN TABLES
Replace `materialIds String[]` in GeneratedContent and PodcastSession with:
  model GeneratedContentMaterial {
    generatedContentId  String
    materialId          String
    generatedContent    GeneratedContent @relation(fields: [generatedContentId], references: [id], onDelete: Cascade)
    material            Material         @relation(fields: [materialId], references: [id], onDelete: Cascade)
    @@id([generatedContentId, materialId])
  }
  Same pattern for PodcastSessionMaterial.
Write a migration script that reads existing String[] values and inserts join table rows.

SCHEMA 3 — CONVERT STRING FIELDS TO ENUMS
  User.role           → enum UserRole { USER ADMIN }
  ExplainerVideo.status → enum VideoStatus { pending processing completed failed }
  PodcastExport.status  → enum ExportStatus { pending processing completed failed }

SCHEMA 4 — METADATA FIELDS AS JSON
All models with `metadata String @db.Text` that store JSON:
  Change to `metadata Json?`
  Update all Prisma reads/writes accordingly.

SCHEMA 5 — SOFT DELETE ON USERS
Add `deletedAt DateTime?` to User model.
Update delete endpoint to set `deletedAt = now()` instead of hard delete.
Add `where: { deletedAt: null }` filter to all user queries.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 5 — /agent FULLY AGENTIC OPEN-LOOP SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Triggered ONLY when `intent_override = "AGENT"` (from /agent slash command).

PHILOSOPHY:
No fixed pipeline. No predetermined steps. No linear tool sequence.
The agent receives a user query + selected material_ids + notebook_id and
autonomously decides what tools to call, in what order, how many times.
Python is the universal output mechanism — if the agent can write Python for it, it does.
The agent loop continues until the goal is met or 10 iterations are reached.

LANGGRAPH STATE MACHINE:

  AgentState {
    query: str
    material_ids: List[str]
    notebook_id: str
    plan: str                    # current reasoning step
    tool_history: List[ToolCall] # all prior tool calls + results
    artifacts: List[Artifact]    # charts, files, tables produced so far
    iteration: int               # max 10
    final_response: str          # set by response_node when done
  }

  NODES:
  
  planner_node(state) → state
    Given: query + tool_history (what has been done so far)
    LLM produces: next tool to call + args + one-line reasoning
    Output: updates state.plan
    RULE: planner only picks the NEXT single tool call — no multi-step pre-planning
    RULE: if tool_history is empty, planner starts fresh; otherwise it builds on prior results
  
  tool_executor_node(state) → state
    Executes the tool chosen by planner_node
    Appends result to state.tool_history
    Emits SSE `agent_step` event (running → done/failed)
    If tool is python_executor and it errors → automatically call code_repair → retry once
  
  reflection_node(state) → "replan" | "respond"
    LLM evaluates: has the user's original query been fully answered by tool_history + artifacts?
    If yes → return "respond" → route to response_node
    If no  → return "replan"  → route back to planner_node
    If iteration >= 10 → force "respond" regardless
    Emits SSE `agent_reflection` event with reasoning
  
  response_node(state) → final SSE stream
    Synthesizes all tool_history outputs + artifacts into final markdown response
    Embeds chart references inline: ![Chart](artifact:0)
    Lists downloadable files at bottom
    Streams as `token` SSE events

TOOL REGISTRY (services/agent/tools/):

  rag_search(query: str, material_ids: List[str], k: int = 10) → RagResult
    Semantic search over user's materials via ChromaDB + BGE reranker
    Returns: ranked chunks with source doc name, page ref, similarity score

  python_executor(code: str, context: dict = {}) → ExecutionResult
    Full sandboxed Python execution
    Available packages: pandas, numpy, matplotlib, plotly, scipy, sklearn,
                        networkx, graphviz, seaborn, pillow, openpyxl
    Auto-captures:
      - plt.savefig() or fig.write_image() → base64 PNG, added to state.artifacts
      - Any DataFrame assigned to variable `result` or `output` → JSON table artifact
      - Any file written to /tmp/agent_output/ → downloadable file artifact
      - stdout → text output
    Returns:
      {
        "stdout": str,
        "charts": [{"data": "base64png", "filename": "chart_1.png"}],
        "tables": [{"columns": [], "rows": []}],
        "files":  [{"path": str, "filename": str, "mime": str}],
        "error":  str | null
      }
    On error: auto-call code_repair(code, error) → retry the fixed code once
              If repair also fails → return error in ExecutionResult, do not raise

  file_generator(type: str, content: Any, filename: str) → FileArtifact
    Supported types: "pdf", "docx", "pptx", "csv", "json", "txt", "md"
    Returns artifact path added to state.artifacts

  web_search(query: str, n_results: int = 5) → List[SearchResult]
    Quick web search, returns title + snippet + URL per result
    Does NOT fetch full page content (that is /research only)

  code_repair(code: str, error: str) → str
    Rewrites broken Python using code_repair_prompt.txt
    Returns corrected code (not executed — executor retries)

  flashcard_generator(material_ids, count, language) → FlashcardResult
  quiz_generator(material_ids, count, difficulty, language) → QuizResult
  mindmap_generator(material_ids) → MindmapResult
  ppt_generator(material_ids, options) → PptArtifact
    All existing generation services wrapped as agent-callable tools

SSE EVENT STREAM (emit from tool_executor_node and response_node):

  {"type": "agent_start",      "plan": "I will search your materials then generate a visualization..."}
  {"type": "agent_step",       "step": {"id": 1, "tool": "rag_search",       "status": "running",  "description": "Searching for neural network concepts"}}
  {"type": "agent_step",       "step": {"id": 1, "tool": "rag_search",       "status": "done",     "result_summary": "Found 12 chunks from 3 documents", "duration_ms": 840}}
  {"type": "agent_step",       "step": {"id": 2, "tool": "python_executor",  "status": "running",  "description": "Building comparison chart"}}
  {"type": "artifact",         "artifact": {"type": "chart",  "index": 0, "data": "base64...", "filename": "comparison.png"}}
  {"type": "artifact",         "artifact": {"type": "file",   "index": 1, "filename": "report.csv", "url": "/files/agent/abc123.csv"}}
  {"type": "artifact",         "artifact": {"type": "table",  "index": 2, "columns": [], "rows": []}}
  {"type": "agent_step",       "step": {"id": 2, "status": "done", "duration_ms": 2100}}
  {"type": "agent_reflection", "reflection": "Chart generated successfully. User question answered. Composing response."}
  {"type": "token",            "content": "## Analysis\n\nBased on your materials..."}
  {"type": "done",             "artifacts": [...]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 6 — /research DEEP WEB RESEARCH PIPELINE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Triggered ONLY when `intent_override = "WEB_RESEARCH"` (from /research slash command).
This is a dedicated 5-step pipeline, NOT the agent loop.

STEP 1 — QUERY DECOMPOSER
  Single LLM call with the user's query.
  Produce 4-6 targeted sub-questions that together fully cover the topic.
  Output: [{"sub_question": str, "search_query": str}]
  Emit: {"type": "research_phase", "phase": "decomposing", "detail": "Breaking into N sub-questions"}

STEP 2 — PARALLEL WEB SEARCH
  Run all sub-question searches concurrently: asyncio.gather(*[search(sq) for sq in sub_questions])
  Collect top 5 URLs per sub-question.
  Deduplicate URLs across all sub-questions (keep first occurrence).
  Emit: {"type": "research_phase", "phase": "searching", "detail": "Running N parallel searches"}

STEP 3 — PARALLEL CONTENT FETCHING
  For top 3 unique URLs per sub-question (up to 15 total after dedup):
    Fetch concurrently via asyncio.gather()
    Use Playwright for JS-heavy sites (detect by failed BS4 extraction)
    Use requests + BeautifulSoup4 as default (faster)
    Per-URL timeout: 10 seconds — skip on timeout, do not block pipeline
    Extract: title, full body text (strip nav/footer/ads), publication date, domain
  Emit per source found:
    {"type": "research_source", "source": {"index": N, "title": str, "url": str, "domain": str, "snippet": str, "relevance_score": float}}
  Emit: {"type": "research_phase", "phase": "fetching", "detail": "Fetching content from N sources"}

STEP 4 — SYNTHESIZER
  Single LLM call with all fetched content passed as context.
  System prompt instructs structured JSON output:
  {
    "executive_summary": str,
    "key_findings": [
      {"finding": str, "confidence": "high|medium|low", "source_indices": [int]}
    ],
    "conflicting_information": [
      {"topic": str, "positions": [str], "source_indices": [[int], [int]]}
    ],
    "source_quality": [
      {"index": int, "domain": str, "recency": str, "relevance_score": float, "rating": "high|medium|low"}
    ]
  }
  Emit: {"type": "research_phase", "phase": "synthesizing", "detail": "Cross-referencing N sources"}

STEP 5 — REPORT FORMATTER
  Convert structured JSON → markdown report with streaming:
  Sections:
    ## Executive Summary
    ## Key Findings  (each finding gets inline [n] citation numbers)
    ## Conflicting Information  (only if present)
    ## Source Quality & Bibliography  (table: domain, rating, recency, relevance)
  Stream as `token` SSE events during formatting.
  Emit: {"type": "research_phase", "phase": "formatting"}
  Final emit:
    {"type": "citations", "citations": [{index, title, url, domain, rating, accessed_at}]}
    {"type": "done"}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 7 — DEFAULT RAG PATH (no slash command)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

When no `intent_override` is present, use the existing RAG pipeline.
This must be the leanest, fastest path — zero intent classification overhead.

Flow:
  1. Retrieve top-K chunks from selected material_ids via ChromaDB + BGE reranker
  2. Build context window respecting MAX_CONTEXT_TOKENS
  3. Stream LLM response with inline citations
  4. Save message to DB with agent_meta: {intent: "RAG", chunks_used: N}

No agent loop, no web requests, no tool calls.
If user has no materials selected → return a clear message asking them to select materials.
If user has no materials uploaded at all → return onboarding message.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 8 — ARCHITECTURE CLEANUP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Delete `services/agent/intent.py`
- Delete `services/agent/planner.py` if it used LLM for intent-based planning
  (replace its planning role with planner_node in Section 5 LangGraph loop)
- Standardize all Prisma access to `from app.db.prisma_client import prisma` singleton
  Remove all `get_prisma()` call patterns
- Apply router prefix directly on each APIRouter instantiation:
    APIRouter(prefix="/chat", tags=["Chat"]) etc.
  Remove prefix-only-in-main.py pattern
- Consolidate duplicate DifficultyLevel enum into `models/shared_enums.py`
  Remove copies from flashcard.py and quiz.py
- Standardize all prompt placeholder syntax to {{DOUBLE_BRACES}} across all 12 prompt files
- Add `@@map` table names in Prisma schema to enforce consistent snake_case DB table names
- Ensure all new endpoints have `response_model` defined — no untyped returns
