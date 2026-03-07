# KeplerLab — Backend Complete Documentation

> **Framework:** FastAPI (Python 3.11) · **DB:** PostgreSQL + Prisma ORM · **Vector DB:** ChromaDB · **LLM:** Ollama / Google Gemini / NVIDIA / Custom OpenLM

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Technology Stack](#2-technology-stack)
3. [Project Structure](#3-project-structure)
4. [Application Entry Point (`main.py`)](#4-application-entry-point-mainpy)
5. [Configuration System](#5-configuration-system)
6. [Database Layer](#6-database-layer)
7. [Authentication System](#7-authentication-system)
8. [Background Worker](#8-background-worker)
9. [Material Ingestion Pipeline](#9-material-ingestion-pipeline)
10. [ChromaDB & Embeddings](#10-chromadb--embeddings)
11. [RAG Pipeline](#11-rag-pipeline)
12. [LLM Service](#12-llm-service)
13. [Agent Pipeline](#13-agent-pipeline)
14. [Code Execution Sandbox](#14-code-execution-sandbox)
15. [Deep Research Pipeline](#15-deep-research-pipeline)
16. [Chat Routing System](#16-chat-routing-system)
17. [Presentation (PPT) Service](#17-presentation-ppt-service)
18. [Podcast Service](#18-podcast-service)
19. [Flashcard & Quiz Services](#19-flashcard--quiz-services)
20. [Mind Map Service](#20-mind-map-service)
21. [WebSocket System](#21-websocket-system)
22. [Routes Reference](#22-routes-reference)
23. [Middleware Stack](#23-middleware-stack)
24. [Complete Request Flow Diagrams](#24-complete-request-flow-diagrams)
25. [Prisma Schema Reference](#25-prisma-schema-reference)

---

## 1. Architecture Overview

KeplerLab backend is an **AI-powered study assistant API** built on FastAPI. It provides:

- **Document ingestion** — Upload files (PDF, DOCX, PPTX, XLSX, CSV, audio/video, URLs, raw text)  
  → OCR → text extraction → chunking → embedding → ChromaDB storage
- **RAG Chat** — Semantic search over user documents → LLM streaming response with citations
- **Agentic AI** — Multi-step agent loop with tool calls (RAG, Python sandbox, web search)
- **Content Generation** — Flashcards, quizzes, HTML presentations, podcasts (TTS), mind maps, explainer videos
- **Real-time updates** — WebSocket for material processing status, SSE for streaming LLM responses
- **Auth** — JWT access tokens (15 min) + HttpOnly refresh tokens (7 days) with family-based rotation

```
┌─────────────────────────────────────────────────────────────┐
│                          FastAPI App                        │
│                                                             │
│  Auth ─► Notebooks ─► Materials ─► Chat ─► Agent ─► PPT    │
│          Flashcard     Quiz         Mindmap  Podcast         │
├──────────┬──────────┬──────────┬──────────┬────────────────-┤
│ Postgres │ ChromaDB │  LLM     │ Sandbox  │  WebSocket      │
│ (Prisma) │ (BGE-m3) │ Provider │ (Python) │  Manager        │
└──────────┴──────────┴──────────┴──────────┴─────────────────┘
```

---

## 2. Technology Stack

| Component | Library / Version |
|-----------|-------------------|
| Web Framework | `fastapi==0.115.6` |
| ASGI Server | `uvicorn[standard]==0.30.6` |
| ORM | `prisma==0.15.0` (async) |
| Database | PostgreSQL |
| Vector Store | `chromadb>=0.5.11,<0.6.0` |
| Embeddings | `sentence-transformers==3.1.1` (BAAI/bge-m3, 1024-dim) |
| Reranker | BAAI/bge-reranker-large |
| LLM Integration | LangChain (Google Gemini, NVIDIA, Ollama, Custom) |
| Agent Framework | LangGraph (for structured tasks) |
| OCR | `pytesseract`, `easyocr` |
| Audio Transcription | `openai-whisper` |
| TTS | `edge-tts` |
| PDF Processing | `pypdf`, `pymupdf`, `pdfplumber`, `pdf2image` |
| Presentation Screenshots | LibreOffice headless + `poppler` |
| Security | `python-jose`, `passlib[bcrypt]` |
| Validation | `pydantic v2`, `pydantic-settings` |
| Caching | `fastapi-cache2` |

---

## 3. Project Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app, lifespan, middleware
│   ├── core/
│   │   ├── config.py            # Pydantic BaseSettings — all env vars
│   │   └── utils.py             # Shared helpers (sanitize_null_bytes, etc.)
│   ├── db/
│   │   ├── chroma.py            # ChromaDB singleton + bootstrap
│   │   └── prisma_client.py     # Prisma async client singleton
│   ├── models/
│   │   ├── mindmap_schemas.py   # MindMap Pydantic schemas
│   │   ├── model_schemas.py     # LLM model path helpers
│   │   └── shared_enums.py      # IntentOverride, DifficultyLevel enums
│   ├── prompts/                 # All LLM prompt template .txt files
│   ├── routes/                  # FastAPI routers (one file per feature)
│   └── services/
│       ├── agent/               # Multi-step agent pipeline
│       ├── auth/                # JWT + bcrypt auth
│       ├── chat/                # Chat session service
│       ├── code_execution/      # Python sandbox + security scanner
│       ├── explainer/           # Explainer video service
│       ├── flashcard/           # Flashcard generator
│       ├── llm_service/         # LLM factory + structured invoker
│       ├── mindmap/             # Mind map generator
│       ├── podcast/             # Script gen + TTS + session manager
│       ├── ppt/                 # Presentation HTML generator
│       ├── quiz/                # Quiz generator
│       ├── rag/                 # Retrieval pipeline
│       ├── research/            # Deep web research pipeline
│       ├── stream/              # SSE stream helpers
│       ├── text_processing/     # File/URL/YouTube text extraction
│       ├── audit_logger.py      # API usage logging
│       ├── gpu_manager.py       # GPU memory management
│       ├── job_service.py       # Background job CRUD
│       ├── material_service.py  # Material lifecycle (ingest, chunk, embed)
│       ├── model_manager.py     # Hugging Face model download manager
│       ├── notebook_service.py  # Notebook CRUD
│       ├── notebook_name_generator.py
│       ├── performance_logger.py # Request timing middleware
│       ├── rate_limiter.py      # Rate limit middleware (currently disabled)
│       ├── storage_service.py   # File-system text storage (material_text/)
│       ├── token_counter.py     # Token counting + usage tracking
│       ├── worker.py            # Background job processor (asyncio.Task)
│       └── ws_manager.py        # WebSocket connection manager
├── cli/                         # CLI tools (backup, reindex, export, etc.)
├── data/
│   ├── chroma/                  # ChromaDB persistent storage
│   ├── material_text/           # Full extracted text files per material
│   ├── models/                  # Downloaded embedding/reranker models
│   ├── output/                  # Generated content (podcasts, presentations)
│   ├── uploads/                 # Raw uploaded files
│   └── workspaces/              # Agent sandbox working dirs
├── logs/                        # Rotating log files
├── output/                      # Alias for generated output
├── prisma/
│   └── schema.prisma            # PostgreSQL schema definition
└── requirements.txt
```

---

## 4. Application Entry Point (`main.py`)

The FastAPI app is configured with an **async lifespan context manager** that runs startup/shutdown logic.

### Startup Sequence (in order)

```
1. connect_db()                   — Connect Prisma/PostgreSQL
2. warm_up_embeddings()           — Preload BAAI/bge-m3 model (run_in_executor)
3. get_reranker()                 — Preload BAAI/bge-reranker-large (run_in_executor)
4. asyncio.create_task(job_processor()) — Start background document worker
5. ensure_packages()              — Install sandbox Python packages
6. Cleanup stale /tmp/kepler_sandbox_* dirs from previous crashes
7. os.makedirs() for output directories
8. cleanup_expired_tokens()       — Purge stale refresh tokens from DB
```

### Shutdown Sequence

```
1. graceful_shutdown()  — Signal worker to stop accepting new jobs
2. _job_processor_task.cancel()  — Cancel background task
3. asyncio.wait_for(..., timeout=30s) — Wait for in-flight jobs to finish
4. disconnect_db()      — Close Prisma connection
```

### Middleware Stack (order of execution)

```
1. performance_monitoring_middleware  — Logs request timing
2. rate_limit_middleware              — Currently a pass-through (disabled)
3. log_requests                       — Logs method, path, status, duration, X-Request-ID
4. CORSMiddleware                     — Allow CORS_ORIGINS (configurable)
5. TrustedHostMiddleware              — Production only: validates Host header
```

### Registered Routers

| Prefix | Module | Description |
|--------|--------|-------------|
| `/auth` | `routes/auth.py` | Signup, login, refresh, logout |
| `/notebook` | `routes/notebook.py` | Notebook CRUD |
| `/upload` | `routes/upload.py` | File/URL/text upload |
| `/materials` | `routes/materials.py` | Material listing, deletion, text view |
| `/flashcard` | `routes/flashcard.py` | Flashcard generation |
| `/quiz` | `routes/quiz.py` | Quiz generation |
| `/chat` | `routes/chat.py` | Chat with RAG / agent / web |
| `/models` | `routes/models.py` | LLM model management |
| `/jobs` | `routes/jobs.py` | Background job status polling |
| `/ppt` | `routes/ppt.py` | Presentation generation |
| `/mindmap` | `routes/mindmap.py` | Mind map generation |
| `/health` | `routes/health.py` | Health check |
| `/ws` | `routes/websocket_router.py` | WebSocket endpoints |
| `/search` | `routes/search.py` | Web search proxy |
| `/proxy` | `routes/proxy.py` | Generic HTTP proxy |
| `/explainer` | `routes/explainer.py` | Explainer video generation |
| `/podcast` | `routes/podcast_live.py` | Podcast session API |
| `/agent` | `routes/agent.py` | Agent execute, code execute, files |

---

## 5. Configuration System

**File:** `app/core/config.py`

All settings use **Pydantic BaseSettings** — automatically loaded from environment / `.env` file.

### Key Settings Categories

#### Database
```python
DATABASE_URL = ""               # PostgreSQL connection string (REQUIRED)
CHROMA_DIR = "./data/chroma"    # ChromaDB persistence directory
```

#### LLM Provider
```python
LLM_PROVIDER = "OLLAMA"         # OLLAMA | GOOGLE | NVIDIA | MYOPENLM
OLLAMA_MODEL = "llama3"
GOOGLE_MODEL = "models/gemini-2.5-flash"
GOOGLE_API_KEY = ""
NVIDIA_MODEL = "qwen/qwen3.5-397b-a17b"
NVIDIA_API_KEY = ""
```

#### LLM Generation Control
```python
LLM_TEMPERATURE_STRUCTURED = 0.1   # JSON/schema outputs
LLM_TEMPERATURE_CHAT = 0.2         # Conversational responses
LLM_TEMPERATURE_CREATIVE = 0.7     # Creative content
LLM_TEMPERATURE_CODE = 0.1         # Code generation
LLM_MAX_TOKENS = 4000
LLM_MAX_TOKENS_CHAT = 3000
```

#### Embeddings + Retrieval
```python
EMBEDDING_MODEL = "BAAI/bge-m3"
EMBEDDING_DIMENSION = 1024
RERANKER_MODEL = "BAAI/bge-reranker-large"
USE_RERANKER = True
INITIAL_VECTOR_K = 10     # Candidates from ChromaDB
MMR_K = 8                 # After MMR diversity filtering
FINAL_K = 10              # Final results after reranking
MAX_CONTEXT_TOKENS = 6000
```

#### JWT Authentication
```python
JWT_SECRET_KEY = ""                    # REQUIRED — 64-byte random key
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7
COOKIE_NAME = "refresh_token"
COOKIE_SECURE = False                  # Auto-set True in production
COOKIE_SAMESITE = "lax"
```

#### CORS
```python
CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000"]
```

### Path Resolution
All relative paths (`CHROMA_DIR`, `UPLOAD_DIR`, `MODELS_DIR`, etc.) are resolved to absolute paths against `_PROJECT_ROOT` at startup via `_resolve_paths_and_cross_validate`.

---

## 6. Database Layer

### Prisma Client (`db/prisma_client.py`)
Async Prisma client singleton. Connected/disconnected in the lifespan.

```python
from app.db.prisma_client import prisma
# Usage anywhere:
user = await prisma.user.find_unique(where={"email": email})
```

### PostgreSQL Schema (`prisma/schema.prisma`)

#### Core Models

| Model | Key Fields | Relations |
|-------|-----------|-----------|
| `User` | id (UUID), email, username, hashedPassword, isActive, role (USER/ADMIN) | Notebooks, Materials, ChatSessions, ChatMessages, GeneratedContent, RefreshTokens, BackgroundJobs, Artifacts |
| `Notebook` | id, userId, name, description | Owner (User), Materials, ChatSessions, ChatMessages, GeneratedContent, AgentLogs |
| `Material` | id, userId, notebookId, filename, title, originalText (summary only), status, chunkCount, sourceType, metadata | Owner, Notebook, GeneratedContent |
| `ChatSession` | id, notebookId, userId, title | Notebook, User, ChatMessages, Artifacts |
| `ChatMessage` | id, notebookId, userId, chatSessionId, role, content, agentMeta (JSON) | ResponseBlocks, Artifacts |
| `GeneratedContent` | id, notebookId, contentType, data (JSON), title | ExplainerVideos, MaterialJoins |
| `RefreshToken` | id, userId, tokenHash, family, used, expiresAt | User |
| `BackgroundJob` | id, userId, jobType, status, result (JSON), error | User |
| `Artifact` | id, userId, notebookId, sessionId, messageId, fileId, mimeType, tokenExpiry | User |

#### Enums
```
UserRole:       USER | ADMIN
MaterialStatus: pending | processing | ocr_running | transcribing | embedding | completed | failed
JobStatus:      pending | processing | ocr_running | transcribing | embedding | completed | failed
VideoStatus:    pending | processing | completed | failed
ExportStatus:   pending | processing | completed | failed
```

#### Additional Models
- `ResponseBlock` — Paragraph-level AI response blocks with citations
- `AgentExecutionLog` — Agent intent, tools used, tokens, elapsed time
- `CodeExecutionSession` — Python sandbox execution history
- `ResearchSession` — Deep research session history
- `PodcastSession + PodcastSessionMaterial` — Podcast session with linked materials
- `ExplainerVideo` — Video generation status + script + audio + chapters
- `UserTokenUsage` — Daily token consumption per user
- `ApiUsageLog` — Per-request latency, token counts, model used

---

## 7. Authentication System

**Files:** `app/services/auth/service.py`, `app/services/auth/security.py`, `app/routes/auth.py`

### Token Architecture

```
                                    ┌─────────────────────────────┐
Browser → POST /auth/login          │  Returns:                   │
                                    │  - access_token (bearer, 15m)│
                                    │  - refresh_token (HttpOnly   │
                                    │    cookie, 7 days)           │
                                    └─────────────────────────────┘

Browser → POST /api/route           Authorization: Bearer <access_token>
          ↓ 401                       → POST /auth/refresh (cookie sent auto)
          ↓ new access_token          → retry original request

Browser → POST /auth/refresh        Cookie: refresh_token=<token>
                                    Returns: { access_token }
                                    Rotates refresh token in DB
```

### Security Features

1. **Password Validation** — min 8 chars, uppercase + lowercase + digit required
2. **Bcrypt Hashing** — `passlib[bcrypt]` via `hash_password()` / `verify_password()`
3. **JWT Signing** — `python-jose` with HS256, separate types: `"access"`, `"refresh"`, `"file"`
4. **Refresh Token Rotation** — Each refresh issues a new token; old token marked `used=True`
5. **Token Family Theft Detection** — If a `used` token is replayed, ALL tokens in that family are revoked
6. **Token Hashing** — Refresh tokens stored as SHA-256 hashes, never plaintext
7. **HttpOnly Cookie** — Refresh token in `HttpOnly; Secure; SameSite=lax` cookie (inaccessible to JS)
8. **Startup Token Cleanup** — Expired refresh tokens purged on every server start
9. **Soft Delete Support** — `deleted_at` field on User model

### Auth Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/signup` | Register user, validate password rules |
| POST | `/auth/login` | Authenticate, issue access + refresh tokens |
| POST | `/auth/refresh` | Rotate refresh token, issue new access token |
| POST | `/auth/logout` | Revoke all user tokens |
| GET | `/auth/me` | Get current user info |

### `get_current_user` Dependency
Used by all protected routes via `Depends(get_current_user)`:
1. Extract Bearer token from `Authorization` header
2. Decode JWT → check type == "access"
3. Load user from DB by `sub` (user_id)
4. Check `user.isActive == True`
5. Return user object

---

## 8. Background Worker

**File:** `app/services/worker.py`

A single `asyncio.Task` created at startup that continuously processes document ingestion jobs.

### Architecture

```
[Upload Route]
   ↓ creates BackgroundJob(jobType="material_processing", status="pending")
   ↓ job_queue.notify()  ← wakes worker immediately

[job_processor() — running as asyncio.Task]
   ↓ fetch_next_pending_job() — SELECT ... FOR UPDATE SKIP LOCKED (atomic claim)
   ↓ up to MAX_CONCURRENT_JOBS=5 jobs run concurrently as asyncio.Tasks
   ↓ _process_job(job) → process_material_by_id() / process_url_material_by_id()
   ↓ Update job status: processing → embedding → completed / failed
```

### Concurrency Model
- **Event-driven** via `_JobQueue` — worker wakes immediately when job is created
- **Falls back to polling** every 2 seconds if no notification received
- At capacity: waits for `asyncio.FIRST_COMPLETED` before picking next job
- Maximum 5 concurrent document processing jobs

### Stuck Job Recovery
On startup, jobs stuck in `processing` longer than 30 minutes are reset to `pending` via raw SQL UPDATE.

### Graceful Shutdown
1. Sets `_shutdown_event` to stop accepting new jobs
2. Waits up to 30 seconds for in-flight tasks to complete
3. Cancels remaining tasks

---

## 9. Material Ingestion Pipeline

**File:** `app/services/material_service.py`

### Ingestion Paths

#### 1. File Upload (`process_material_by_id`)
```
pending → processing
   ↓ text_processing/extractor.py
   ↓ Selects extractor by MIME/extension:
   │  • PDF:   PyMuPDF + OCR fallback (pytesseract / easyocr)
   │  • DOCX:  python-docx
   │  • PPTX:  python-pptx (text extraction)
   │  • XLSX/CSV: pandas → full data + structured summary chunk
   │  • MP3/MP4/WAV: Whisper transcription (status → transcribing)
   │  • Image: OCR (status → ocr_running)
   ↓ chunk_text() — LangChain RecursiveCharacterTextSplitter
   ↓ embed_and_store() → ChromaDB
   ↓ save_material_text() → data/material_text/{material_id}.txt
   ↓ DB: status=completed, chunkCount=N, originalText=summary[:1000]
```

#### 2. URL Ingestion (`process_url_material_by_id`)
```
   ↓ Detect URL type:
   │  • YouTube URL → YouTubeService (transcript API or Whisper)
   │  • Web URL → WebScrapingService (trafilatura / BeautifulSoup)
   ↓ Same chunking + embedding pipeline
```

#### 3. Text Upload (`process_text_material_by_id`)
```
   ↓ Direct text → chunk → embed → store
```

### Storage Architecture
- **Full text** → `data/material_text/{material_id}.txt` (file system)
- **Database** → only `originalText` (first 1000 chars as summary), `chunkCount`, metadata
- **ChromaDB** → text chunks with metadata (user_id, notebook_id, material_id, filename)
- *Why files, not DB?* — Avoids PostgreSQL TOAST bloat for large documents; simple file I/O is faster

### Structured Data (CSV/Excel) Special Path
```python
# For CSV/Excel: two things happen:
# 1. Full df.to_string() saved to material_text/ (complete data for LLM)
# 2. Schema summary (column names + dtypes + shape + head(5)) stored in ChromaDB
#    tagged chunk_type="structured_summary"
# → When retrieved, secure_retriever swaps in the full dataset for the LLM context
```

### WebSocket Status Pushes
Every status transition emits `{"type": "material_update", "material_id": "...", "status": "..."}` via `ws_manager.send_to_user()`.

---

## 10. ChromaDB & Embeddings

**Files:** `app/db/chroma.py`, `app/services/rag/embedder.py`

### ChromaDB Setup

- Single collection: `"chapters"` — shared across all users
- Tenant isolation via `user_id` metadata filter on all queries
- Embedding function: `SentenceTransformerEmbeddingFunction("BAAI/bge-m3", device="cpu")`
- 1024-dimensional vectors (FP32)

### Bootstrap Sequence (`get_collection`)
```
1. Check version marker: <CHROMA_DIR>/.embedding_version
   → If EMBEDDING_VERSION changed or marker absent: physically wipe CHROMA_DIR
     (prevents stale HNSW dimension mismatch)
2. chromadb.PersistentClient(CHROMA_DIR)
3. get_or_create_collection("chapters", embedding_function=bge_m3_ef)
4. Dimension probe: embed ["warm-up"] string → upsert → delete
   → If dimension error: wipe + retry once → if still fails: RuntimeError
5. Write version marker on success
```

### `embed_and_store()`
- **UPSERT semantics** — idempotent re-processing
- **Batch size 200** — below ChromaDB's 256-item hard limit
- **3 retries** with 0.5s/1s/1.5s backoff for transient I/O errors
- **Dimension errors** → permanent, never retried; invalidates version marker

### Metadata per chunk
```python
{
  "user_id": str,          # REQUIRED for tenant isolation
  "material_id": str,
  "notebook_id": str,
  "filename": str,
  "source": "chapter",
  "embedding_version": str,
  "section_title": str,    # Optional
  "chunk_index": str,      # Optional
  "chunk_type": str,       # Optional: "structured_summary"
}
```

---

## 11. RAG Pipeline

**Files:** `app/services/rag/`

### Pipeline Overview
```
User Query
   ↓ secure_similarity_search_enhanced()
   ↓ [1] ChromaDB vector search (K=10) filtered by user_id + material_ids
   ↓ [2] MMR (Maximal Marginal Relevance) diversity filtering (K=8)
   ↓ [3] BGE-reranker-large re-scores candidates (if USE_RERANKER=True)
   ↓ [4] Sort by reranker score, take top FINAL_K=10
   ↓ context_builder.py — Assemble context within MAX_CONTEXT_TOKENS=6000
   ↓ context_formatter.py — Format with [SOURCE N] citation markers
   ↓ LLM streaming with citations
   ↓ citation_validator.py — Verify citations are valid
```

### `secure_retriever.py`  
All retrieval goes through `secure_similarity_search_enhanced()` which:
- **Enforces user_id filter** — prevents cross-tenant data leaks
- Optionally filters by specific `material_ids` (user-selected sources)
- Optionally filters by `notebook_id`
- Supports both MMR and standard similarity search modes

### RAG Chat Flow (`rag/pipeline.py`)
```
1. No materials selected → polite message asking to select materials
2. No relevant context found → clear "couldn't find" message
3. Build prompt: context + last 10 history messages + user query
4. Stream LLM tokens → SSE "token" events → accumulate full response
5. Validate citations
6. Emit SSE "meta" event: { intent, chunks_used, elapsed }
7. Emit SSE "done" event
```

### Reranker (`rag/reranker.py`)
- Model: `BAAI/bge-reranker-large` loaded once at startup
- Runs on CPU to avoid VRAM contention
- Cross-encoder model: directly scores (query, document) pairs

---

## 12. LLM Service

**File:** `app/services/llm_service/llm.py`

### Provider Factory Pattern
```python
from app.services.llm_service.llm import get_llm, get_llm_structured

llm = get_llm()                        # Chat temperature (0.2)
llm = get_llm(temperature=0.1)         # Custom temperature
llm = get_llm_structured()             # Lower temperature (0.1) for JSON
```

### Supported Providers

| Provider | Key | LangChain Class | Notes |
|----------|-----|-----------------|-------|
| Ollama | `OLLAMA` | `ChatOllama` | Local models, default |
| Google Gemini | `GOOGLE` | `ChatGoogleGenerativeAI` | `models/gemini-2.5-flash` |
| NVIDIA | `NVIDIA` | `ChatNVIDIA` | `qwen/qwen3.5-397b-a17b`, thinking disabled |
| Custom | `MYOPENLM` | `MyOpenLM` (custom) | Custom HTTP endpoint |

### LLM Instance Cache
- LRU cache (`_llm_cache`, max 16 entries) keyed by `(provider, temperature, top_p, max_tokens, **kwargs)`
- Prevents creating new client objects on every request

### `structured_invoker.py`
Used for formats requiring strict JSON output (flashcards, quiz, mindmap, PPT):
```python
result = invoke_structured(prompt, OutputSchema, max_retries=2)
# Uses LLM with temperature=STRUCTURED (0.1)
# Auto-parses and validates JSON with json_repair fallback
```

---

## 13. Agent Pipeline

**Files:** `app/services/agent/`

The agent is the most complex system — it orchestrates multi-step AI task execution.

### Execution Lifecycle
```
stream_agent(message, notebook_id, material_ids, session_id, user_id)
   │
   ├─ STEP 1: Intent Detection
   │    classify_task(message, has_materials)
   │    → TaskType: DATA_ANALYSIS | VISUALIZATION | ML_MODELING |
   │                STATISTICAL_ANALYSIS | TEXT_ANALYSIS | QA | etc.
   │    → Confidence score
   │    → Flags: requires_computation, requires_materials
   │    Emits SSE: "intent"
   │
   ├─ STEP 1.5: Dataset Profiling (for data tasks with materials)
   │    DatasetProfiler.profile_all()
   │    → For each CSV/Excel material: load → pandas profiling
   │    → Column names, dtypes, missing %, statistics
   │    → Stored in state.dataset_profile_context
   │    Emits SSE: "step" (phase: profiling)
   │
   ├─ STEP 2: Execution Planning
   │    generate_execution_plan(message, classification, profiles)
   │    → LLM generates ordered steps with tool assignments:
   │       { steps: [{tool, description, inputs}] }
   │    Emits SSE: "agent_start" (plan)
   │
   ├─ STEP 3: Tool Execution Loop (max MAX_ITERATIONS=10)
   │    For each plan step:
   │      ExecutionEngine.execute_step(step_index, tool, description, inputs)
   │      ├─ rag_tool       → ChromaDB retrieval
   │      ├─ python_tool    → Code gen → security scan → sandbox execution
   │      │                   Auto-repair loop (max 3 attempts)
   │      │                   On-demand package install (approved list)
   │      ├─ web_search_tool → External search service (DuckDuckGo)
   │      └─ research_tool  → Deep iterative web research
   │      Emits SSE: "step", "code_generated", "tool_result"
   │
   ├─ STEP 4: Artifact Detection
   │    ArtifactDetector.detect_artifacts(work_dir)
   │    → Scan output files: .png/.svg/.html/.csv/.json/.pkl
   │    → Register in DB: Artifact table with short-lived token (24h)
   │    Emits SSE: "artifact" per detected file
   │
   ├─ STEP 5: Result Validation
   │    ResultValidator.validate(state)
   │    → Check step success rates, artifact counts
   │    → Determine overall execution quality
   │
   ├─ STEP 6: Response Synthesis
   │    SummaryGenerator.generate(state)
   │    → LLM synthesizes a final narrative from all step results
   │    Emits SSE: "summary", "token" (streaming)
   │
   └─ STEP 7: Persistence
        → Save AgentExecutionLog to DB
        → Save ChatMessage with agentMeta JSON
        Emits SSE: "done"
```

### Tool Registry
```python
TOOL_REGISTRY = {
    "rag_tool":        rag_tool,
    "python_tool":     python_tool,
    "web_search_tool": web_search_tool,
    "research_tool":   research_tool,
}
```

### AgentExecutionState
Tracks full execution state:
- `phase: ExecutionPhase` — PLANNING | EXECUTING | VALIDATING | COMPLETE | FAILED
- `steps: List[StepState]` — each step's status, timing, output
- `artifacts: List[dict]` — detected output files
- `datasets: List[DatasetMetadata]`
- `generated_code: Dict[int, str]` — code per step index
- `dataset_profile_context: str` — pre-computed column/type info
- `detected_intent, intent_confidence`

### Security Sandboxing for Python Execution
Always applied before running any code:
1. `validate_code()` — AST-based scanner for dangerous imports/syscalls
2. `sanitize_code()` — Strips known dangerous patterns
3. Code runs in isolated subprocess with `cwd=work_dir` and `MPLBACKEND=Agg`
4. Hard timeout (`CODE_EXECUTION_TIMEOUT=15s`, extendable to 120s via agent route)
5. Only approved packages can be installed on-demand (`APPROVED_ON_DEMAND` whitelist)

---

## 14. Code Execution Sandbox

**Files:** `app/services/code_execution/`

### `sandbox.py` — Subprocess Execution
```python
result = await run_in_sandbox(
    code,
    work_dir="/tmp/kepler_agent_xyz",
    timeout=30,
    on_stdout_line=callback,  # Optional line-by-line streaming
)
# Returns ExecutionResult:
#   stdout, stderr, exit_code, timed_out, elapsed_seconds
#   chart_base64 (if __CHART__: marker detected in stdout)
#   output_files (list of produced files)
```

- Runs code as a subprocess using the same Python interpreter (`sys.executable`)
- Streams stdout/stderr asynchronously via `asyncio.subprocess.PIPE`
- Detects chart output via `__CHART__:<base64>` stdout marker
- Limits stdout to 16 MB to prevent memory exhaustion
- Kills process on timeout with `proc.kill()`

### `security.py` — Code Scanner
AST-based static analysis before any execution:
- Blocks dangerous imports: `os.system`, `subprocess`, `ctypes`, `socket`, `pickle` (unsafe usage)
- Blocks file writes outside work_dir
- Blocks shell command injection patterns
- `sanitize_code()` — removes known injection vectors

### `sandbox_env.py` — Package Management
Pre-installed packages in sandbox environment. Approved on-demand packages:
```python
APPROVED_ON_DEMAND = {
    "seaborn": "0.13.2",
    "wordcloud": "1.9.3",
    "missingno": "0.5.2",
    "folium": "0.15.1",
    "altair": "5.2.0",
    "pyvis": "0.3.2",
}
```

---

## 15. Deep Research Pipeline

**File:** `app/services/research/pipeline.py`

Triggered by `intent_override = "WEB_RESEARCH"` (user types `/research` command).

### Multi-Pass Research Flow
```
1. Decompose Query
   → LLM breaks query into 3-5 sub-questions
   → SSE: "research_start"

2. For each of 3 iterations:
   a. Web Search: _web_search() → external POST /api/search (DuckDuckGo via kepler-sandbox)
   b. URL Fetching: _fetch_url() → external POST /api/scrape (max 3 URLs/subq, 15 total)
   c. Partial Synthesis: LLM processes gathered content → partial answer + gaps
   d. Gap Analysis: LLM generates follow-up queries for next iteration
   → SSE: "research_phase" (iteration N/3, phase: searching → fetching → synthesizing)
   → SSE: "research_source" per URL

3. Final Synthesis
   → LLM generates structured markdown report with inline [1][2][3] citations
   → Streams as "token" SSE events
   → SSE: "citations" (list of all sources)
   → SSE: "done"
```

### External Dependencies
Two calls go to the `kepler-sandbox` service (default: `http://localhost:8002`):
- `POST /api/search` — DuckDuckGo web search
- `POST /api/scrape` — URL content scraping

---

## 16. Chat Routing System

**File:** `app/routes/chat.py`

### Routing Logic (Strict Frontend-Driven — No LLM Classification)

The frontend sends an explicit `intent_override` field based on the slash command used:

```
intent_override == "AGENT"          → _route_agent()         (full agent pipeline)
intent_override == "WEB_RESEARCH"   → _route_web_research()  (deep research pipeline)
intent_override == "CODE_EXECUTION" → _route_code_execution() (Python sandbox directly)
intent_override == "WEB_SEARCH"     → _route_web_search()    (quick web search + LLM)
None (no override)                  → _route_rag()           (default RAG pipeline)
```

### Chat Request Schema
```python
class ChatRequest(BaseModel):
    material_ids: Optional[List[str]] = None
    message: str                               # 1-50000 chars
    notebook_id: str
    session_id: Optional[str] = None
    stream: Optional[bool] = True
    intent_override: Optional[IntentOverride] = None
```

### `_route_rag` (Default Path)
```
1. filter_completed_material_ids() — skip unfinished materials
2. create/auto-title chat session
3. stream_rag() — SSE stream
4. Accumulate tokens → _persist_and_finalize()
5. Save user + assistant messages to DB with ResponseBlocks
6. Emit SSE "blocks" event with parsed blocks
```

### `_route_agent`
```
1. stream_agent() — full agent pipeline SSE stream
2. Forward all SSE events to client
3. On "done" event: save final ChatMessage with agentMeta JSON
```

### `_route_web_search` (Quick Search)
```
1. POST to kepler-sandbox /api/search
2. Fetch top 3 URL contents
3. LLM synthesizes answer from web content
4. Streams tokens
```

### `_route_code_execution`
```
1. LLM generates Python code from message
2. Security scan + sanitize
3. run_in_sandbox() with 30s timeout
4. Return stdout, stderr, exit_code, chart (if any)
```

### Session Management
- Sessions auto-created if `session_id` not provided
- Auto-title: first 30 chars of message
- Sessions not re-fetched unless notebook changes

---

## 17. Presentation (PPT) Service

**File:** `app/services/ppt/generator.py`

### Generation Flow
```
generate_presentation(material_text, user_id, max_slides=10, theme?, instructions?)
   │
   ├─ 1. Build prompt: get_ppt_prompt(text, slide_count, theme, instructions)
   │     Template: prompts/ppt_prompt.txt
   │
   ├─ 2. invoke_structured(prompt, PresentationHTMLOutput, retries=2)
   │     → LLM returns JSON: { title, theme, slide_count, html }
   │     → html is a FULL standalone HTML document (<!DOCTYPE html>…)
   │     → Validated by PresentationHTMLOutput Pydantic schema
   │
   ├─ 3. _post_process_html(html)
   │     → Ensure DOCTYPE
   │     → Fix/inject viewport meta tag (width=1920)
   │     → Inject safety CSS: 1920×1080 fixed slide dimensions
   │     → No JavaScript execution
   │
   ├─ 4. extract_slides(html)  — slide_extractor.py
   │     → BeautifulSoup parses HTML for .slide elements
   │     → Each slide extracted as standalone HTML document
   │     → Returns [{slide_number, slide_id, html}]
   │
   └─ Returns: { presentation_id, title, slide_count, theme, html, slides }
       slides = list of standalone HTML docs, rendered in iframes at 1920×1080
```

### Async Presentation via Background Jobs
Route `/presentation/async` creates a BackgroundJob, returns `job_id` immediately.  
Frontend polls `GET /jobs/{job_id}` every 3 seconds until `status=completed`.

### Explainer Video (`services/explainer/`)
Builds on presentations:
1. PPT generation → video narration script via LLM
2. Per-slide TTS audio via `edge-tts`
3. LibreOffice → PNG screenshots of slides
4. `ffmpeg` combines images + audio → MP4

---

## 18. Podcast Service

**Files:** `app/services/podcast/`

### Podcast Architecture

#### Session Lifecycle
```
POST /podcast/session          → Create session (mode, language, voices, material_ids)
POST /podcast/session/{id}/start → Start generation pipeline
  ├─ script_generator.py        → Generate 2-persona dialogue script
  │   ├─ Multi-angle RAG (2-3 parallel queries per mode)
  │   ├─ LLM generates JSON: { segments: [{speaker, text}], chapters, title }
  │   └─ Modes: overview | deep-dive | debate | q-and-a | full | topic
  └─ tts_service.py             → Text-to-Speech per segment
      ├─ edge-tts voices (configurable per language/gender)
      ├─ Streams audio files as generated
      └─ Progress pushed via WebSocket events

GET /podcast/session/{id}/segment/{n}/audio → FileResponse (MP3)

POST /podcast/session/{id}/question → Q&A mid-playback
  ├─ qa_service.py: RAG search for answer
  ├─ LLM generates spoken answer
  └─ TTS converts to audio

POST /podcast/session/{id}/export  → Export as PDF summary or JSON transcript
```

#### Voice System (`voice_map.py`)
- `VOICE_MAP[language][gender]` → edge-tts voice name
- Supports: English, Spanish, French, German, Hindi, Chinese, Japanese, Korean, Arabic, Portuguese, Russian, Italian
- Preview generation endpoint

#### Q&A Flow (`qa_service.py`)
```
User pauses at segment N → types question
→ RAG search for answer context
→ LLM generates spoken answer in podcast style
→ edge-tts converts to audio
→ Returns audio URL
→ satisfaction_detector.py: evaluates if answer was complete
```

#### WebSocket Events (pushed to user)
```json
{"type": "podcast_generating", "session_id": "...", "progress": 45}
{"type": "podcast_segment_ready", "session_id": "...", "segment": 5}
{"type": "podcast_completed", "session_id": "..."}
{"type": "podcast_failed", "session_id": "...", "error": "..."}
```

---

## 19. Flashcard & Quiz Services

**Files:** `app/services/flashcard/generator.py`, `app/services/quiz/generator.py`

### Flashcard Generation
```
POST /flashcard
  → Load material text (require_material_text / require_materials_text)
  → Optional topic filter prepended to text
  → invoke_structured(prompt, FlashcardsOutput)
  → Prompt: prompts/flashcard_prompt.txt
  → Returns: { flashcards: [{front, back, difficulty}] }
  
Parameters: card_count (1-150), difficulty (easy/medium/hard), topic, additional_instructions
```

### Quiz Generation
```
POST /quiz
  → Same text loading pipeline
  → invoke_structured(prompt, QuizOutput)
  → Prompt: prompts/... (quiz-specific)
  → Returns: { questions: [{question, options: [A/B/C/D], correct_answer, explanation}] }
  
Parameters: mcq_count, difficulty, topic, additional_instructions
```

Both services use `loop.run_in_executor(None, lambda: invoke_structured(...))` to avoid blocking the event loop on synchronous LLM calls.

---

## 20. Mind Map Service

**File:** `app/services/mindmap/`

```
POST /mindmap
  → Load material text
  → invoke_structured(prompt, MindMapOutput)
  → Prompt: prompts/mindmap_prompt.txt
  → Returns hierarchical node tree:
     { nodes: [{id, label, children: [...]}] }
  
MindMap chat bridge:
  → User can click any mind map node → sends pre-filled query to chat
```

---

## 21. WebSocket System

**Files:** `app/services/ws_manager.py`, `app/routes/websocket_router.py`

### Connection Manager (`ConnectionManager`)

```python
ws_manager.connect_user(user_id, websocket)   # Register connection
ws_manager.disconnect_user(user_id, websocket) # Remove on close
await ws_manager.send_to_user(user_id, payload) # Push to all user tabs
await ws_manager.broadcast(payload)             # Push to all users
ws_manager.user_is_connected(user_id)          # Presence check
ws_manager.stats()                              # { user_connections, unique_users }
```

- `defaultdict(list)` — supports multiple tabs per user
- Max 10 connections per user (prevents DoS)
- Dead connections auto-pruned on failed send
- Thread-safe (CPython GIL + asyncio single-threaded)

### WebSocket Endpoint: `/ws/jobs/{user_id}`

**Authentication:** Two modes:
1. Query param: `?token=<jwt>` (legacy)
2. First-message auth: `{"type": "auth", "token": "<jwt>"}` within 10-second timeout

**Keepalive:** Server sends `{"type": "ping"}` every 30 seconds; client echoes `{"type": "pong"}`.

**Messages received by client:**
```json
{ "type": "connected", "channel": "jobs", "user_id": "..." }
{ "type": "material_update", "material_id": "...", "status": "embedding" }
{ "type": "podcast_generating", "session_id": "...", "progress": 45 }
{ "type": "ping" }
```

---

## 22. Routes Reference

### Auth Routes (`/auth`)
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/signup` | No | Register new user |
| POST | `/auth/login` | No | Email/password login, set refresh cookie |
| POST | `/auth/refresh` | Cookie | Rotate refresh token, get new access token |
| POST | `/auth/logout` | Bearer | Revoke all user tokens |
| GET | `/auth/me` | Bearer | Get current user profile |

### Notebook Routes (`/notebook`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/notebook` | Create notebook |
| GET | `/notebook/{id}` | Get single notebook |
| GET | `/notebook` | List user notebooks |
| PATCH | `/notebook/{id}` | Rename/update description |
| DELETE | `/notebook/{id}` | Delete notebook + cascade |

### Upload Routes (`/upload`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/upload` | Upload single file (202 Accepted) |
| POST | `/upload/batch` | Upload multiple files |
| POST | `/upload/url` | Submit URL for ingestion |
| POST | `/upload/text` | Submit raw text |
| GET | `/upload/supported-formats` | List accepted MIME types + max size |

### Materials Routes (`/materials`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/materials/{notebook_id}` | List materials in notebook |
| GET | `/materials/{id}/text` | Get full material text |
| PATCH | `/materials/{id}` | Update title |
| DELETE | `/materials/{id}` | Delete material + embeddings |
| POST | `/materials/{id}/move` | Move to different notebook |

### Chat Routes (`/chat`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/chat` | Stream chat response (SSE) |
| GET | `/chat/history/{notebook_id}` | Load message history |
| DELETE | `/chat/history/{notebook_id}` | Clear history |
| GET | `/chat/sessions/{notebook_id}` | List chat sessions |
| POST | `/chat/sessions` | Create session |
| DELETE | `/chat/sessions/{session_id}` | Delete session |
| POST | `/chat/block-followup` | Ask follow-up on specific response block |
| POST | `/chat/suggestions` | Autocomplete suggestions |

### Agent Routes (`/agent`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/agent/execute` | Full agent pipeline (SSE) |
| POST | `/agent/execute-code` | Run reviewed code in sandbox (SSE) |
| GET | `/agent/file/{artifact_id}` | Serve artifact file (token auth) |
| POST | `/agent/refresh-token` | Refresh artifact download token |
| POST | `/agent/research` | Research-only endpoint |

### Generation Routes
| Method | Path | Description |
|--------|------|-------------|
| POST | `/flashcard` | Generate flashcards |
| POST | `/quiz` | Generate quiz |
| POST | `/ppt` | Generate presentation (sync) |
| POST | `/presentation/async` | Generate presentation (async job) |
| POST | `/mindmap` | Generate mind map |
| POST | `/explainer/{ppt_id}/start` | Start explainer video |

### Podcast Routes (`/podcast`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/podcast/session` | Create session |
| GET | `/podcast/session/{id}` | Get session state |
| GET | `/podcast/sessions/{notebook_id}` | List sessions |
| PATCH | `/podcast/session/{id}` | Update title/tags/position |
| DELETE | `/podcast/session/{id}` | Delete session |
| POST | `/podcast/session/{id}/start` | Start generation |
| GET | `/podcast/session/{id}/segment/{n}/audio` | Stream segment audio |
| POST | `/podcast/session/{id}/question` | Submit Q&A |
| POST | `/podcast/session/{id}/bookmark` | Add bookmark |
| POST | `/podcast/session/{id}/annotation` | Add note |
| POST | `/podcast/session/{id}/export` | Export PDF/JSON |
| GET | `/podcast/voices/{language}` | Available voices |

### Other Routes
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/jobs/{job_id}` | Job status |
| POST | `/search/web` | Web search proxy |
| WS | `/ws/jobs/{user_id}` | Real-time job updates |

---

## 23. Middleware Stack

### Performance Logger (`performance_logger.py`)
- Logs every request: `method path status_code duration_ms [request_id]`
- Adds `X-Request-ID` header to all responses

### Rate Limiter (`rate_limiter.py`)
- Currently **DISABLED** — passes all requests through
- Designed for 3 bucket types: `upload`, `chat`, `generation`

### CORS Middleware
- `allow_origins = settings.CORS_ORIGINS` (default: localhost:3000, localhost:5173)
- `allow_credentials = True` (required for HttpOnly cookie)
- `allow_methods = ["*"]`, `allow_headers = ["*"]`

### TrustedHost Middleware
- Active only in `production` environment
- Validates `Host` header against allowed origins (prevents host-header injection)

---

## 24. Complete Request Flow Diagrams

### Upload + Process File
```
Browser
  │  POST /upload/batch  multipart/form-data
  │  Authorization: Bearer <access_token>
  ▼
FastAPI [upload.py]
  │  1. Stream file to /tmp/uuid_filename.ext (async chunked)
  │  2. validate_upload() → python-magic MIME check + size check
  │  3. Move to data/uploads/{uuid}/{filename}
  │  4. prisma.material.create(status=pending)
  │  5. create_job(userId, jobType="material_processing", result={material_id, ...})
  │  6. job_queue.notify()
  │  Returns: 202 { material_id, job_id }
  ▼
Background Worker [worker.py]
  │  fetch_next_pending_job() — SELECT ... FOR UPDATE SKIP LOCKED
  │  _process_job(job)
  │  process_material_by_id(material_id, user_id, notebook_id)
  │     status → processing
  │     extractor.extract_text() by MIME type
  │     status → [ocr_running | transcribing] (if needed)
  │     chunk_text(text) → chunks[]
  │     status → embedding
  │     embed_and_store(chunks, material_id, user_id)
  │     save_material_text(material_id, full_text)
  │     status → completed
  │     ws_manager.send_to_user(user_id, material_update event)
  ▼
Browser [WebSocket /ws/jobs/{user_id}]
  Receives: {"type":"material_update","material_id":"...","status":"completed"}
```

### Chat RAG Request
```
Browser
  │  POST /chat
  │  { message, notebook_id, material_ids: ["id1","id2"] }
  │  Authorization: Bearer <access_token>
  ▼
ChatRoute [chat.py]
  │  validate material ownership
  │  filter_completed_material_ids() — skip pending
  │  route → _route_rag()
  │  stream_rag() → StreamingResponse(media_type="text/event-stream")
  │
  │  [RAG Pipeline]
  │    secure_similarity_search_enhanced(query, material_ids, user_id)
  │      → ChromaDB.query(where={user_id, material_id ∈ material_ids})
  │      → MMR diversity filter
  │      → BGE reranker scoring
  │      → top 10 chunks
  │    build_context(chunks) → context string with [SOURCE N] markers
  │    get_chat_history() → last 10 messages
  │    get_chat_prompt(context, history, query)
  │    llm.astream(prompt) → token by token
  │
  │  Browser receives: SSE stream
  │  event: token
  │  data: {"content": "The "}
  │  event: token
  │  data: {"content": "answer "}
  │  ...
  │  event: meta
  │  data: {"intent":"RAG","chunks_used":5,"elapsed":2.3}
  │  event: done
  │  data: {"elapsed":2.3}
  │
  │  After stream complete:
  │    _persist_and_finalize() → save user + assistant messages
  │    → split response into ResponseBlocks
  │    → emit SSE "blocks" event
  ▼
Browser renders streamed response
```

### Podcast Generation
```
Browser
  POST /podcast/session
  → Script generation: multi-angle RAG + LLM → JSON dialogue
  → TTS: edge-tts per segment → MP3 files
  → WebSocket events: progress updates

Browser polls /podcast/session/{id} for phase
  → phase: "script_generated" | "tts_generating" | "completed"

Browser streams /podcast/session/{id}/segment/{n}/audio
  → FileResponse MP3
  → HTML5 Audio plays
```

---

## 25. Prisma Schema Reference

### Key Relationships

```
User
 ├── Notebooks (1:many)
 │     └── Materials (1:many, nullable notebook)
 │     └── ChatSessions (1:many)
 │     └── ChatMessages (1:many)
 │     └── GeneratedContent (1:many)
 │     └── AgentExecutionLogs (1:many)
 ├── RefreshTokens (1:many, rotation family)
 ├── BackgroundJobs (1:many)
 ├── PodcastSessions (1:many, via join table)
 ├── Artifacts (1:many)
 └── UserTokenUsage (1:many, per day)

ChatSession
 └── ChatMessages
       └── ResponseBlocks
       └── Artifacts

GeneratedContent (flashcard|quiz|presentation|mindmap)
 └── ExplainerVideos
 └── GeneratedContentMaterial (join table)

Material
 └── GeneratedContent (legacy direct ref)
 └── GeneratedContentMaterial (join table)
 └── PodcastSessionMaterial (join table)
```

### Material Status Lifecycle
```
pending
  → processing (worker claimed job)
  → ocr_running (PDF/image OCR in progress)
  → transcribing (audio/video Whisper in progress)
  → embedding (ChromaDB upsert in progress)
  → completed ✓
  → failed ✗ (error stored in material.error field)
```

### Important Indexes
- `Material`: `[userId]`, `[notebookId]`, `[sourceType]`
- `ChatMessage`: `[chatSessionId]`, `[notebookId]`, `[notebookId, createdAt]`
- `RefreshToken`: `[userId]`, `[family]`
- `AgentExecutionLog`: `[userId]`, `[notebookId]`
- `ApiUsageLog`: `[userId]`, `[endpoint]`, `[createdAt]`

---

> **Note:** All sensitive data (passwords, JWT keys, API keys) must be set via environment variables. Never hardcode credentials. The `JWT_SECRET_KEY` and `DATABASE_URL` are validated as non-empty on startup and will prevent the server from starting if missing.
