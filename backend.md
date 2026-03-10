# KeplerLab Backend — Complete Architecture & Feature Documentation

---

## Table of Contents

1. [Overview](#overview)
2. [Technology Stack](#technology-stack)
3. [Project Structure](#project-structure)
4. [Application Startup & Lifecycle](#application-startup--lifecycle)
5. [Configuration System](#configuration-system)
6. [Database Layer](#database-layer)  
   - [PostgreSQL / Prisma Schema](#postgresql--prisma-schema)
   - [ChromaDB Vector Store](#chromadb-vector-store)
7. [Middleware Stack](#middleware-stack)
8. [Authentication System](#authentication-system)
9. [LLM Service Layer](#llm-service-layer)
10. [RAG (Retrieval-Augmented Generation) Pipeline](#rag-pipeline)
11. [Text Processing Pipeline](#text-processing-pipeline)
12. [Background Job System](#background-job-system)
13. [WebSocket Real-Time Layer](#websocket-real-time-layer)
14. [Feature-by-Feature Flow](#feature-by-feature-flow)
    - [Upload & Material Processing](#upload--material-processing)
    - [Chat System (v2)](#chat-system-v2)
    - [Quiz Generation](#quiz-generation)
    - [Flashcard Generation](#flashcard-generation)
    - [Presentation (PPT) Generation](#presentation-ppt-generation)
    - [Mind Map Generation](#mind-map-generation)
    - [Podcast (Live) System](#podcast-live-system)
    - [Explainer Video System](#explainer-video-system)
    - [Code Execution System](#code-execution-system)
    - [Artifact Management](#artifact-management)
    - [Web Search & Research Pipeline](#web-search--research-pipeline)
    - [Notebook Management](#notebook-management)
    - [Search Endpoint](#search-endpoint)
    - [Proxy Endpoint](#proxy-endpoint)
15. [Rate Limiting](#rate-limiting)
16. [Performance Logging](#performance-logging)
17. [Security Architecture](#security-architecture)
18. [CLI Tools](#cli-tools)
19. [Output Directory Structure](#output-directory-structure)
20. [Environment Variables Reference](#environment-variables-reference)

---

## Overview

KeplerLab is an AI-powered study platform backend built with **FastAPI** (Python 3.11+). It provides a comprehensive REST + WebSocket API supporting:

- Multi-format document upload, text extraction & vector embedding
- Context-aware AI chat (RAG, Web Search, Code Execution, Deep Research)
- Automated generation of quizzes, flashcards, presentations, mind maps, podcasts, and explainer videos
- Secure multi-tenant user isolation at every level
- Background async job processing for long-running tasks
- Real-time progress updates via WebSockets

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Web Framework | FastAPI 0.115.6 |
| ASGI Server | Uvicorn with Standard extras |
| ORM / DB Client | Prisma (async) — `prisma-client-py` |
| Relational DB | PostgreSQL |
| Vector Store | ChromaDB (PersistentClient) |
| Embedding Model | `BAAI/bge-m3` (1024-dim, SentenceTransformers) |
| Reranker Model | `BAAI/bge-reranker-large` (CrossEncoder) |
| LLM Providers | Ollama / Google Gemini / NVIDIA NIM / Custom OpenLM |
| LLM Orchestration | LangChain, LangGraph |
| TTS | Edge-TTS (Microsoft) |
| OCR | Tesseract + EasyOCR |
| Audio Transcription | OpenAI Whisper |
| Web Scraping | BeautifulSoup4, Selenium, Trafilatura |
| YouTube | youtube-transcript-api, yt-dlp |
| PDF Extract | PyMuPDF, PDFPlumber, pypdf |
| Auth | JWT (python-jose), bcrypt (passlib) |
| Task Queue | Custom asyncio-based job processor |
| FFmpeg | Video composition for explainer videos |
| Code Execution | Subprocess sandbox (multi-language) |
| Pydantic | v2 (schemas, settings) |
| Python | 3.11 recommended |

---

## Project Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI app factory, middleware, router registration
│   ├── core/
│   │   ├── config.py            # Pydantic Settings (all env vars, LRU-cached)
│   │   ├── utils.py             # Helpers (sanitize_null_bytes, etc.)
│   │   └── web_search.py        # DuckDuckGo search wrapper
│   ├── db/
│   │   ├── chroma.py            # ChromaDB client factory, collection bootstrap
│   │   └── prisma_client.py     # Prisma async client init/teardown
│   ├── models/
│   │   ├── mindmap_schemas.py   # Pydantic schemas for mind map
│   │   ├── model_schemas.py     # Local model path helpers
│   │   └── shared_enums.py      # DifficultyLevel enum
│   ├── routes/                  # FastAPI routers (one per feature)
│   │   ├── auth.py
│   │   ├── notebook.py
│   │   ├── upload.py
│   │   ├── materials.py
│   │   ├── chat.py              # Re-exports from services/chat_v2/router.py
│   │   ├── quiz.py
│   │   ├── flashcard.py
│   │   ├── ppt.py
│   │   ├── mindmap.py
│   │   ├── podcast_live.py
│   │   ├── explainer.py
│   │   ├── code_execution.py
│   │   ├── artifacts.py
│   │   ├── search.py
│   │   ├── proxy.py
│   │   ├── jobs.py
│   │   ├── models.py
│   │   ├── health.py
│   │   ├── websocket_router.py
│   │   └── utils.py             # Shared route helpers
│   ├── services/
│   │   ├── auth/                # JWT auth, bcrypt, token rotation
│   │   ├── chat_v2/             # Chat orchestrator, router logic, streaming
│   │   ├── code_execution/      # Sandbox, security validator, env setup
│   │   ├── explainer/           # Video generation pipeline
│   │   ├── flashcard/           # Flashcard LLM generator
│   │   ├── llm_service/         # LLM provider factory, structured invoker
│   │   ├── mindmap/             # Mind map generator
│   │   ├── model_manager.py
│   │   ├── notebook_service.py
│   │   ├── notebook_name_generator.py
│   │   ├── performance_logger.py
│   │   ├── podcast/             # Script gen, TTS, session mgr, QA, export
│   │   ├── ppt/                 # PPT generator, screenshot, slide extractor
│   │   ├── quiz/                # Quiz generator
│   │   ├── rag/                 # Embedder, retriever, reranker, pipeline
│   │   ├── rate_limiter.py
│   │   ├── research/            # Deep research pipeline
│   │   ├── storage_service.py   # Material text file storage
│   │   ├── text_processing/     # Extractor, chunker, OCR, Whisper, web scrape
│   │   ├── tools/               # RAG tool, web search tool, Python tool, Research tool
│   │   ├── web_search/
│   │   ├── worker.py            # Background async job processor
│   │   ├── ws_manager.py        # WebSocket connection manager
│   │   ├── file_validator.py
│   │   ├── job_service.py
│   │   ├── material_service.py
│   │   └── rate_limiter.py
│   └── prompts/                 # .txt prompt templates loaded at runtime
├── cli/                         # CLI utilities (backup, reindex, export)
├── data/                        # Runtime data (uploads, chroma, models, artifacts)
├── logs/                        # Rotating log files
├── output/                      # Generated output (presentations, explainers, podcasts)
├── prisma/
│   └── schema.prisma            # Full DB schema (20+ models)
├── requirements.txt
└── .env                         # Environment variables (not committed)
```

---

## Application Startup & Lifecycle

The FastAPI application uses an **async context manager lifespan** (`@asynccontextmanager async def lifespan(app)`):

### Startup Phase (in order)
1. **Connect PostgreSQL** via Prisma async client (`await connect_db()`)
2. **Warm up embedding model** — loads `BAAI/bge-m3` into memory via `warm_up_embeddings()` (runs in thread pool to not block the event loop)
3. **Preload reranker model** — loads `BAAI/bge-reranker-large` CrossEncoder into memory
4. **Start background job processor** — creates an `asyncio.Task` running `job_processor()` indefinitely
5. **Ensure sandbox packages** — calls `ensure_packages()` to verify Python sandbox dependencies
6. **Clean up stale temp dirs** — removes any leftover `/tmp/kepler_sandbox_*` directories from previous crashes
7. **Ensure output directories** exist (`output/generated`, `output/presentations`, `output/explainers`, `output/podcast`, `data/artifacts`)
8. **Purge expired refresh tokens** from the database

### Shutdown Phase
1. Signal graceful shutdown to job processor
2. Wait up to `_SHUTDOWN_TIMEOUT = 30s` for in-flight jobs to complete
3. Cancel job processor task
4. Disconnect PostgreSQL

---

## Configuration System

All configuration is in `app/core/config.py` using **Pydantic Settings** (`BaseSettings`). It reads from a `.env` file and environment variables. A singleton is created via `@lru_cache(maxsize=1)`.

### Key Configuration Groups

#### Application
| Setting | Default | Description |
|---------|---------|-------------|
| `ENVIRONMENT` | `development` | `development` / `staging` / `production` |
| `DEBUG` | `False` | Enable debug mode |
| `CORS_ORIGINS` | `localhost:3000, 5173` | Allowed CORS origins |

#### Database
| Setting | Description |
|---------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (required) |
| `CHROMA_DIR` | Path to ChromaDB persistent storage |

#### File Handling
| Setting | Default | Description |
|---------|---------|-------------|
| `UPLOAD_DIR` | `./data/uploads` | Where uploaded files are stored |
| `MAX_UPLOAD_SIZE_MB` | `10240` | Maximum upload size in MB |
| `ARTIFACTS_DIR` | `data/artifacts` | Code execution output artifacts |
| `WORKSPACE_BASE_DIR` | `./data/workspaces` | Sandbox workspace dirs |

#### LLM Provider
| Setting | Default | Description |
|---------|---------|-------------|
| `LLM_PROVIDER` | `OLLAMA` | Active provider: `OLLAMA`, `GOOGLE`, `NVIDIA`, `MYOPENLM` |
| `OLLAMA_MODEL` | `llama3` | Ollama model name |
| `GOOGLE_MODEL` | `models/gemini-2.5-flash` | Google Gemini model |
| `GOOGLE_API_KEY` | `""` | Required for Google provider |
| `NVIDIA_MODEL` | `qwen/qwen3.5-397b-a17b` | NVIDIA NIM model |
| `NVIDIA_API_KEY` | `""` | Required for NVIDIA provider |
| `LLM_TIMEOUT` | `None` | Request timeout (seconds) |

#### LLM Temperature Presets
| Setting | Default | Used For |
|---------|---------|----------|
| `LLM_TEMPERATURE_STRUCTURED` | `0.1` | JSON/structured outputs |
| `LLM_TEMPERATURE_CHAT` | `0.2` | Chat responses |
| `LLM_TEMPERATURE_CREATIVE` | `0.7` | Podcast scripts, creative content |
| `LLM_TEMPERATURE_CODE` | `0.1` | Code generation |

#### Embedding & RAG
| Setting | Default | Description |
|---------|---------|-------------|
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | SentenceTransformer model name |
| `EMBEDDING_DIMENSION` | `1024` | Vector dimension |
| `RERANKER_MODEL` | `BAAI/bge-reranker-large` | CrossEncoder reranker |
| `USE_RERANKER` | `True` | Enable/disable reranking |
| `INITIAL_VECTOR_K` | `10` | Initial vector search result count |
| `MMR_K` | `8` | MMR (Maximal Marginal Relevance) result count |
| `FINAL_K` | `10` | Final context chunks to use |
| `MAX_CONTEXT_TOKENS` | `6000` | Max tokens in LLM context |
| `MIN_SIMILARITY_SCORE` | `0.3` | Minimum cosine similarity threshold |

#### JWT Auth
| Setting | Default | Description |
|---------|---------|-------------|
| `JWT_SECRET_KEY` | Required | Secret key for JWT signing |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |
| `COOKIE_SECURE` | `False` | Set to `True` in production |
| `COOKIE_SAMESITE` | `lax` | SameSite cookie policy |

#### Code Execution
| Setting | Default | Description |
|---------|---------|-------------|
| `MAX_CODE_REPAIR_ATTEMPTS` | `3` | Auto-repair retry count |
| `CODE_EXECUTION_TIMEOUT` | `15` | Sandbox execution timeout (seconds) |
| `APPROVED_ON_DEMAND` | dict | Packages that can be auto-installed: seaborn, wordcloud, missingno, folium, altair, pyvis |

---

## Database Layer

### PostgreSQL / Prisma Schema

The Prisma schema (`prisma/schema.prisma`) defines **20+ models**. Generator: `prisma-client-py` with async interface.

#### Core Models

**User**
- `id` (UUID), `email` (unique), `username`, `hashedPassword`, `isActive`, `role` (USER/ADMIN)
- Relations: notebooks, materials, chatSessions, chatMessages, generatedContent, refreshTokens, backgroundJobs, artifacts, podcastSessions, explainerVideos, researchSessions, codeExecutions

**Notebook**
- `id`, `userId`, `name`, `description`, `createdAt`, `updatedAt`
- Belongs to User, has many Materials, ChatSessions, ChatMessages, GeneratedContent

**Material**
- `id`, `userId`, `notebookId`, `filename`, `title`, `originalText` (summary), `status` (enum), `chunkCount`, `sourceType` (`file`/`url`/`youtube`/`text`), `metadata` (JSON), `error`
- **Status enum**: `pending` → `processing` → `ocr_running` / `transcribing` → `embedding` → `completed` / `failed`

**ChatSession**
- `id`, `notebookId`, `userId`, `title`
- Has many ChatMessages, Artifacts

**ChatMessage**
- `id`, `notebookId`, `userId`, `chatSessionId`, `role` (user/assistant), `content`, `agentMeta` (JSON — intent, tools_used, chunks_used)
- Has many ResponseBlocks, Artifacts

**ResponseBlock**
- `id`, `chatMessageId`, `blockIndex`, `text`
- Paragraph-level blocks of assistant responses, support per-block actions

**GeneratedContent**
- `id`, `notebookId`, `userId`, `materialId`, `contentType` (flashcards/quiz/presentation/mindmap/audio), `title`, `data` (JSON), `language`
- Has many ExplainerVideos

**ExplainerVideo**
- `id`, `userId`, `presentationId`, `pptLanguage`, `narrationLanguage`, `voiceGender`, `voiceId`, `status` (VideoStatus enum), `script`, `audioFiles`, `videoUrl`, `duration`, `chapters`

**RefreshToken**
- `id`, `userId`, `tokenHash` (SHA-256), `family` (for rotation detection), `used` (bool), `expiresAt`
- Used for sliding window token rotation with breach detection

**BackgroundJob**
- `id`, `userId`, `jobType`, `status` (JobStatus enum), `result` (JSON), `error`
- Supports: `pending` → `processing` / `embedding` / `ocr_running` / `transcribing` → `completed` / `failed`

**PodcastSession**, **PodcastSegment**, **PodcastDoubt**, **PodcastExport**, **PodcastBookmark**, **PodcastAnnotation**
- Full podcast session lifecycle with Q&A doubts, bookmarks, chapter annotations, multi-format exports

**Artifact**
- `id`, `userId`, `notebookId`, `sessionId`, `messageId`, `filename`, `mimeType`, `displayType`, `sizeBytes`, `downloadToken` (unique), `tokenExpiry`, `workspacePath`, `sourceCode`
- Time-limited download tokens for code execution output files

**Other Models**: `UserTokenUsage`, `ApiUsageLog`, `AgentExecutionLog`, `CodeExecutionSession`, `ResearchSession`

---

### ChromaDB Vector Store

Managed in `app/db/chroma.py`:

- **Collection name**: `chapters` (single global collection, multi-tenant via metadata filters)
- **Embedding function**: `SentenceTransformerEmbeddingFunction` with `BAAI/bge-m3` (1024-dim, CPU)
- **Persistence**: `PersistentClient` at `settings.CHROMA_DIR`
- **Version marker file**: `.embedding_version` in chroma dir — if model version changes, the entire collection is auto-wiped and rebuilt
- **Dimension probe**: On startup, a test embed is upserted to verify dimensionality  
- **Telemetry**: Completely disabled (`ANONYMIZED_TELEMETRY=False`, posthog patched to no-op)
- **Thread safety**: `threading.RLock()` around client/collection initialization

Each document stored in ChromaDB has metadata:
```
{
  "user_id": str,          # MANDATORY for tenant isolation
  "material_id": str,
  "notebook_id": str,
  "embedding_version": str,
  "source": "chapter",
  "filename": str,
  "section_title": str,
  "chunk_index": str,
  "is_structured": "true"  # for CSV/Excel structured summaries
}
```

---

## Middleware Stack

Applied to all requests in order:

1. **`performance_monitoring_middleware`** — Logs slow requests, tracks endpoint latency
2. **`rate_limit_middleware`** — In-memory sliding window rate limiter
3. **`log_requests` (custom)** — Per-request UUID, duration logging, attaches `X-Request-ID` header
4. **`CORSMiddleware`** — Configured with `settings.CORS_ORIGINS`; in production, `TrustedHostMiddleware` also added
5. **Exception Handlers**:
   - `HTTPException` → structured JSON with CORS headers
   - `Exception` (global) → 500 JSON with `request_id`

---

## Authentication System

### Architecture: JWT + HttpOnly Cookie Rotation

**Files**: `app/routes/auth.py`, `app/services/auth/service.py`, `app/services/auth/security.py`

### Token Types
| Token | Storage | TTL | Purpose |
|-------|---------|-----|---------|
| Access Token | `Authorization: Bearer` header | 15 minutes | API authentication |
| Refresh Token | HttpOnly cookie (`refresh_token`) | 7 days | Access token renewal |
| File Token | Query param `?token=` | 5 minutes | Secure file downloads |

### Password Security
- Bcrypt hashing via `passlib[bcrypt]`
- Password requirements (enforced in Pydantic validator):
  - Minimum 8 characters
  - At least 1 uppercase letter
  - At least 1 lowercase letter  
  - At least 1 digit

### Token Rotation with Breach Detection
1. Each refresh token has a `family` UUID
2. On `POST /auth/refresh`: validates token, marks it as `used=True`, issues new token in same family
3. If a `used=True` token is presented → **Reuse detected** → entire token family is revoked (all sessions)
4. Refresh tokens are stored as **SHA-256 hashes** (never the raw token)

### API Endpoints

| Method | Path | Auth Required | Description |
|--------|------|--------------|-------------|
| POST | `/auth/signup` | ❌ | Create new user account |
| POST | `/auth/login` | ❌ | Authenticate, get access + refresh token |
| POST | `/auth/refresh` | ❌ (cookie) | Rotate refresh token |
| GET | `/auth/me` | ✅ | Get current user info |
| POST | `/auth/logout` | ✅ | Revoke all refresh tokens + clear cookie |

### `get_current_user` Dependency
Supports token from:
1. `Authorization: Bearer <token>` header
2. `?token=<value>` query param (for WebSocket, file downloads)

Validates: token type must be `"access"`, user must exist and be active (`isActive=True`).

---

## LLM Service Layer

**Files**: `app/services/llm_service/llm.py`, `llm_schemas.py`, `structured_invoker.py`

### Provider Architecture
Four providers are registered in `_PROVIDERS` dict:

| Provider | Class | Notes |
|----------|-------|-------|
| `OLLAMA` | `ChatOllama` | Local Ollama server |
| `GOOGLE` | `ChatGoogleGenerativeAI` | Requires `GOOGLE_API_KEY` |
| `NVIDIA` | `ChatNVIDIA` | NVIDIA NIM endpoint, streaming enabled, thinking mode off |
| `MYOPENLM` | `MyOpenLM` | Custom HTTP fallback |

### `get_llm(mode, temperature, top_p, max_tokens, provider, **kwargs)` 
- Mode presets: `chat` (0.2), `creative` (0.7), `structured` (0.1), `code` (0.1)
- Results **cached** in `_llm_cache` (LRU, max 16 entries) to avoid rebuilding clients per request

### `get_llm_structured(temperature, top_p, max_tokens, provider, **kwargs)`
- Uses structured/low-temperature settings (T=0.1, top_p=0.9)
- For Google/Ollama, adds `top_k=settings.LLM_TOP_K`

### `extract_chunk_content(chunk)`
- Handles both `str` and `list` content from LLM chunks
- Filters out thinking blocks (for NVIDIA/Claude models)

### Structured Output (`structured_invoker.py`)
- `invoke_structured(prompt, output_schema: BaseModel, max_retries=2)` — uses LangChain `.with_structured_output()` or JSON parsing with `json_repair` fallback

---

## RAG Pipeline

**Files**: `app/services/rag/`

### Full RAG Flow

```
User Query
    ↓
secure_similarity_search_enhanced(user_id, query, material_ids, notebook_id)
    ↓
[1] Check: is_cross_document_query? (compare/vs/contrast keywords)
    ↓
[2] ChromaDB.query(query_texts=[query], n_results=INITIAL_VECTOR_K, where=filter)
    Filter: {"$and": [{"user_id": user_id}, {"material_id": {"$in": material_ids}}]}
    ↓
[3] MMR (Maximal Marginal Relevance) reranking
    - Fetch embeddings from ChromaDB
    - Compute cosine similarities query↔docs and selected↔remaining
    - Iteratively pick docs that balance relevance + diversity (λ=0.5)
    ↓
[4] Cross-Encoder Reranker (BAAI/bge-reranker-large)
    - Input: [query, chunk] pairs
    - Output: relevance scores → sort descending
    - Batch size: 16, max_length: 512 tokens
    - Falls back gracefully if GPU OOM
    ↓
[5] Source Diversity Balancing (multi-material queries)
    - Guarantees MIN_CHUNKS_PER_MATERIAL (1) from each source
    - Up to MAX_CHUNKS_PER_MATERIAL (3) per source
    - Remaining slots filled by top-ranked chunks
    ↓
[6] Structured Chunk Expansion
    - If chunk is_structured=true, loads full raw file text
    - Capped at 50,000 chars
    ↓
[7] Context Formatting → format_context_with_citations()
    - Produces [SOURCE 1]\ntext\n\n[SOURCE 2]\ntext\n format
    - Attaches material filenames
    ↓
Formatted Context String → LLM
```

### Tenant Isolation
- Every retrieval call **must** include `user_id`
- `_build_where()` always adds `{"user_id": user_id}` to ChromaDB filter
- `_validate_result_ownership()` post-validates that all returned documents belong to the authenticated user
- `TenantIsolationError` raised if filter is missing `user_id`
- Security violations logged to `security.retrieval` logger

### Embedder (`rag/embedder.py`)
- `embed_and_store(chunks, material_id, user_id, notebook_id, filename)`:
  - Batch size: 200 chunks per upsert
  - Up to 3 retry attempts per batch with exponential backoff
  - Dimension mismatch → invalidates version marker and resets singletons
- `delete_material_embeddings(material_id, user_id)` — queries by `material_id` + `user_id` filter, deletes all matching IDs

### Citation Validator (`rag/citation_validator.py`)
- Post-validates that LLM responses contain properly formatted `[SOURCE N]` citations
- Runs after every RAG response; violations logged as warnings

---

## Text Processing Pipeline

**Files**: `app/services/text_processing/`

### File Type Detector (`file_detector.py`)
Classifies uploaded files into categories: `document`, `spreadsheet`, `image`, `audio`, `video`

### Text Extractor (`extractor.py`)
`EnhancedTextExtractor.extract_text(file_path, source_type)` dispatches based on extension:

| Extension | Method |
|-----------|--------|
| `pdf` | PyMuPDF + PDFPlumber + optional OCR for image pages |
| `docx`, `doc` | `unstructured` library (with `python-docx` fallback) |
| `pptx`, `ppt` | `unstructured` library |
| `xlsx`, `xls`, `ods` | pandas DataFrames → structured summary |
| `csv`, `tsv` | pandas → structured summary |
| `txt`, `md`, `rst`, others | Direct UTF-8 read (with chardet encoding detection) |
| `jpg`, `png`, `gif`, `webp` | EasyOCR + Tesseract (OCRService) |
| `mp3`, `wav`, `mp4`, `m4a`, `webm` | OpenAI Whisper transcription |

### OCRService (`ocr_service.py`)
- EasyOCR as primary, Tesseract as fallback
- Timeout: `OCR_TIMEOUT_SECONDS` (default 300s)
- Retries: `PROCESSING_MAX_RETRIES` (default 2)

### Whisper Transcription (`transcription_service.py`)
- OpenAI Whisper (local model)
- Timeout: `WHISPER_TIMEOUT_SECONDS` (default 600s)

### YouTube Service (`youtube_service.py`)
- Uses `youtube-transcript-api` for caption extraction
- Falls back to `yt-dlp` for audio download + Whisper transcription

### Web Scraping (`web_scraping.py`)
- `trafilatura` for clean article extraction
- BeautifulSoup4 fallback
- `fake-useragent` for user-agent rotation

### Text Chunker (`chunker.py`)
Intelligent chunking strategy:

1. **Structured data** (CSV/Excel): Split on `===` section separators, preserve schema headers
2. **Markdown-structured text**: Split on headings (`# ## ### ####`) then process each section separately
3. **Plain prose**: Split on double-newlines (paragraphs)

Per-section processing:
- If paragraph ≤ `TARGET_CHUNK_CHARS` (2000 chars): single chunk
- If paragraph ≤ `MAX_PARAGRAPH_CHARS` (3200 chars): single chunk (or semantic split if enabled)
- If paragraph > `MAX_PARAGRAPH_CHARS`: sentence-based splitting with `OVERLAP_CHARS` (600 chars) overlap

Quality filters:
- Min chunk length: `MIN_CHUNK_LENGTH` (100 chars)
- Min alpha ratio: 10% alphabetic characters

---

## Background Job System

**Files**: `app/services/worker.py`, `app/services/job_service.py`

### Architecture
- Single asyncio `Task` (`job_processor`) running as a perpetual loop
- Polls DB for pending jobs every `_POLL_SECONDS = 2.0` seconds
- Maximum `MAX_CONCURRENT_JOBS = 5` parallel jobs (semaphore via task set tracking)
- Notified immediately when new jobs are created via `job_queue.notify()`

### Job Processor Loop
```
while not shutdown:
    1. Collect done tasks, await them
    2. Calculate slots available = MAX_CONCURRENT - active
    3. Fetch up to `slots` pending jobs from DB (FIFO)
    4. Create asyncio.Task for each → add to active set
    5. If active >= MAX or no new jobs: wait for first completion
    6. Else: wait on short poll timer
```

### Stuck Job Recovery
On startup, jobs stuck in `processing` status for > 30 minutes are auto-reset to `pending`.

### Job Types

| `source_type` | Handler | Description |
|-------------|---------|-------------|
| `file` | `process_material_by_id` | Uploaded file processing |
| `url` / `web` | `process_url_material_by_id` | URL/web page scraping |
| `youtube` | `process_url_material_by_id` | YouTube transcript extraction |
| `text` | `process_text_material_by_id` | Pasted text ingestion |

### After Successful Job
- Notebook gets auto-renamed via AI if it still has a default name and was created within last 5 minutes
- Material gets AI-generated title in a background asyncio task

### Old Job Cleanup
Background task `_cleanup_old_jobs()` removes jobs older than 7 days.

---

## WebSocket Real-Time Layer

**Files**: `app/services/ws_manager.py`, `app/routes/websocket_router.py`

### WebSocket Endpoint
`GET /ws/jobs/{user_id}?token=<access_token>`

Two-phase auth:
1. Token in query param → immediate auth
2. No query param → expect `{"type": "auth", "token": "..."}` message within 10 seconds

Security checks:
- Token `user_id` must match URL `user_id`
- Max `MAX_CONNECTIONS_PER_USER = 10` connections per user

### Connection Manager (`ws_manager.py`)
- `connect_user(user_id, ws)` — accepts WebSocket, adds to per-user list
- `disconnect_user(user_id, ws)` — removes from list, cleans empty entries
- `send_to_user(user_id, payload)` — broadcasts JSON to all connections for a user; dead connections auto-pruned
- `broadcast(payload)` — sends to all connected users

### Server→Client Event Types
| Event Type | Sender | Payload |
|-----------|--------|---------|
| `material_update` | worker.py after each processing stage | `{material_id, status, title?, error?, chunk_count?}` |
| `notebook_update` | material_service.py after AI title gen | `{notebook_id, name}` |
| `podcast_progress` | podcast session_manager | `{session_id, phase, message, progress}` |
| `podcast_segment_ready` | podcast TTS pipeline | `{session_id, segment: {index, speaker, text, audioUrl, durationMs, chapter}}` |
| `podcast_complete` | session_manager | `{session_id, total_segments, total_duration_ms}` |
| `podcast_failed` | session_manager | `{session_id, error}` |
| `ping` / `pong` | server keepalive | `{}` |
| `connected` | on join | `{channel, user_id}` |

---

## Feature-by-Feature Flow

### Upload & Material Processing

**Route**: `POST /upload`  
**Auth**: Required

#### File Upload Flow
```
1. Client streams file → write to temp file (1MB chunks via asyncio executor)
2. Validate file (validate_upload):
   - Check MIME type via python-magic 
   - Check file size ≤ MAX_UPLOAD_SIZE_MB
   - Check for dangerous extensions
3. Move temp file → data/uploads/{user_id}/{uuid}_{filename}
4. If auto_create_notebook=true: create Notebook record
5. create_material_record() → INSERT Material (status=pending)
6. create_job() → INSERT BackgroundJob (type=material_processing)
7. job_queue.notify() → wake up job processor immediately
8. Return: {material_id, job_id, filename, status: "pending"}
```

#### URL Upload Flow
```
POST /upload/url  →  {url, notebook_id, source_type, title}
1. SSRF validation: reject private IPs, localhost, file:// schemes
2. Detect YouTube URL → source_type = "youtube"
3. Otherwise auto-detect → "url" or "web"
4. create_material_record() with source_type
5. create_job() with payload {url, source_type}
6. Return: {material_id, job_id, url, status: "pending"}
```

#### Text Upload Flow
```
POST /upload/text  →  {text, title, notebook_id}
1. Validate text length > 10 chars
2. create_material_record(source_type="text")
3. create_job() with payload {text, title}
4. Return: {material_id, job_id, status: "pending"}
```

#### Background Processing Pipeline
```
_process_job(job)
    ↓
detect file type → set material status (ocr_running / transcribing / processing)
    ↓
EnhancedTextExtractor.extract_text(file_path) — runs in thread executor
    ↓
[If structured: CSV/Excel] → make_structured_summary_chunk()
   - Load full DataFrame, generate: schema + dtypes + shape + head(5)
   - Store full text for context expansion
   - Skip to embedding (1 chunk)
    ↓
[If prose/document] → chunk_text(text, use_semantic=True, source_type)
   - Heading-aware or paragraph-based chunking
   - 150-token overlap between chunks
    ↓
save_material_text(material_id, text) → disk at data/material_text/{material_id}.txt
    ↓
embed_and_store(chunks, material_id, user_id, notebook_id) → ChromaDB
    ↓
UPDATE Material: status=completed, chunkCount, title (fast title), originalText (1000-char summary)
    ↓
WebSocket → send material_update {status: "completed"} to user
    ↓
Background asyncio task:
  - generate_material_title() via LLM
  - generate_notebook_name() via LLM (if notebook is new and default-named)
  - WebSocket notifications for both
```

---

### Chat System (v2)

**Route**: `POST /chat`  
**Auth**: Required  
**Response**: SSE stream

#### Router Logic (`chat_v2/router_logic.py`)

The `route_capability()` function determines intent:

| Priority | Condition | Capability |
|----------|-----------|-----------|
| 1 | `intent_override` provided | As specified |
| 2 | `material_ids` not empty | `RAG` |
| 3 | Code/data keywords in message | `CODE_EXECUTION` |
| 4 | Web search keywords in message | `WEB_SEARCH` |
| 5 | Default | `NORMAL_CHAT` |

**Code keywords**: plot, chart, graph, histogram, scatter, heatmap, dataset, csv, dataframe, regression, classify, cluster, analyze data, visualize, train model, predict, correlation, pandas, numpy, matplotlib, seaborn, sklearn

**Web search keywords**: search the web, search online, latest news, current events, look up online, google, recent developments, today's, this week

#### Orchestrator Flow (`chat_v2/orchestrator.py`)

```
Capability.RAG:
  1. _run_rag_tool() → secure_similarity_search_enhanced → ToolResult(context chunks)
  2. If no context → return "no relevant information" message
  3. build_messages(user_message, history, rag_context) → prompt
  4. llm.astream(prompt) → token SSE events
  5. validate_citations(answer, chunks_used) → log if invalid
  6. persist messages + response blocks

Capability.WEB_SEARCH:
  1. _run_web_search_tool() → DuckDuckGo search → ToolResult(search results)
  2. Build synthesis prompt with search results
  3. llm.astream (T=0.3) → tokens → SSE
  4. persist

Capability.CODE_EXECUTION:
  1. _handle_code_execution() → python_tool.execute()
  2. LLM generates code → sse_code_block event
  3. persist

Capability.WEB_RESEARCH:
  1. _handle_research() → research_tool.execute()
  2. stream_research() → multi-iteration web search + synthesis
  3. persist

Capability.NORMAL_CHAT:
  1. build_messages(user_message, history) → no RAG context
  2. llm.astream() → tokens
  3. persist
```

#### SSE Event Format

All events follow:
```
event: <type>
data: <JSON>
```

| Event Type | Payload | Description |
|------------|---------|-------------|
| `token` | `{content: str}` | Streaming response token |
| `meta` | `{intent, chunks_used, elapsed}` | Response metadata |
| `done` | `{elapsed, intent?}` | Stream complete |
| `error` | `{error: str}` | Error occurred |
| `blocks` | `[{id, text, blockIndex}]` | Response blocks saved |
| `tool_start` | `{tool, label}` | Tool invocation started |
| `tool_result` | `{tool, success, summary}` | Tool completed |
| `code_block` | `{code, language, session_id}` | Generated code |
| `artifact` | `{filename, mime, display_type, ...}` | File produced by code |
| `web_search_update` | `{status, queries, scrapingUrls}` | Web search progress |
| `web_sources` | `{sources: [{title, url, snippet}]}` | Web sources found |
| `research_start` | `{query, max_iterations, target_sources}` | Deep research started |
| `research_phase` | `{phase, iteration, queries, sources_count}` | Research progress |

#### Session Management
- `POST /chat/sessions/{notebook_id}` — list sessions
- `POST /chat/create-session/{notebook_id}` — create session
- `DELETE /chat/sessions/{session_id}` — delete session
- `GET /chat/history/{notebook_id}?session_id=` — get message history
- `DELETE /chat/history/{notebook_id}` — clear history

#### Block Follow-up
`POST /chat/block-followup` — per-paragraph LLM actions:
- `ask` — answer a specific question about the paragraph
- `simplify` — rewrite in simpler language
- `translate` — translate to specified language
- `explain` — expand with more depth and examples

#### Chat Suggestions
`POST /chat/suggestions` — AI-powered prompt completion:
- Analyzes notebook context (title + material names)
- Returns 3-5 confidence-ranked prompt completions

---

### Quiz Generation

**Route**: `POST /quiz`  
**Auth**: Required

```
Request: {material_id?, material_ids?, topic?, mcq_count (1-150), difficulty, additional_instructions}

1. Load material text from storage (require_material_text or require_materials_text)
2. If topic provided: prepend "Focus on the topic: {topic}" to text
3. Run in thread executor: generate_quiz(text, mcq_count, difficulty, instructions)
   - LLM call with quiz_prompt.txt
   - Structured JSON output: {questions: [{question, options, correct_answer, explanation}]}
4. Return JSON quiz

Difficulty levels: easy, medium, hard (DifficultyLevel enum)
Max questions: 150
```

---

### Flashcard Generation

**Route**: `POST /flashcard`  
**Auth**: Required

```
Request: {material_id?, material_ids?, topic?, card_count (1-150), difficulty, additional_instructions}

1. Load material text
2. If topic: prepend topic filter
3. Thread executor: generate_flashcards(text, card_count, difficulty, instructions)
   - LLM with flashcard_prompt.txt
   - Structured JSON: {flashcards: [{front, back, category?}]}
4. Return JSON flashcards
```

---

### Presentation (PPT) Generation

**Route**: `POST /presentation` (sync) or `POST /presentation/async` (background job)  
**Auth**: Required

#### Sync Flow
```
1. Load material text
2. get_ppt_prompt(text, slide_count, theme, additional_instructions)
3. invoke_structured(prompt, PresentationHTMLOutput, max_retries=2)
   - PresentationHTMLOutput schema: {title, slide_count, theme, html}
   - HTML is full standalone HTML with .slide divs
4. _post_process_html(html):
   - Enforce 1920×1080 slide dimensions
   - Add viewport meta
   - Add safety CSS overrides
   - Strip all <script> tags
   - Replace 100vh → 1080px
5. extract_slides(html) → parse .slide divs with BeautifulSoup
6. Return {presentation_id, title, slide_count, theme, html, slides[]}
```

#### Async Flow (recommended for large docs)
```
1. POST /presentation/async → creates BackgroundJob → returns {job_id, status: "pending"}
2. Client polls GET /jobs/{job_id}
3. Job runs generate_presentation() in background
4. On completion: store result in job.result (JSON)
5. Client fetches completed result
```

**Slide dimensions**: 1920×1080px (forced via CSS), 16:9 aspect ratio

---

### Mind Map Generation

**Route**: `POST /mindmap`  
**Auth**: Required

```
Request: {material_ids, notebook_id, additional_context?}

1. Verify notebook ownership
2. generate_mindmap(material_ids, notebook_id, user_id):
   - Load and combine material texts
   - LLM with mindmap_prompt.txt
   - Structured JSON: {nodes: [{id, label, type}], edges: [{from, to}]}
3. Save to GeneratedContent (contentType="mindmap")
4. Return {nodes, edges, id}

GET /mindmap/{notebook_id} → retrieve latest mindmap
DELETE /mindmap/{id} → delete
```

---

### Podcast (Live) System

**Route**: `/podcast/*`  
**Auth**: Required  
**Real-time**: WebSocket progress events

#### Session Lifecycle
```
1. POST /podcast/session → create_session()
   - Validates mode (overview/deep-dive/debate/q-and-a/full/topic)
   - Topic required for topic/deep-dive modes
   - Selects voice pair from voice_map per language
   - Creates PodcastSession (status=created)

2. POST /podcast/session/{id}/start → start_generation()
   - Validates session can be started (status=created or failed)
   - Kicks off asyncio task: _generation_pipeline()
```

#### Generation Pipeline
```
_generation_pipeline():
  Phase 1 (status=script_generating, progress=5%):
    - _gather_context() — RAG queries based on mode:
      * overview/full: 2 broad queries
      * deep-dive: technical detail queries
      * debate: argument/counter-argument queries
      * q-and-a: FAQ queries
      * topic: 2 targeted queries on the specific topic
    - get_podcast_script_prompt(language, mode_instruction, context)
    - LLM call (mode=creative, max_tokens=12000)
    - Parse JSON: {title, segments: [{segment_index, speaker, text}], chapters[]}
    - WebSocket: podcast_progress {phase: "script", progress: 25%}
    
  Phase 2 (status=audio_generating):
    - synthesize_all_segments():
      * Concurrency: 15 simultaneous Edge-TTS requests
      * Per segment: edge_tts.Communicate(text, voice_id) → .mp3 file
      * Duration: mutagen.MP3 to read audio length
      * 3 retry attempts per segment
    - Per segment ready callback:
      * INSERT PodcastSegment to DB
      * WebSocket: podcast_segment_ready event
    - Progress events at each completion
    
  Phase 3 (status=ready, progress=100%):
    - UPDATE PodcastSession: status=ready, title, chapters, totalDurationMs
    - WebSocket: podcast_complete event
```

#### Podcast Modes
| Mode | Description | RAG Strategy |
|------|-------------|-------------|
| `overview` | High-level survey of all topics | 2 broad comprehensive queries |
| `deep-dive` | In-depth technical analysis | 2 technical detail queries |
| `debate` | Present multiple viewpoints | Arguments + counter-arguments queries |
| `q-and-a` | Q&A format | FAQ + misconceptions queries |
| `full` | Comprehensive long-form episode | Breadth + depth queries |
| `topic` | Focus on specific topic | 2 targeted topic queries |

#### Voice System
- `voice_map.py` provides per-language voice pairs (host + guest)
- Supports: English, Spanish, French, German, Japanese, Chinese, Hindi, Portuguese, Arabic, Korean, Italian, Dutch, Russian, Turkish, Swedish, Norwegian, Danish, Finnish, Polish
- `POST /podcast/voices` — list all available voices
- `POST /podcast/voice-preview` — stream audio preview for a voice

#### Q&A (Doubts) System
```
POST /podcast/session/{id}/question
  {question_text, paused_at_segment, question_audio_url?}
  
1. qa_service.handle_question():
   - Validate session
   - Get context (3 segments around pause point)
   - LLM generates answer (qa_prompt.txt)
   - generate TTS audio for answer
   - Store PodcastDoubt record
2. Return {answer_text, answer_audio_url}
```

#### Bookmarks & Annotations
- `POST /podcast/session/{id}/bookmark` — bookmark a segment with optional label
- `GET /podcast/session/{id}/bookmarks` — list bookmarks
- `POST /podcast/session/{id}/annotation` — add notes to a segment
- `DELETE /podcast/session/{id}/annotation/{id}` — remove annotation

#### Export
- `POST /podcast/session/{id}/export` — generate PDF or JSON export
- `GET /podcast/export/{export_id}` — check export status
- `GET /podcast/export/file/{session_id}/{filename}` — download export file

---

### Explainer Video System

**Route**: `/explainer/*`  
**Auth**: Required  
**Processing**: Background task

#### Pipeline Flow
```
POST /explainer/generate
  {material_ids, notebook_id, ppt_language, narration_language, voice_gender, presentation_id?, create_new_ppt?}

1. Validate languages (EDGE_TTS_VOICES keys)
2. Select voice_id via get_voice_id(language, gender)
3. Get or create presentation:
   a. Use existing: load from GeneratedContent DB record
   b. Create new: run generate_presentation() → save to DB
4. Create ExplainerVideo record (status=pending)
5. Start background_tasks.add_task(process_explainer_video, ...)

process_explainer_video():
  Stage 1 (status=capturing_slides):
    - ScreenshotService.capture_slides(html, user_id, presentation_id, slide_count)
    - LibreOffice headless + pdf2image for slide capture
    - Fallback: create placeholder images if capture fails
  
  Stage 2 (status=generating_script):
    - generate_slide_scripts_async(slides, language, max_concurrent=3)
    - For each slide: LLM generates 30-60 second narration script
    - Stored in explainer.script JSON

  Stage 3 (status=generating_audio):
    - For each slide: edge_tts → MP3 file
    - get_audio_duration() via mutagen

  Stage 4 (status=composing_video):
    - For each slide: compose_slide_video(image, audio, output.mp4) via ffmpeg
    - concatenate_videos(all_slide_videos, final.mp4) via ffmpeg concat demuxer
    
  Stage 5 (status=completed):
    - Compute chapter timestamps
    - UPDATE ExplainerVideo: videoUrl, duration, chapters, completedAt
    - Save to GeneratedContent DB record
```

#### Status Progression
`pending` → `capturing_slides` → `generating_script` → `generating_audio` → `composing_video` → `completed` / `failed`

---

### Code Execution System

**Route**: `POST /code-execution/execute-code`  
**Auth**: Required  
**Response**: SSE stream

#### Full Execution Flow
```
Request: {code, language, notebook_id, timeout (5-120s), stdin?}

1. validation: validate_code(code) — detect dangerous patterns
   - Blocked: os.system, subprocess, eval with dangerous args, __import__
   - Returns ValidationResult(is_safe, violations)
2. sanitize_code(code)
3. Create temp work_dir
4. run_in_sandbox(code, work_dir, timeout, language):
   
   [For compiled languages: C/C++/Java/Rust]
   a. Write source file to work_dir
   b. Run compiler (gcc/g++/javac/rustc) with 60s timeout
   c. If compilation fails: return compilation error
   
   [Run phase for all languages]
   a. Start subprocess: python/node/ts-node/java/go/go run/bash/binary
   b. Stream stdout/stderr asynchronously
   c. Enforce timeout via asyncio.wait_for
   d. stdout lines starting __CHART__: → extract base64 chart data
   e. Truncate output at 16MB
   f. Return ExecutionResult(stdout, stderr, exit_code, elapsed, chart_base64)

5. If exit_code != 0 and ModuleNotFoundError:
   - Extract module name
   - If in APPROVED_ON_DEMAND: install_package_if_missing_async()
   - Retry execution

6. If still failing: LLM auto-repair loop (max_retries=3):
   - get_code_repair_prompt(code, error)
   - LLM generates repaired code
   - validate_code(repaired) → if safe: yield sse repair_suggestion
   
7. If success: _detect_output_files(work_dir)
   - Register each artifact in DB (Artifact model)
   - Set download token with 24h expiry
   - Yield sse artifact events

8. Yield sse execution_done
9. Persist CodeExecutionSession to DB
```

#### Supported Languages
Python, JavaScript (Node.js), TypeScript (ts-node), C, C++, Java, Go, Rust, Bash

#### Artifact Classification
| Display Type | Condition |
|-------------|-----------|
| `image` | MIME image/* |
| `csv_table` | .csv, .xlsx, .xls |
| `json_tree` | .json |
| `text_preview` | .txt, .md, .log |
| `html_preview` | .html |
| `pdf_embed` | .pdf |
| `audio_player` | audio/* MIME |
| `video_player` | video/* MIME |
| `file_card` | everything else |

---

### Artifact Management

**Route**: `/artifacts/*`  
**Auth**: Bearer token or `?token=` query param (file token)

```
GET /artifacts/{artifact_id}
  - Validate ownership or download token
  - Stream file with correct MIME type

GET /artifacts/download/{download_token}
  - Token-based download (no auth header needed)
  - Validates token expiry
  - Streams file

POST /artifacts/refresh-token/{artifact_id}
  - Issues new download token (24h TTL)
  - Old token invalidated

GET /artifacts/notebook/{notebook_id}
  - List all artifacts for a notebook
  - Categorized by: charts, datasets, reports, models, files

DELETE /artifacts/{artifact_id}
  - Delete artifact record + file from disk
```

---

### Web Search & Research Pipeline

#### Simple Web Search (`search.py`)
`POST /search/web → {query, file_type, engine}`
- Calls `ddg_search()` via `ddgs` library
- Returns max 5 results: `{title, link, snippet}`

#### Web Search Tool (`tools/web_search_tool.py`)
Used in chat when WEB_SEARCH capability is detected:
1. Query DuckDuckGo
2. Scrape each URL with `WebScrapingService`
3. Return formatted results with source citations

#### Deep Research Pipeline (`services/research/pipeline.py`)
Used in chat when WEB_RESEARCH capability is requested:
```
stream_research(query, user_id, notebook_id, session_id):
  1. emit research_start event
  2. Generate multiple search queries from original query
  3. Multi-iteration loop (default max 3 iterations):
     a. Search web for each query
     b. Scrape up to TARGET_SOURCES (80) pages
     c. emit research_phase events with progress
  4. Synthesize all content into comprehensive report
  5. emit citations event with source URLs
  6. Stream report tokens via SSE
  7. Save ResearchSession to DB
```

---

### Notebook Management

**Route**: `/notebooks/*`  
**Auth**: Required

```
POST /notebooks → {name, description} → creates Notebook
GET /notebooks → list user's notebooks (paginated: skip/take)
GET /notebooks/{id} → get single notebook
PUT /notebooks/{id} → update name/description
DELETE /notebooks/{id} → delete (cascades to all materials, messages, content)

POST /notebooks/{id}/content → save generated content (flashcards/quiz/presentation/audio)
GET /notebooks/{id}/content → list all generated content
DELETE /notebooks/{id}/content/{content_id} → delete generated content
PUT /notebooks/{id}/content/{content_id} → update content title
```

---

### Search Endpoint

`POST /search/web` — Web search via DuckDuckGo (requires auth)

---

### Proxy Endpoint

`/proxy/*` — A proxy endpoint for forwarding requests. Used to bypass CORS or access external resources.

---

## Rate Limiting

**File**: `app/services/rate_limiter.py`

In-memory sliding window rate limiter (middleware):
- Tracks request counts per IP
- Returns `429 Too Many Requests` when limit exceeded
- Applied to all endpoints

---

## Performance Logging

**File**: `app/services/performance_logger.py`

`performance_monitoring_middleware` middleware:
- Tracks response time for every request
- Logs slow requests above threshold
- Used for latency monitoring

---

## Security Architecture

### Input Validation
- All request bodies validated by Pydantic v2 with strict validators
- File uploads validated via `file_validator.py` (MIME type inspection via python-magic)
- SSRF prevention on URL uploads: blocks private IPs (`10.x`, `192.168.x`, `172.16-31.x`, `127.x`), `localhost`, `file://` schemes

### Code Execution Security (`code_execution/security.py`)
- Static analysis before execution: blocks `os.system`, dangerous `subprocess`, `eval`, `exec` with suspicious args, `__import__` bypass patterns
- Execution in temp directory (isolated working directory)
- Output truncation at 16MB
- Configurable timeout (5-120 seconds)
- Only approved packages can be auto-installed

### JWT Security
- HS256 signing with configurable secret
- Short access token TTL (15 min)
- Refresh token rotation with breach detection
- Tokens stored as SHA-256 hashes in DB

### Path Traversal Prevention
- `safe_path()` helper in `routes/utils.py` validates file paths are within expected directories

### CORS
- Strict origin allowlist via `settings.CORS_ORIGINS`
- Production: `TrustedHostMiddleware` additionally validates `Host` header

---

## CLI Tools

Located in `backend/cli/`:

| Script | Purpose |
|--------|---------|
| `reindex.py` | Re-embed all materials (after model change) |
| `backup_chroma.py` | Backup ChromaDB to archive |
| `export_embeddings.py` | Export embeddings to file |
| `import_embeddings.py` | Import embeddings from file |
| `download_models.py` | Pre-download HuggingFace models |
| `migrate_material_joins.py` | DB migration for join table |

---

## Output Directory Structure

```
backend/
├── data/
│   ├── uploads/
│   │   └── {user_id}/
│   │       └── {uuid}_{filename}      # Uploaded source files
│   ├── chroma/                         # ChromaDB persistent storage
│   ├── material_text/
│   │   └── {material_id}.txt          # Extracted full text cache
│   ├── models/                         # Downloaded HuggingFace models
│   └── artifacts/
│       └── {artifact_id}/
│           └── {filename}             # Code execution output files
├── output/
│   ├── presentations/
│   │   └── {user_id}/{presentation_id}/*.png  # Slide screenshots
│   ├── explainers/
│   │   └── {explainer_id}/
│   │       ├── slide_1.mp3, slide_1.mp4, ...
│   │       └── explainer_final.mp4
│   ├── podcast/
│   │   └── {session_id}/
│   │       └── seg_0000_host.mp3, seg_0001_guest.mp3, ...
│   └── generated/                     # Miscellaneous generated files
└── logs/
    └── app.log                         # Rotating log (10MB × 3)
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | ✅ | — | PostgreSQL DSN |
| `JWT_SECRET_KEY` | ✅ | — | JWT signing secret (min 32 chars recommended) |
| `LLM_PROVIDER` | ✅ | `OLLAMA` | Active LLM provider |
| `GOOGLE_API_KEY` | Only if GOOGLE | `""` | Gemini API key |
| `NVIDIA_API_KEY` | Only if NVIDIA | `""` | NVIDIA NIM API key |
| `ENVIRONMENT` | ❌ | `development` | Enables TrustedHostMiddleware, secure cookies in `production` |
| `CHROMA_DIR` | ❌ | `./data/chroma` | ChromaDB path |
| `UPLOAD_DIR` | ❌ | `./data/uploads` | File upload path |
| `EMBEDDING_MODEL` | ❌ | `BAAI/bge-m3` | Embedding model |
| `EMBEDDING_VERSION` | ❌ | `bge_m3_v1` | Version marker (change triggers re-index) |
| `USE_RERANKER` | ❌ | `True` | Enable cross-encoder reranking |
| `CORS_ORIGINS` | ❌ | `localhost:3000,5173` | Comma-separated allowed origins |
| `OLLAMA_MODEL` | ❌ | `llama3` | Ollama model name |
| `GOOGLE_MODEL` | ❌ | `models/gemini-2.5-flash` | Gemini model |
| `MAX_UPLOAD_SIZE_MB` | ❌ | `10240` | Max file size in MB |
| `CODE_EXECUTION_TIMEOUT` | ❌ | `15` | Code sandbox timeout |
| `COOKIE_SECURE` | ❌ | `False` | Set `True` in production |
| `COOKIE_SAMESITE` | ❌ | `lax` | Cookie SameSite policy |
| `COOKIE_DOMAIN` | ❌ | `None` | Cookie Domain (for cross-subdomain) |

---

*End of backend.md*
