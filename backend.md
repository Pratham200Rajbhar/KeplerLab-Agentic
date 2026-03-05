# KeplerLab Backend — Complete Technical Documentation

> **Application:** KeplerLab AI Learning Platform  
> **Framework:** FastAPI 0.115.6  
> **Python:** 3.11+  
> **Last Updated:** March 2026

---

## Table of Contents

1. [Overview](#1-overview)
2. [Project Directory Structure](#2-project-directory-structure)
3. [Technology Stack](#3-technology-stack)
4. [Architecture Overview](#4-architecture-overview)
5. [Database Schema (PostgreSQL + Prisma)](#5-database-schema)
6. [Application Startup & Lifespan](#6-application-startup--lifespan)
7. [Middleware Stack](#7-middleware-stack)
8. [Configuration System](#8-configuration-system)
9. [Authentication System](#9-authentication-system)
10. [API Routes — Complete Reference](#10-api-routes)
11. [Feature Flows — End to End](#11-feature-flows)
    - 11.1 [Material Upload & Processing](#111-material-upload--processing)
    - 11.2 [RAG Chat](#112-rag-chat)
    - 11.3 [Code Execution Mode (/code)](#113-code-execution-mode)
    - 11.4 [Web Search Mode (/web)](#114-web-search-mode)
    - 11.5 [Deep Research Mode (/research)](#115-deep-research-mode)
    - 11.6 [Agent Mode (/agent)](#116-agent-mode)
    - 11.7 [Flashcard Generation](#117-flashcard-generation)
    - 11.8 [Quiz Generation](#118-quiz-generation)
    - 11.9 [Presentation (PPT) Generation](#119-presentation-ppt-generation)
    - 11.10 [Mind Map Generation](#1110-mind-map-generation)
    - 11.11 [Podcast Feature](#1111-podcast-feature)
    - 11.12 [Explainer Video Generation](#1112-explainer-video-generation)
    - 11.13 [Notebook Management](#1113-notebook-management)
12. [Service Layer — Detailed Reference](#12-service-layer)
13. [RAG Pipeline — Deep Dive](#13-rag-pipeline)
14. [LLM Service](#14-llm-service)
15. [Background Job Worker](#15-background-job-worker)
16. [WebSocket Manager](#16-websocket-manager)
17. [Vector Database (ChromaDB)](#17-vector-database-chromadb)
18. [Storage Service](#18-storage-service)
19. [Security & Validation](#19-security--validation)
20. [Logging & Monitoring](#20-logging--monitoring)
21. [CLI Tools](#21-cli-tools)
22. [Environment Variables Reference](#22-environment-variables-reference)

---

## 1. Overview

KeplerLab is an AI-powered learning platform backend built on FastAPI. It provides:

- **Notebook workspace** — users organize materials (PDFs, URLs, YouTube, text, code) into named notebooks
- **RAG Chat** — retrieval-augmented generation over uploaded materials
- **Multi-modal AI** — flashcards, quizzes, presentations, mindmaps, podcasts, explainer videos
- **Agentic AI** — multi-step autonomous task execution, Python sandbox, web research
- **Real-time features** — WebSocket-based material processing status, podcast playback
- **Multi-provider LLM** — Ollama (local), Google Gemini, NVIDIA NIM, MyOpenLM

The API serves a Next.js 16 frontend and runs as a single FastAPI process with a background async job processor.

---

## 2. Project Directory Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI app, lifespan, middleware, routers
│   ├── core/
│   │   ├── config.py              # Pydantic BaseSettings — all env vars
│   │   └── utils.py               # Shared utilities
│   ├── db/
│   │   ├── prisma_client.py       # Prisma singleton (PostgreSQL ORM)
│   │   └── chroma.py              # ChromaDB persistent client + collection
│   ├── models/
│   │   ├── mindmap_schemas.py     # MindMap Pydantic models
│   │   ├── model_schemas.py       # LLM model metadata
│   │   └── shared_enums.py        # IntentOverride, DifficultyLevel enums
│   ├── prompts/                   # Plaintext prompt templates (*.txt)
│   │   ├── chat_prompt.txt
│   │   ├── flashcard_prompt.txt
│   │   ├── quiz_prompt.txt
│   │   ├── mindmap_prompt.txt
│   │   ├── ppt_prompt.txt         # Stage 1: intent
│   │   ├── presentation_intent_prompt.txt
│   │   ├── presentation_strategy_prompt.txt
│   │   ├── slide_content_prompt.txt
│   │   ├── code_generation_prompt.txt
│   │   ├── code_repair_prompt.txt
│   │   ├── data_analysis_prompt.txt
│   │   ├── podcast_script_prompt.txt
│   │   ├── podcast_qa_prompt.txt
│   │   └── flashcard_prompt.txt
│   ├── routes/                    # FastAPI routers (one file per feature)
│   │   ├── auth.py                 GET /auth/me, POST /auth/signup|login|refresh|logout
│   │   ├── notebook.py             CRUD /notebooks + content store
│   │   ├── upload.py               POST /upload (file, url, youtube, text)
│   │   ├── materials.py            GET|PATCH|DELETE /materials
│   │   ├── chat.py                 POST /chat + sessions + suggestions
│   │   ├── flashcard.py            POST /flashcard
│   │   ├── quiz.py                 POST /quiz
│   │   ├── ppt.py                  POST /presentation
│   │   ├── mindmap.py              POST|GET|DELETE /mindmap
│   │   ├── podcast_live.py         /podcast/* (session, segments, QA, export)
│   │   ├── explainer.py            /explainer/* (check, generate, status, video)
│   │   ├── agent.py                POST /agent/execute-code, GET /workspace/file
│   │   ├── search.py               POST /search/web (bridges external search)
│   │   ├── proxy.py                GET /proxy/presentation/slides (image proxy)
│   │   ├── jobs.py                 GET /jobs/{id} (job polling)
│   │   ├── models.py               GET /models (LLM list)
│   │   ├── health.py               GET /health, /health/simple
│   │   ├── websocket_router.py     WS /ws/materials/{id}
│   │   └── utils.py                Shared route helpers
│   └── services/                  # Business logic (one subdir per domain)
│       ├── agent/                  pipeline.py, tools.py, schemas.py
│       ├── auth/                   service.py, security.py
│       ├── chat/                   service.py
│       ├── code_execution/         sandbox.py, sandbox_env.py, security.py
│       ├── explainer/              processor.py, script_generator.py, tts.py, video_composer.py
│       ├── flashcard/              generator.py
│       ├── llm_service/            llm.py, llm_schemas.py, structured_invoker.py
│       ├── mindmap/                generator.py
│       ├── podcast/                session_manager.py, script_generator.py, tts_service.py,
│       │                           qa_service.py, satisfaction_detector.py, export_service.py, voice_map.py
│       ├── ppt/                    generator.py, screenshot_service.py, slide_extractor.py
│       ├── quiz/                   generator.py
│       ├── rag/                    pipeline.py, embedder.py, reranker.py,
│       │                           context_builder.py, context_formatter.py,
│       │                           citation_validator.py, secure_retriever.py
│       ├── research/               pipeline.py
│       ├── text_processing/        file_detector.py (+ text extractors)
│       ├── audit_logger.py         API usage logging to DB
│       ├── file_validator.py       Upload MIME/size validation
│       ├── gpu_manager.py          GPU memory management
│       ├── job_service.py          Background job CRUD
│       ├── material_service.py     Material CRUD + processing dispatch
│       ├── model_manager.py        Model registry
│       ├── notebook_name_generator.py  AI-generated notebook names
│       ├── notebook_service.py     Notebook + content CRUD
│       ├── performance_logger.py   Request timing middleware
│       ├── rate_limiter.py         Rate limit middleware (disabled)
│       ├── storage_service.py      Local file storage for material text
│       ├── token_counter.py        LLM token counting/tracking
│       ├── worker.py               Async background job processor
│       └── ws_manager.py           WebSocket connection manager
├── cli/                           # One-off maintenance scripts
│   ├── backup_chroma.py
│   ├── download_models.py
│   ├── export_embeddings.py
│   ├── import_embeddings.py
│   ├── migrate_material_joins.py
│   └── reindex.py
├── data/
│   ├── chroma/                    ChromaDB persistent storage
│   ├── material_text/             Extracted material text files ({uuid}.txt)
│   ├── models/                    Local sentence-transformer model cache
│   ├── uploads/                   Raw uploaded files
│   ├── output/                    Generated output files
│   └── workspaces/                Per-session code sandbox directories
├── logs/                          Rotating log files (app.log)
├── output/
│   ├── explainers/                Explainer MP4 videos
│   ├── generated/                 Generated files (CSV exports, etc.)
│   ├── podcast/                   Podcast MP3 audio segments
│   └── presentations/             Generated HTML presentations
├── prisma/
│   └── schema.prisma              Complete Prisma schema
├── templates/                     PPT HTML templates
└── requirements.txt
```

---

## 3. Technology Stack

| Layer | Technology |
|-------|-----------|
| Web Framework | FastAPI 0.115.6 |
| ASGI Server | Uvicorn 0.30.6 |
| ORM | Prisma 0.15.0 (prisma-client-py, asyncio) |
| Database | PostgreSQL |
| Vector DB | ChromaDB ≥0.5.11, <0.6.0 |
| Embeddings | BAAI/bge-m3 (1024-dim) via sentence-transformers |
| Reranker | BAAI/bge-reranker-large |
| LLM Orchestration | LangChain 0.2.16 + LangGraph ≥0.2.0 |
| LLM Providers | Ollama (llama3), Google Gemini 2.5 Flash, NVIDIA Qwen, MyOpenLM |
| PDF Extraction | PyMuPDF, pypdf, pdfplumber |
| OCR | pytesseract, EasyOCR |
| Audio/TTS | edge-tts, pydub, soundfile |
| Transcription | OpenAI Whisper |
| Video | ffmpeg-python |
| Auth | python-jose (JWT), passlib/bcrypt |
| HTTP Client | httpx |
| Web Scraping | beautifulsoup4, selenium, trafilatura, yt-dlp |
| Data | numpy, pyarrow, pandas (implicit via polars) |
| Validation | Pydantic v2 |
| Config | pydantic-settings |
| Testing | pytest, pytest-asyncio |

---

## 4. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Next.js Frontend                        │
│          (HTTP REST + Server-Sent Events + WebSocket)        │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP / WS
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                        │
│                                                              │
│  Middleware Stack (in order):                                │
│  ① PerformanceMonitoring → ② RateLimit → ③ RequestLogger   │
│  ④ CORSMiddleware → ⑤ TrustedHost (prod)                   │
│                                                              │
│  Routers (18 total):                                         │
│  auth | notebook | upload | materials | chat | flashcard    │
│  quiz | ppt | mindmap | podcast | explainer | agent         │
│  search | proxy | jobs | models | health | ws               │
└───────────┬──────────────────────────────────────┬──────────┘
            │                                      │
     ┌──────▼──────┐                    ┌──────────▼────────┐
     │  Services   │                    │  Background Worker │
     │  Layer      │                    │  (asyncio.Task)    │
     └──────┬──────┘                    └──────────┬────────┘
            │                                      │
     ┌──────┴──────────────────────────────────────┘
     │
     ├── PostgreSQL (via Prisma)     [Users, Notebooks, Materials, Sessions...]
     ├── ChromaDB                    [Vector embeddings — BAAI/bge-m3 1024d]
     ├── Local Filesystem            [Uploaded files, material text, outputs]
     └── External                    [LLM providers, Search service, Sandbox]
```

### Key Design Decisions

- **No request-level LLM intent classification** — intent is always set explicitly by the frontend via slash commands (`IntentOverride` enum). Backend never guesses.
- **Single background worker** — one `asyncio.Task` processes the job queue sequentially (up to 5 concurrent material extractions). Gracefully shuts down with 30s timeout.
- **Event-driven job queue** — instead of polling, the worker uses an asyncio `Event` notified immediately on new job creation.
- **Token rotation auth** — refresh tokens stored hashed in DB, rotated on every use. Reuse detection kicks the user out of all sessions.
- **Sticky embedding version** — ChromaDB is wiped and rebuilt if `EMBEDDING_VERSION` changes, preventing dimension mismatches.
- **SSE streaming** — all chat, agent, code-execution responses are streamed via `StreamingResponse` with SSE format.

---

## 5. Database Schema

Complete PostgreSQL schema managed by Prisma ORM. 20 models total.

### Enums

| Enum | Values |
|------|--------|
| `UserRole` | `USER`, `ADMIN` |
| `MaterialStatus` | `pending`, `processing`, `ocr_running`, `transcribing`, `embedding`, `completed`, `failed` |
| `JobStatus` | `pending`, `processing`, `ocr_running`, `transcribing`, `embedding`, `completed`, `failed` |
| `VideoStatus` | `pending`, `processing`, `completed`, `failed` |
| `ExportStatus` | `pending`, `processing`, `completed`, `failed` |
| `PodcastSessionStatus` | `created`, `script_generating`, `audio_generating`, `ready`, `playing`, `paused`, `completed`, `failed` |

### Core Models

#### `User`
```
id             UUID (PK)
email          VARCHAR(255) UNIQUE
username       VARCHAR(100)
hashedPassword VARCHAR(255)
isActive       BOOLEAN DEFAULT true
role           UserRole DEFAULT USER
deletedAt      TIMESTAMP?
createdAt      TIMESTAMP
updatedAt      TIMESTAMP
```
Relations → Notebook[], Material[], ChatSession[], ChatMessage[], GeneratedContent[], RefreshToken[], BackgroundJob[], UserTokenUsage[], ApiUsageLog[], AgentExecutionLog[], CodeExecutionSession[], ResearchSession[], ExplainerVideo[], PodcastSession[], Artifact[]

#### `Notebook`
```
id          UUID (PK)
userId      UUID (FK → User, CASCADE)
name        VARCHAR(255)
description TEXT?
createdAt   TIMESTAMP
updatedAt   TIMESTAMP
```

#### `Material`
```
id           UUID (PK)
userId       UUID (FK → User)
notebookId   UUID? (FK → Notebook)
filename     VARCHAR(255)
title        VARCHAR(510)?        -- Custom title for URL/YouTube materials
originalText TEXT?                -- Extracted text stored in DB (legacy)
status       MaterialStatus
chunkCount   INT DEFAULT 0
sourceType   VARCHAR(50)?         -- 'file', 'url', 'youtube', 'text'
metadata     JSON?                -- Extraction metadata
error        TEXT?
```

#### `ChatSession`
```
id         UUID (PK)
notebookId UUID (FK → Notebook)
userId     UUID (FK → User)
title      VARCHAR(255) DEFAULT 'New Chat'
```

#### `ChatMessage`
```
id            UUID (PK)
notebookId    UUID
userId        UUID
chatSessionId UUID?
role          VARCHAR(20)     -- 'user' or 'assistant'
content       TEXT
agentMeta     TEXT?           -- JSON: intent, tools_used, step_log, etc.
```
→ has ResponseBlock[] (paragraph-level blocks) and Artifact[]

#### `GeneratedContent`
```
id          UUID (PK)
notebookId  UUID
userId      UUID
materialId  UUID?           -- legacy single-material link
contentType VARCHAR(50)     -- 'flashcard', 'quiz', 'presentation', 'mindmap'
title       VARCHAR(255)?
data        JSON            -- full generated content
language    VARCHAR(10)?
materialIds STRING[]        -- legacy array
```
M2M join → `GeneratedContentMaterial` (generatedContentId, materialId)

#### `RefreshToken`
```
id        UUID (PK)
userId    UUID
tokenHash VARCHAR(255) UNIQUE
family    VARCHAR(255)    -- Token rotation family ID
used      BOOLEAN DEFAULT false
expiresAt TIMESTAMP
```

#### `BackgroundJob`
```
id      UUID (PK)
userId  UUID
jobType VARCHAR(50)     -- 'material_processing', 'url_processing', 'youtube_processing', 'text_processing'
status  JobStatus
result  JSON?
error   TEXT?
```

#### `UserTokenUsage`
```
id         UUID (PK)
userId     UUID
date       DATE
tokensUsed INT DEFAULT 0
```
Unique constraint on (userId, date) — daily token tracking.

#### `ApiUsageLog`
```
id                 UUID
userId             UUID
endpoint           VARCHAR(255)
materialIds        STRING[]
contextTokenCount  INT
responseTokenCount INT
modelUsed          VARCHAR(100)
llmLatency         FLOAT
retrievalLatency   FLOAT
totalLatency       FLOAT
```

#### `AgentExecutionLog`
```
id          UUID
userId      UUID
notebookId  UUID
intent      VARCHAR(50)
confidence  FLOAT
toolsUsed   STRING[]
stepsCount  INT
tokensUsed  INT
elapsedTime FLOAT
```

#### `CodeExecutionSession`
```
id          UUID
userId      UUID
notebookId  UUID
code        TEXT
stdout      TEXT?
stderr      TEXT?
exitCode    INT DEFAULT -1
hasChart    BOOLEAN
elapsedTime FLOAT
```

#### `ResearchSession`
```
id           UUID
userId       UUID
notebookId   UUID
query        TEXT
report       TEXT?
sourcesCount INT
queriesCount INT
iterations   INT
elapsedTime  FLOAT
sourceUrls   STRING[]
```

#### `ExplainerVideo`
```
id                UUID
userId            UUID
presentationId    UUID (FK → GeneratedContent)
pptLanguage       VARCHAR(10)
narrationLanguage VARCHAR(10)
voiceGender       VARCHAR(10)
voiceId           VARCHAR(100)
status            VideoStatus
script            JSON?         -- Array of slide narration scripts
audioFiles        JSON?
videoUrl          TEXT?
duration          INT?
chapters          JSON?
```

#### Podcast Models
- `PodcastSession` — session config + state (mode, language, voices, status, chapters, totalDurationMs)
- `PodcastSessionMaterial` — M2M join (sessions ↔ materials)
- `PodcastSegment` — individual host/guest dialogue segment (text + audioUrl + durationMs)
- `PodcastDoubt` — user-submitted question mid-playback (question + answer text + audio URLs)
- `PodcastExport` — export requests (PDF or JSON)
- `PodcastBookmark` — segment bookmarks with optional label
- `PodcastAnnotation` — text notes attached to a segment

#### `Artifact`
```
id            UUID
userId        UUID
notebookId    UUID?
sessionId     UUID?
messageId     UUID?
filename      VARCHAR(255)
mimeType      VARCHAR(128)
displayType   VARCHAR(50)?    -- 'chart', 'table', 'csv', 'text'
sizeBytes     INT
downloadToken VARCHAR(64) UNIQUE
tokenExpiry   TIMESTAMP      -- 24-hour expiry default
workspacePath TEXT           -- absolute path on disk
sourceCode    TEXT?
```

#### `ResponseBlock`
```
id            UUID
chatMessageId UUID
blockIndex    INT
text          TEXT
```
Stores individual paragraph blocks of AI responses for hover-menu interactions.

---

## 6. Application Startup & Lifespan

The `lifespan` async context manager in `main.py` performs these steps in order on **startup**:

1. **Connect to PostgreSQL** via Prisma (`connect_db()`)
2. **Warm up embedding model** `BAAI/bge-m3` in thread pool executor (non-blocking)
3. **Preload reranker** `BAAI/bge-reranker-large` in thread pool executor
4. **Start background job processor** as `asyncio.Task` named `job_processor`
5. **Ensure sandbox packages** installed (seaborn, wordcloud, etc.)
6. **Clean up stale sandbox temp dirs** from previous crashes (`/tmp/kepler_sandbox_*`, `/tmp/kepler_analysis_*`)
7. **Ensure output directories** exist (`output/generated`, `output/presentations`, `output/explainers`, `output/podcast`)
8. **Purge expired refresh tokens** from DB

On **shutdown**:
1. Signal graceful shutdown to worker
2. Cancel `_job_processor_task` and wait up to 30s
3. `disconnect_db()`

---

## 7. Middleware Stack

Applied in order (first to last around the request):

| Order | Middleware | Purpose |
|-------|-----------|---------|
| 1 | `performance_monitoring_middleware` | Records full request time, logs slow requests |
| 2 | `rate_limit_middleware` | **Currently disabled** — passes all requests through |
| 3 | `log_requests` | Logs `METHOD /path STATUS time [request_id]`, adds `X-Request-ID` header |
| 4 | `CORSMiddleware` | Allows configured origins, credentials, all methods/headers |
| 5 | `TrustedHostMiddleware` | Production only — validates `Host` header against CORS domains |

Global error handlers ensure CORS headers are included even on exception responses:
- `HTTPException` handler → returns `JSONResponse` with proper CORS headers
- `Exception` handler → logs unhandled exceptions, returns 500 with `request_id`

---

## 8. Configuration System

`app/core/config.py` — Pydantic `BaseSettings` loaded from `.env` file.

### Key Configuration Sections

| Section | Variables | Notes |
|---------|-----------|-------|
| Environment | `ENVIRONMENT`, `DEBUG` | `development` / `staging` / `production` |
| Database | `DATABASE_URL` | Required |
| ChromaDB | `CHROMA_DIR` | Default `./data/chroma` |
| File Storage | `UPLOAD_DIR`, `MAX_UPLOAD_SIZE_MB` | 10 GB default |
| Output Dirs | `PRESENTATIONS_OUTPUT_DIR`, `GENERATED_OUTPUT_DIR`, `TEMPLATES_DIR` | |
| Code Execution | `MAX_CODE_REPAIR_ATTEMPTS` (3), `CODE_EXECUTION_TIMEOUT` (15s) | |
| Workspace | `WORKSPACE_BASE_DIR`, `WORKSPACE_IDLE_TTL_MINUTES` (30), `WORKSPACE_MEMORY_MB` (512) | |
| JWT | `JWT_SECRET_KEY` (required), `ACCESS_TOKEN_EXPIRE_MINUTES` (15), `REFRESH_TOKEN_EXPIRE_DAYS` (7) | |
| Cookies | `COOKIE_SECURE`, `COOKIE_SAMESITE`, `COOKIE_DOMAIN`, `COOKIE_NAME` | Auto-secure in production |
| CORS | `CORS_ORIGINS` | Comma-separated string or list |
| LLM | `LLM_PROVIDER`, `OLLAMA_MODEL`, `GOOGLE_MODEL`, `NVIDIA_MODEL` | Provider selection |
| API Keys | `GOOGLE_API_KEY`, `NVIDIA_API_KEY` | Required per-provider |
| LLM Params | `LLM_TEMPERATURE_STRUCTURED` (0.1), `LLM_TEMPERATURE_CHAT` (0.2), `LLM_TEMPERATURE_CREATIVE` (0.7), `LLM_TEMPERATURE_CODE` (0.1) | |
| Tokens | `LLM_MAX_TOKENS` (4000), `LLM_MAX_TOKENS_CHAT` (3000) | |
| Embeddings | `EMBEDDING_MODEL` (BAAI/bge-m3), `EMBEDDING_VERSION`, `EMBEDDING_DIMENSION` (1024) | |
| Reranking | `RERANKER_MODEL` (BAAI/bge-reranker-large), `USE_RERANKER` (true) | |
| Retrieval | `INITIAL_VECTOR_K` (10), `MMR_K` (8), `FINAL_K` (10), `MMR_LAMBDA` (0.5), `MAX_CONTEXT_TOKENS` (6000) | |
| Thresholds | `MIN_SIMILARITY_SCORE` (0.3), `MIN_CHUNK_LENGTH` (100), `MIN_CONTEXT_CHUNK_LENGTH` (150) | |
| Timeouts | `OCR_TIMEOUT_SECONDS` (300), `WHISPER_TIMEOUT_SECONDS` (600), `LIBREOFFICE_TIMEOUT_SECONDS` (120) | |
| Search | `SEARCH_SERVICE_URL` | External search microservice |

All relative paths are resolved to absolute at validation time against the project root.
`COOKIE_SECURE` is auto-set to `True` in production.

---

## 9. Authentication System

Located in `app/services/auth/` (service.py + security.py) and `app/routes/auth.py`.

### Flow

```
POST /auth/signup
  → Validate email/username/password (min 8 chars, 1 upper, 1 lower, 1 digit)
  → Hash password with bcrypt
  → Create User record in DB
  → Return UserResponse

POST /auth/login
  → Authenticate credentials
  → Generate UUID token family
  → Create access_token (JWT, 15 min expiry)
  → Create refresh_token (JWT, 7-day expiry, includes family claim)
  → Store SHA-256 hash of refresh_token in RefreshToken table
  → Set refresh_token as HttpOnly cookie (path="/")
  → Return { access_token, token_type }

POST /auth/refresh (called by frontend auto-refresh)
  → Read refresh_token from cookie
  → Look up token hash in RefreshToken table
  → Verify not expired, not already used
  → If token was already used → REUSE DETECTED → revoke entire family → 401
  → Mark old token as used
  → Create new access_token + new refresh_token (same family)
  → Store new refresh_token hash
  → Set new cookie
  → Return new access_token

GET /auth/me
  → Validate Bearer access_token from Authorization header
  → Return current user info

POST /auth/logout
  → Revoke ALL refresh tokens for user
  → Clear cookie

App startup
  → cleanup_expired_tokens() — deletes expired rows from DB
```

### Token Details
- **Access Token**: JWT signed with `JWT_SECRET_KEY`, algorithm `HS256`, 15-minute expiry, payload `{"sub": user_id}`
- **Refresh Token**: JWT with 7-day expiry, includes `family` claim for rotation tracking
- **Storage**: Only SHA-256 hash stored in DB (never plaintext)
- **Rotation**: Every refresh rotates the token. Reuse detection by checking `used` flag.

### Route Protection
All protected routes use `Depends(get_current_user)` which:
1. Extracts `Authorization: Bearer <token>` header
2. Decodes JWT and extracts `sub` (user ID)
3. Fetches user from DB and verifies `isActive`
4. Returns the `User` model

---

## 10. API Routes

### Public Routes (no auth required)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Full health check (DB, ChromaDB, LLM) |
| `GET` | `/health/simple` | Basic uptime check |
| `POST` | `/auth/signup` | Register new user |
| `POST` | `/auth/login` | Login, set refresh cookie |
| `POST` | `/auth/refresh` | Rotate refresh token |
| `GET` | `/models` | List available LLM models |

### Protected Routes (Bearer token required)

#### Auth
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/auth/me` | Get current user |
| `POST` | `/auth/logout` | Revoke tokens, clear cookie |

#### Notebooks
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/notebooks` | Create notebook |
| `GET` | `/notebooks` | List user notebooks (skip/take pagination) |
| `GET` | `/notebooks/{id}` | Get single notebook |
| `PATCH` | `/notebooks/{id}` | Update name/description |
| `DELETE` | `/notebooks/{id}` | Delete notebook + all content (cascade) |
| `POST` | `/notebooks/{id}/content` | Save generated content to notebook |
| `GET` | `/notebooks/{id}/content` | Get notebook saved content |
| `DELETE` | `/notebooks/{id}/content/{content_id}` | Delete saved content item |

#### Upload
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/upload` | Upload file (PDF, DOCX, PPTX, XLSX, CSV, TXT, audio, video, image) |
| `POST` | `/upload/url` | Ingest web URL |
| `POST` | `/upload/youtube` | Ingest YouTube video (transcript or Whisper) |
| `POST` | `/upload/text` | Save raw text as material |

#### Materials
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/materials` | List materials (optional `?notebook_id=`) |
| `PATCH` | `/materials/{id}` | Update filename or title |
| `DELETE` | `/materials/{id}` | Delete material + embeddings |
| `GET` | `/materials/{id}/text` | Get full extracted text |

#### Chat
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/chat` | Send chat message (SSE stream or JSON) |
| `GET` | `/chat/sessions` | List chat sessions for notebook |
| `POST` | `/chat/sessions` | Create new chat session |
| `DELETE` | `/chat/sessions/{id}` | Delete session + messages |
| `GET` | `/chat/sessions/{id}/messages` | Load session history |
| `POST` | `/chat/block-followup` | Follow-up on a specific response block |
| `POST` | `/chat/suggestions` | Get input suggestions from partial text |

#### Generation
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/flashcard` | Generate flashcards |
| `POST` | `/quiz` | Generate MCQ quiz |
| `POST` | `/presentation` | Generate HTML presentation |
| `POST` | `/mindmap` | Generate mind map |
| `GET` | `/mindmap/{notebook_id}` | Get saved mind map |
| `DELETE` | `/mindmap/{id}` | Delete mind map |

#### Podcast
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/podcast/session` | Create podcast session |
| `POST` | `/podcast/session/{id}/generate` | Start script + audio generation |
| `GET` | `/podcast/session/{id}` | Get session state |
| `GET` | `/podcast/sessions` | List user sessions |
| `PATCH` | `/podcast/session/{id}` | Update title/tags/current_segment |
| `DELETE` | `/podcast/session/{id}` | Delete session |
| `GET` | `/podcast/session/{id}/segments` | Get all audio segments |
| `GET` | `/podcast/audio/{session_id}/{index}` | Stream MP3 audio segment |
| `POST` | `/podcast/session/{id}/doubt` | Submit a question (interrupt) |
| `GET` | `/podcast/session/{id}/doubts` | Get Q&A history |
| `POST` | `/podcast/session/{id}/bookmark` | Add bookmark |
| `POST` | `/podcast/session/{id}/annotation` | Add annotation |
| `POST` | `/podcast/session/{id}/export` | Export PDF/JSON |
| `GET` | `/podcast/export/{id}/file` | Download export |
| `GET` | `/podcast/voices` | List available TTS voices by language |
| `POST` | `/podcast/voices/preview` | Generate voice preview audio |

#### Explainer
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/explainer/check-presentations` | Find existing PPTs for materials |
| `POST` | `/explainer/generate` | Start explainer video generation |
| `GET` | `/explainer/{id}/status` | Poll generation progress |
| `GET` | `/explainer/{id}/video` | Download finished MP4 |

#### Agent / Code
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/agent/execute-code` | Execute code in sandbox (SSE stream) |
| `GET` | `/workspace/file/{id}` | Serve artifact file with token auth |

#### Utilities
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/search/web` | Bridge to external search service |
| `GET` | `/proxy/presentation/slides/{path}` | Image proxy for presentation slides |
| `GET` | `/jobs/{id}` | Poll background job status |

#### WebSocket
| Method | Path | Description |
|--------|------|-------------|
| `WS` | `/ws/materials/{material_id}` | Real-time material processing status |

---

## 11. Feature Flows

### 11.1 Material Upload & Processing

**Supported source types:** file, URL, YouTube, text

#### File Upload Flow
```
POST /upload
Body: multipart/form-data { file, notebook_id? }

1. FileValidator validates MIME type and extension
2. Sanitize filename (strip dangerous chars)
3. Save raw file to data/uploads/{uuid}_{filename}
4. Create Material record in DB with status=pending
5. Create BackgroundJob (type=material_processing) in DB
6. Notify job queue event → worker wakes up immediately
7. Return { material_id, status: "pending" }

Background Worker picks up job:
1. status → processing
2. Detect file type (FileTypeDetector)
3. Extract text:
   - PDF: PyMuPDF → pdfplumber (tables) → OCR fallback (pytesseract/EasyOCR)
   - DOCX: python-docx
   - PPTX: python-pptx (text extraction)
   - XLSX/CSV: openpyxl/xlrd (tabular to text)
   - TXT/MD: direct UTF-8
   - Audio (MP3/WAV/M4A): Whisper transcription
   - Video (MP4): extract audio → Whisper
   - Image (JPG/PNG): OCR via EasyOCR
4. status → ocr_running (if OCR needed)
5. status → transcribing (if Whisper needed)
6. status → embedding
7. Save full text to data/material_text/{uuid}.txt (StorageService)
8. Chunk text:
   - langchain RecursiveCharacterTextSplitter
   - chunk_overlap = CHUNK_OVERLAP_TOKENS (150)
   - Min chunk length: MIN_CHUNK_LENGTH (100 chars)
9. Generate embeddings for all chunks (BAAI/bge-m3)
10. Upsert into ChromaDB collection
11. Update Material.chunkCount
12. status → completed
13. WebSocket push to all clients watching this material

Error handling: status → failed, error message stored in Material.error
```

#### URL Upload Flow
```
POST /upload/url
Body: { url, notebook_id?, title? }

1. Validate URL format
2. Create Material (sourceType='url')
3. Create BackgroundJob (type=url_processing)

Worker:
1. Fetch page content (httpx + trafilatura for text extraction)
2. Fall back to BeautifulSoup if trafilatura fails
3. Continue with embedding pipeline (same as file)
```

#### YouTube Upload Flow
```
POST /upload/youtube
Body: { url, notebook_id? }

Worker:
1. Extract video ID from URL (yt-dlp)
2. Try youtube_transcript_api for existing transcript
3. Fall back: yt-dlp → download audio → Whisper transcription
4. status → transcribing during Whisper
5. Continue with embedding pipeline
```

#### Text Upload Flow
```
POST /upload/text
Body: { text, title, notebook_id? }

Worker:
1. Directly tokenize/chunk provided text
2. Embed and store in ChromaDB
```

---

### 11.2 RAG Chat

Intent: no slash command (default path)

```
POST /chat
Body: { message, material_ids[], notebook_id, session_id?, stream? }

1. Resolve material IDs (material_ids or material_id)
2. Validate all materials belong to user
3. Filter to only completed materials
4. Find or create ChatSession (auto-title from first message)
5. Save user ChatMessage to DB
6. Call chat_service.get_response():

   RAG Pipeline (rag/pipeline.py):
   ┌─ Retrieval Phase ─────────────────────────────────────────┐
   │ a. Embed query (BAAI/bge-m3)                               │
   │ b. ChromaDB initial similarity search → INITIAL_VECTOR_K=10│
   │ c. Filter: skip chunks < MIN_SIMILARITY_SCORE (0.3)        │
   │ d. MMR (Maximal Marginal Relevance) re-rank → MMR_K=8      │
   │ e. Reranker (bge-reranker-large) cross-encoder scoring     │
   │ f. Final top-k → FINAL_K=10                               │
   │ g. Token budget trim → MAX_CONTEXT_TOKENS=6000            │
   └───────────────────────────────────────────────────────────┘
   ┌─ Context Building ─────────────────────────────────────────┐
   │ a. Format chunks with material names and page numbers      │
   │ b. Citation validator — validate citation indices           │
   │ c. Build context string with source attribution            │
   └───────────────────────────────────────────────────────────┘
   ┌─ Generation Phase ─────────────────────────────────────────┐
   │ a. Load prompt from chat_prompt.txt                        │
   │ b. Build message array: [system, ...history, human]        │
   │ c. LLM.stream() → token chunks                            │
   │ d. Parse [n] citation markers in response                  │
   │ e. Map citations to material metadata                      │
   └───────────────────────────────────────────────────────────┘

7. SSE stream format:
   data: {"type": "token", "content": "..."}
   data: {"type": "citations", "citations": [...]}
   data: {"type": "done"}

8. Save assistant ChatMessage + ResponseBlocks to DB
9. Log ApiUsageLog (tokens, latency, model)
10. Track UserTokenUsage (daily aggregate)
```

---

### 11.3 Code Execution Mode

Intent: `CODE_EXECUTION` (set by `/code` slash command)

**Phase 1 — Code Generation (via POST /chat):**
```
1. LLM receives message with code_generation_prompt.txt
2. Returns Python code (not executed yet)
3. SSE stream: sends code to frontend via "code" type events
4. Frontend shows code in CodePanel (Monaco-like editor)
5. User can edit code before running
```

**Phase 2 — Code Execution (POST /agent/execute-code):**
```
1. Code received from frontend
2. SecurityValidator scans code:
   - Checks for forbidden imports (os.system, subprocess, socket, etc.)
   - Checks for dangerous patterns (__import__, exec, eval of untrusted input)
   - Returns violations list
3. If not safe → SSE "execution_blocked" event
4. sanitize_code() — removes obviously malicious tokens
5. Create temp directory: /tmp/kepler_code_{uuid}

Sandbox Execution (code_execution/sandbox.py):
   - Write code to {work_dir}/code.py
   - Run in subprocess with timeout
   - Capture stdout, stderr, exit_code
   - Detect output files (plots, CSVs, charts)

6. If ModuleNotFoundError & module in APPROVED_ON_DEMAND:
   → pip install the package
   → retry execution

7. If exit_code != 0 (error):
   → Send to LLM with code_repair_prompt.txt
   → Attempt auto-repair (up to MAX_CODE_REPAIR_ATTEMPTS=3)
   → If repaired → re-execute

8. SSE events:
   "execution_start" → "stdout" → "stderr" → "chart" (base64 PNG) → "done"

9. Detect and register output artifacts:
   - PNG/JPEG charts → displayType='chart'
   - CSV files → displayType='table'
   - Other files → generic artifact

10. Save CodeExecutionSession to DB
11. Register Artifact records with downloadToken (24h expiry)
```

---

### 11.4 Web Search Mode

Intent: `WEB_SEARCH` (set by `/web` slash command)

```
POST /chat (intent_override: WEB_SEARCH)

1. Extract query from message
2. POST to search service (SEARCH_SERVICE_URL/api/search)
   - Returns organic_results[]: {title, link, snippet}
3. Build context from top search results (titles + snippets + URLs)
4. LLM summarizes with web search context
5. SSE stream response with source URLs
6. Frontend displays WebSources component with clickable links
```

---

### 11.5 Deep Research Mode

Intent: `WEB_RESEARCH` (set by `/research` slash command)

```
POST /chat (intent_override: WEB_RESEARCH)

Research Pipeline (services/research/pipeline.py):
1. Query decomposition — LLM breaks query into sub-questions
2. For each sub-question:
   a. Web search (via search service)
   b. Fetch page content (httpx + trafilatura extraction)
   c. Extract relevant paragraphs
3. Iterative synthesis:
   a. Merge evidence from all sources
   b. LLM generates structured report with inline citations
4. Final report building:
   - Executive summary
   - Detailed sections
   - Citation list with URLs
5. SSE stream: progress events + final report
6. Save ResearchSession to DB (query, report, sourcesCount, sourceUrls, elapsedTime)
7. Frontend displays ResearchReport component with progress bar
```

---

### 11.6 Agent Mode

Intent: `AGENT` (set by `/agent` slash command)

```
POST /chat (intent_override: AGENT)

Agent Pipeline (services/agent/pipeline.py):
Uses LangGraph for multi-step tool orchestration.

Available tools (services/agent/tools.py):
  - rag_search: Search materials with vector retrieval
  - web_search: Quick web lookup
  - run_code: Execute Python in sandbox
  - read_artifact: Read previously generated artifact
  - create_chart: Generate matplotlib/seaborn chart
  - write_file: Save output to workspace

Tool call loop:
1. LLM decides next action (ReAct: Reasoning + Acting)
2. Execute tool
3. Feed tool result back to LLM
4. Loop until LLM returns final_answer
5. Each step streamed as SSE event:
   "agent_step" → {"tool": "...", "input": "...", "output": "..."}

6. Final response streamed
7. Save AgentExecutionLog (intent, tools_used, stepsCount, tokensUsed, elapsedTime)
8. Any artifacts registered with download tokens
```

---

### 11.7 Flashcard Generation

```
POST /flashcard
Body: { material_ids[], topic?, card_count?, difficulty, additional_instructions? }

1. Load material text (single or combined)
2. If topic provided → prepend "Focus on topic: {topic}"
3. Run flashcard/generator.py in thread pool executor
4. LLM called with flashcard_prompt.txt
5. Structured JSON output:
   { flashcards: [{ front, back, source? }] }
6. Return JSON directly (no DB persistence of individual cards)
   The frontend saves to notebook via POST /notebooks/{id}/content

Difficulty levels: easy | medium | hard
Max cards: 150
```

---

### 11.8 Quiz Generation

```
POST /quiz
Body: { material_ids[], topic?, mcq_count=10, difficulty, additional_instructions? }

1. Load material text
2. Run quiz/generator.py in thread pool executor
3. LLM called with quiz_prompt.txt
4. Structured JSON output:
   { questions: [{ question, options: [A,B,C,D], correct_answer, explanation }] }
5. Return JSON

Max questions: 150
```

---

### 11.9 Presentation (PPT) Generation

```
POST /presentation
Body: { material_ids[], max_slides?, theme?, additional_instructions? }

Multi-stage generation (services/ppt/generator.py):

Stage 1 — Intent Analysis:
  LLM + presentation_intent_prompt.txt
  Output: { title, audience, key_themes[], tone, language }

Stage 2 — Strategy Planning:
  LLM + presentation_strategy_prompt.txt
  Input: intent + material outline
  Output: { slide_plan: [{slide_title, key_points[], visual_suggestion}] }

Stage 3 — Slide Content Generation:
  LLM + slide_content_prompt.txt (per-slide batching)
  Output: full slide content with structured data

Stage 4 — HTML Rendering:
  Template engine renders slide data to HTML/CSS
  Each slide: title, bullets, optional visual

Returns:
  {
    title, slide_count,
    html: "<html>...</html>",   -- Full presentation HTML
    slides: [{title, content}],
    metadata: { theme, language, ... }
  }

Save to GeneratedContent (contentType='presentation')
```

---

### 11.10 Mind Map Generation

```
POST /mindmap
Body: { material_ids[], notebook_id }

1. Verify notebook belongs to user
2. Load material texts
3. LLM + mindmap_prompt.txt
4. Structured output:
   {
     nodes: [{id, label, type: 'root'|'branch'|'leaf'}],
     edges: [{source, target, label?}]
   }
5. Save to GeneratedContent (contentType='mindmap') in DB

GET /mindmap/{notebook_id}
  → Fetch latest GeneratedContent of type 'mindmap'
  → Returns nodes + edges + id

DELETE /mindmap/{id}
  → Delete GeneratedContent record

Frontend renders with @xyflow/react (React Flow) + dagre layout.
```

---

### 11.11 Podcast Feature

**Creation & Generation Flow:**
```
POST /podcast/session
Body: { notebook_id, mode, topic?, language, host_voice?, guest_voice?, material_ids[] }

Modes: overview | deep-dive | debate | q-and-a | full | topic

1. Validate material_ids ≥ 1
2. topic required for 'topic' or 'deep-dive' modes
3. Create PodcastSession record
4. If no voice specified → use language defaults from voice_map.py

POST /podcast/session/{id}/generate
1. status → script_generating
2. Load content from all linked materials
3. LLM + podcast_script_prompt.txt
   Output: [ { speaker: 'host'|'guest', text: "..." } ]
4. Save PodcastSegment records
5. status → audio_generating
6. edge-tts TTS generation:
   - One MP3 per segment using host_voice/guest_voice
   - Save to output/podcast/{session_id}/{index}.mp3
   - Update PodcastSegment.audioUrl + durationMs
7. Detect chapter boundaries — save to PodcastSession.chapters
8. Calculate totalDurationMs
9. status → ready
10. WebSocket push to all subscribed clients
```

**Playback:**
```
GET /podcast/audio/{session_id}/{index}
→ FileResponse for MP3 file

Frontend usePodcastPlayer hook:
- Manages AudioContext + segment queue
- Seamless crossfade between segments
- Updates currentSegment in session
- Sends PATCH /podcast/session/{id} on segment advance
```

**Q&A / Doubt Interruption:**
```
POST /podcast/session/{id}/doubt
Body: { question_text, paused_at_segment, question_audio_url? }

1. Create PodcastDoubt record
2. Load context from nearby podcast segments
3. LLM + podcast_qa_prompt.txt
4. Generate answer text
5. TTS → answer audio (same host/guest voice)
6. Save answer to PodcastDoubt
7. Return { answer_text, answer_audio_url }
```

**Export:**
```
POST /podcast/session/{id}/export
Body: { format: 'pdf' | 'json' }

PDF: fpdf2 → transcript + metadata
JSON: full session data dump

GET /podcast/export/{id}/file → Download
```

---

### 11.12 Explainer Video Generation

```
POST /explainer/check-presentations
Body: { material_ids[], notebook_id }
→ Find existing GeneratedContent presentations for these materials

POST /explainer/generate
Body: { material_ids[], notebook_id, ppt_language, narration_language, voice_gender, presentation_id?, create_new_ppt? }

1. Validate languages against EDGE_TTS_VOICES
2. Create ExplainerVideo record (status=pending)
3. Start background task (BackgroundTasks):

Explainer Processor (services/explainer/processor.py):
  
  Step 1 — Get or generate presentation:
    - If presentation_id → fetch existing SlideData from GeneratedContent
    - If create_new_ppt=True → call generate_presentation()
  
  Step 2 — Script generation (explainer/script_generator.py):
    - LLM generates narration for each slide
    - { slide: N, narration: "...", duration_hint: Xs }
  
  Step 3 — TTS audio (explainer/tts.py):
    - edge-tts voice selected by gender + language
    - Generate MP3 per slide narration
    - Save to output/explainers/
  
  Step 4 — Video composition (explainer/video_composer.py):
    - Screenshot each slide (screenshot_service.py)
    - ffmpeg: combine slide PNG + audio into MP4 clip per slide
    - Concatenate all clips into final MP4
    - Add fade transitions
  
  Step 5 — Save result:
    - Update ExplainerVideo.videoUrl, duration, chapters
    - status → completed

GET /explainer/{id}/status → { status, progress%, videoUrl? }
GET /explainer/{id}/video → FileResponse MP4
```

---

### 11.13 Notebook Management

```
POST /notebooks
Body: { name, description? }
→ Create Notebook record
→ AI generates name suggestions (notebook_name_generator.py)

GET /notebooks
→ Paginated list (skip/take)

GET /notebooks/{id}
→ Single notebook + metadata

PATCH /notebooks/{id}
→ Update name or description

DELETE /notebooks/{id}
→ Cascade delete: materials, chat sessions, generated content, jobs

POST /notebooks/{id}/content
→ Save generated content (flashcards, quizzes, etc.) to notebook
→ Stored as GeneratedContent in DB

GET /notebooks/{id}/content
→ List all saved content items (type, title, createdAt, data)

DELETE /notebooks/{id}/content/{content_id}
→ Remove specific saved content
```

---

## 12. Service Layer

### `services/auth/`
- **service.py**: `register_user`, `authenticate_user`, `get_current_user`, `create_access_token`, `create_refresh_token`, `store_refresh_token`, `validate_and_rotate_refresh_token`, `revoke_user_tokens`, `cleanup_expired_tokens`
- **security.py**: Password hashing (bcrypt), JWT encoding/decoding

### `services/rag/`
- **pipeline.py**: Full RAG pipeline — combines embedding, retrieval, reranking, context building, LLM generation
- **embedder.py**: BAAI/bge-m3 sentence-transformer — `warm_up_embeddings()`, `embed_texts()`, `embed_query()`
- **reranker.py**: BAAI/bge-reranker-large cross-encoder — `get_reranker()`, `rerank()`
- **secure_retriever.py**: ChromaDB query wrapper with user isolation (always filters by material_id)
- **context_builder.py**: Builds LLM-ready context string from retrieved chunks with metadata
- **context_formatter.py**: Formats chunks for different prompt types
- **citation_validator.py**: Validates and resolves `[n]` citation markers to source info

### `services/llm_service/`
- **llm.py**: LLM factory — `get_llm()`, `get_llm_structured()` with provider selection (Ollama/Google/NVIDIA/MyOpenLM). LRU cache (max 16 instances).
- **structured_invoker.py**: Calls LLM with retry logic and JSON parsing for structured outputs
- **llm_schemas.py**: Pydantic models for common LLM response shapes

### `services/material_service.py`
- `process_material_by_id(material_id)` — dispatches to correct extractor
- `process_url_material_by_id(material_id)` — URL fetch + extract
- `process_text_material_by_id(material_id)` — direct text
- `get_user_materials(user_id, notebook_id?)` — DB query
- `delete_material(material_id, user_id)` — deletes DB record + ChromaDB embeddings + text file
- `filter_completed_material_ids(ids, user_id)` — filters to only completed materials

### `services/worker.py`
- Single `asyncio.Task` running `job_processor()` loop
- Polls for `pending` jobs every 2 seconds (or woken by `_JobQueue.notify()`)
- Atomically claims jobs (`status → processing`)
- Dispatches to material/url/text processors
- Handles stuck job recovery on startup
- Supports up to 5 concurrent material extractions
- Graceful shutdown with 30s timeout

### `services/ws_manager.py`
- `WebSocketManager` with per-material-ID subscription sets
- `connect(material_id, websocket)` — register connection
- `disconnect(material_id, websocket)` — cleanup
- `broadcast(material_id, message)` — push status to all watchers

### `services/storage_service.py`
- Abstracts file storage for material text
- Current: local filesystem at `data/material_text/{uuid}.txt`
- UUID validation prevents path traversal
- Designed for future S3/MinIO migration

### `services/token_counter.py`
- `estimate_token_count(text)` — tiktoken-based estimate
- `track_token_usage(user_id, tokens)` — upserts UserTokenUsage daily aggregate
- `get_model_token_limit(model_name)` — per-model context window

### `services/audit_logger.py`
- `log_api_usage(user_id, endpoint, material_ids, context_tokens, response_tokens, model, llm_latency, retrieval_latency, total_latency)` — saves ApiUsageLog

### `services/performance_logger.py`
- Middleware that times each request and logs slow requests (>2s)

### `services/rate_limiter.py`
- Currently disabled — all requests pass through

### `services/gpu_manager.py`
- GPU memory management utilities for local model loading

### `services/model_manager.py`
- Registry of available LLM models and their metadata

### `services/notebook_name_generator.py`
- Generates AI-suggested notebook names based on first material

### `services/file_validator.py`
- MIME type detection (python-magic)
- Extension whitelist checking
- Returns structured validation result

---

## 13. RAG Pipeline — Deep Dive

`app/services/rag/pipeline.py`

### Chunking Strategy
- Splitter: `RecursiveCharacterTextSplitter` from LangChain
- Chunk overlap: 150 tokens
- Min chunk size: 100 chars (shorter discarded at indexing)
- Min retrieval chunk size: 150 chars (shorter skipped after retrieval)

### Embedding
- Model: `BAAI/bge-m3` (multilingual, 1024 dimensions)
- Stored in ChromaDB with EF `SentenceTransformerEmbeddingFunction`
- Warmed up at startup in thread pool executor

### Retrieval Parameters

| Parameter | Setting | Purpose |
|-----------|---------|---------|
| `INITIAL_VECTOR_K` | 10 | Initial vector similarity results |
| `MMR_K` | 8 | After MMR diversity filter |
| `MMR_LAMBDA` | 0.5 | Balance relevance vs diversity |
| `FINAL_K` | 10 | After reranker sorting |
| `MIN_SIMILARITY_SCORE` | 0.3 | Drop irrelevant chunks |
| `MAX_CONTEXT_TOKENS` | 6000 | Token budget for LLM context |
| `CHUNK_OVERLAP_TOKENS` | 150 | Chunk overlap for continuity |

### Pipeline Steps
1. Embed query with `embed_query()`
2. ChromaDB `query()` with `n_results=INITIAL_VECTOR_K`, filtered to user's material IDs
3. Filter chunks below `MIN_SIMILARITY_SCORE`
4. MMR re-ranking for diversity (λ=0.5 relevance/diversity trade-off)
5. If `USE_RERANKER=True`: bge-reranker-large cross-encoder scoring
6. Sort by reranker score, take top `FINAL_K`
7. Trim to `MAX_CONTEXT_TOKENS` budget
8. Format with `/services/rag/context_formatter.py`
9. Inject into prompt: `[Source: material_name, Page: N] chunk_text`
10. LLM generation with streaming
11. Citation extraction and validation

---

## 14. LLM Service

`app/services/llm_service/llm.py`

### Provider Selection
Configured via `LLM_PROVIDER` env var:

| Provider | Model | Class |
|----------|-------|-------|
| `OLLAMA` | `OLLAMA_MODEL` (default: llama3) | `ChatOllama` |
| `GOOGLE` | `GOOGLE_MODEL` (gemini-2.5-flash) | `ChatGoogleGenerativeAI` |
| `NVIDIA` | `NVIDIA_MODEL` (qwen/qwen3.5-397b-a17b) | `ChatNVIDIA` |
| `MYOPENLM` | Custom endpoint | Custom LangChain LLM |

### Factory Functions
- `get_llm()` — chat temperature (0.2), higher creativity
- `get_llm_structured()` — structured temperature (0.1), deterministic JSON output
- LRU cache (max 16 instances) keyed on provider + kwargs

### Temperature Configuration
| Context | Temperature |
|---------|------------|
| Structured (JSON) | 0.1 |
| Chat | 0.2 |
| Code generation | 0.1 |
| Creative (podcast, naming) | 0.7 |

### Prompt Templates
All prompts stored as plaintext `.txt` files in `app/prompts/` and loaded via `app/prompts/__init__.py`. No inline prompt strings in code.

---

## 15. Background Job Worker

`app/services/worker.py`

### Architecture
- Single `asyncio.Task` created at startup
- Event-driven: notified immediately when new job added
- Falls back to 2-second polling for missed notifications
- Max 5 concurrent material extractions (`asyncio.Semaphore`)
- 5-second backoff after unexpected errors

### Job Type Mapping
| jobType | Handler |
|---------|---------|
| `material_processing` | `process_material_by_id()` |
| `url_processing` | `process_url_material_by_id()` |
| `youtube_processing` | `process_url_material_by_id()` |
| `text_processing` | `process_text_material_by_id()` |

### Status Lifecycle
```
pending → processing → [ocr_running] → [transcribing] → embedding → completed
                                                                    → failed
```

### Stuck Job Recovery
On startup, resets any jobs stuck in `processing` state for > 30 minutes back to `pending`. Uses raw SQL for atomic update.

### Graceful Shutdown
- Sets `_shutdown_event` flag
- Waits for in-flight jobs to complete (30s timeout)
- Any remaining jobs left in DB with `processing` status (recovered on next start)

---

## 16. WebSocket Manager

`app/services/ws_manager.py` + `app/routes/websocket_router.py`

### Connection
```
WS /ws/materials/{material_id}?token={access_token}
```
- Token validated on connection
- User must own the material
- Connection stored in `Dict[str, Set[WebSocket]]` keyed by material_id

### Messages Pushed
```json
{"event": "status_update", "material_id": "...", "status": "embedding", "chunk_count": 0}
{"event": "status_update", "material_id": "...", "status": "completed", "chunk_count": 142}
{"event": "status_update", "material_id": "...", "status": "failed", "error": "OCR timeout"}
```

### Frontend Usage
- `useMaterialUpdates` hook subscribes on material view
- Updates material status in Zustand `useMaterialStore`
- Shows real-time progress indicator on upload

---

## 17. Vector Database (ChromaDB)

`app/db/chroma.py`

### Configuration
- Type: `PersistentClient` at `CHROMA_DIR`
- Collection: single shared collection `documents`
- Embedding function: `SentenceTransformerEmbeddingFunction` with `BAAI/bge-m3`
- Dimension: 1024

### Version Management
- Version marker file at `{CHROMA_DIR}/.embedding_version`
- Contains `EMBEDDING_VERSION` string (e.g., `bge_m3_v1`)
- If version mismatch on startup → **wipe entire CHROMA_DIR** → rebuild
- Dimension probe: embed test string → verify 1024-dim upsert succeeds before writing marker

### Document Storage Format
Each chunk stored with:
```python
{
  "id": f"{material_id}_{chunk_index}",
  "document": chunk_text,
  "metadata": {
    "material_id": "uuid",
    "user_id": "uuid",
    "notebook_id": "uuid",
    "chunk_index": N,
    "source_page": N,  # PDF page number
    "filename": "material.pdf"
  }
}
```

### Isolation
All queries filter by `material_id` (and optionally `user_id`) to prevent cross-user data leakage.

### Telemetry
All ChromaDB and posthog telemetry is disabled at import time.

---

## 18. Storage Service

`app/services/storage_service.py`

- Material texts stored at: `data/material_text/{material_id}.txt`
- UUID validation prevents path traversal attacks
- `save_material_text(material_id, text)` — writes UTF-8 text file
- `load_material_text(material_id)` — reads back
- `delete_material_text(material_id)` — removes file
- Designed as abstraction layer for future S3/MinIO migration

### Directory Layout
```
data/
├── uploads/          # Raw uploaded files (PDFs, audio, images, etc.)
├── material_text/    # Extracted text per material ({uuid}.txt)
├── models/           # Sentence-transformer model cache
├── chroma/           # ChromaDB persistent storage
│   ├── .embedding_version
│   ├── chroma.sqlite3
│   └── <uuid>/       # HNSW segment data
└── workspaces/       # Per-session code sandboxes
```

---

## 19. Security & Validation

### Upload Security
- MIME type detection via `python-magic` (not just extension)
- Extension whitelist: `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.csv`, `.txt`, `.md`, `.mp3`, `.wav`, `.m4a`, `.mp4`, `.jpg`, `.png`, etc.
- Filename sanitization: strip path separators, limit length
- Max upload size: 10 GB (configurable)

### Code Execution Security
`services/code_execution/security.py`:
- Static analysis of code before execution
- Forbidden import list: `os.system`, `subprocess`, `socket`, `ftplib`, `smtplib`, `ctypes`, `importlib`
- Dangerous pattern detection: `__import__`, bare `exec` on untrusted strings
- Approved on-demand packages: `seaborn`, `wordcloud`, `missingno`, `folium`, `altair`, `pyvis`
- Execution timeout: `CODE_EXECUTION_TIMEOUT` (15s default, up to 120s via API)
- Isolated temp directory per execution (`/tmp/kepler_code_*`)
- Cleanup of stale temp dirs on startup

### Artifact Access Control
- Each artifact gets a unique `downloadToken` (64-char random hex)
- Token expires after `ARTIFACT_TOKEN_EXPIRY_HOURS` (24h)
- `GET /workspace/file/{id}?token={downloadToken}` validates token and expiry
- Token burned after single use (or expiry)

### Path Traversal Prevention
- UUID format validation for all material_id references
- All file paths constructed through `safe_path()` utility
- No user-controlled path components in file I/O

---

## 20. Logging & Monitoring

### Log Configuration
`main.py` configures at module level (before any imports):
- **Stream handler**: stdout
- **File handler**: `logs/app.log`, rotating, 10 MB max, 3 backups
- Format: `%(asctime)s %(name)s %(levelname)s %(message)s`
- Noisy loggers suppressed: `httpx`, `httpcore`, `uvicorn.access`

### Request Logging
Every request logged with:
```
METHOD /path STATUS_CODE elapsed_time [request_id]
```
`X-Request-ID` header added to all responses.

### Performance Monitoring
`services/performance_logger.py` — middleware that:
- Times full request lifecycle
- Logs slow requests (>2s) with `SLOW_REQUEST` prefix
- Records endpoint, method, status, latency

### Database Audit Logging
`services/audit_logger.py` — saves `ApiUsageLog` for every LLM-powered request:
- Endpoint name
- Material IDs involved
- Context token count + response token count
- Model used
- LLM latency, retrieval latency, total latency

### Token Usage Tracking
`services/token_counter.py` — `UserTokenUsage` table updated daily with aggregate token consumption per user.

### Agent Execution Logging
`AgentExecutionLog` records every agent run:
- Intent, confidence, tools used, steps count, tokens, elapsed time

---

## 21. CLI Tools

All in `backend/cli/`:

| Script | Purpose |
|--------|---------|
| `backup_chroma.py` | Export ChromaDB data to backup |
| `download_models.py` | Pre-download embedding + reranker models |
| `export_embeddings.py` | Export embeddings to Parquet |
| `import_embeddings.py` | Import embeddings from Parquet |
| `migrate_material_joins.py` | Migrate legacy materialIds arrays to join table |
| `reindex.py` | Re-embed all materials (after model change) |

---

## 22. Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | ✅ | — | PostgreSQL connection string |
| `JWT_SECRET_KEY` | ✅ | — | 64-char random secret for JWT |
| `LLM_PROVIDER` | — | `OLLAMA` | `OLLAMA` / `GOOGLE` / `NVIDIA` / `MYOPENLM` |
| `GOOGLE_API_KEY` | If GOOGLE | — | Google AI Studio API key |
| `NVIDIA_API_KEY` | If NVIDIA | — | NVIDIA NIM API key |
| `OLLAMA_MODEL` | — | `llama3` | Ollama model name |
| `GOOGLE_MODEL` | — | `models/gemini-2.5-flash` | Google model ID |
| `ENVIRONMENT` | — | `development` | Sets cookie security, trusted hosts |
| `CORS_ORIGINS` | — | localhost:3000,5173 | Comma-separated allowed origins |
| `EMBEDDING_MODEL` | — | `BAAI/bge-m3` | Sentence-transformer model |
| `EMBEDDING_VERSION` | — | `bge_m3_v1` | Version marker (bump to rebuild index) |
| `RERANKER_MODEL` | — | `BAAI/bge-reranker-large` | Reranker model |
| `USE_RERANKER` | — | `true` | Enable/disable reranking |
| `CHROMA_DIR` | — | `./data/chroma` | ChromaDB storage |
| `UPLOAD_DIR` | — | `./data/uploads` | Uploaded file storage |
| `SEARCH_SERVICE_URL` | — | `http://localhost:8002` | External search microservice |
| `CODE_EXECUTION_TIMEOUT` | — | `15` | Sandbox execution timeout (seconds) |
| `MAX_CODE_REPAIR_ATTEMPTS` | — | `3` | LLM self-repair iterations |
| `REFRESH_TOKEN_EXPIRE_DAYS` | — | `7` | Refresh token lifetime |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | — | `15` | Access token lifetime |
| `COOKIE_SECURE` | — | `false` | Set to `true` for HTTPS production |
| `COOKIE_SAMESITE` | — | `lax` | Cookie SameSite policy |
| `MAX_CONTEXT_TOKENS` | — | `6000` | Max RAG context tokens |
| `LLM_TIMEOUT` | — | `None` | LLM call timeout (null = no timeout) |

---

*Generated from full codebase analysis — March 2026*
