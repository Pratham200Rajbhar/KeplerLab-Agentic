# KeplerLab — Backend Documentation

> **Application:** Study Assistant API v2.0.0  
> **Framework:** FastAPI (Python 3.11+)  
> **Architecture:** Async microservice-style monolith with LangGraph agentic AI

---

## Table of Contents

1. [Overview](#1-overview)
2. [Technology Stack](#2-technology-stack)
3. [High-Level Architecture](#3-high-level-architecture)
4. [Directory Structure](#4-directory-structure)
5. [Configuration & Environment Variables](#5-configuration--environment-variables)
6. [Application Startup Lifecycle](#6-application-startup-lifecycle)
7. [Database Schema](#7-database-schema)
8. [API Routes (Endpoints)](#8-api-routes-endpoints)
9. [Authentication & Security](#9-authentication--security)
10. [Middleware Stack](#10-middleware-stack)
11. [LLM Service](#11-llm-service)
12. [RAG Pipeline](#12-rag-pipeline)
13. [Agent System (LangGraph)](#13-agent-system-langgraph)
14. [Background Worker & Job Queue](#14-background-worker--job-queue)
15. [Document Processing Pipeline](#15-document-processing-pipeline)
16. [Podcast Feature (Live AI Podcast)](#16-podcast-feature-live-ai-podcast)
17. [WebSocket Infrastructure](#17-websocket-infrastructure)
18. [Generation Services](#18-generation-services)
19. [Code Execution & Sandbox](#19-code-execution--sandbox)
20. [Rate Limiting](#20-rate-limiting)
21. [CLI Tools](#21-cli-tools)
22. [Logging & Observability](#22-logging--observability)
23. [Data Flow Diagrams](#23-data-flow-diagrams)

---

## 1. Overview

KeplerLab is an **AI-powered learning platform** whose backend is a single FastAPI application that acts as the intelligence layer between users' study materials and AI services. It orchestrates:

- **Document ingestion** (PDF, DOCX, PPTX, images, audio/video, YouTube, web URLs, plain text)
- **Vector search** via ChromaDB for RAG (Retrieval-Augmented Generation)
- **LangGraph-powered agent** that classifies user intent and routes to specialized tools
- **Content generation** — flashcards, quizzes, mind maps, PowerPoint presentations, explainer videos, live podcasts
- **Real-time communication** via Server-Sent Events (SSE) for streaming LLM responses and WebSockets for processing status updates

---

## 2. Technology Stack

| Layer | Technology |
|-------|-----------|
| **API Framework** | FastAPI 0.115.6 |
| **ASGI Server** | Uvicorn (standard) |
| **Database ORM** | Prisma (prisma-client-py, async interface) |
| **Relational DB** | PostgreSQL |
| **Vector DB** | ChromaDB ≥ 0.5.11 |
| **LLM Orchestration** | LangChain 0.2.16, LangGraph ≥ 0.2.0 |
| **Embedding Model** | BAAI/bge-m3 (1024-dim, SentenceTransformers) |
| **Reranker** | BAAI/bge-reranker-large |
| **OCR** | Tesseract (pytesseract) + EasyOCR |
| **Audio Transcription** | OpenAI Whisper |
| **TTS** | edge-tts |
| **PDF Processing** | pypdf, PyMuPDF, pdfplumber, pdf2image |
| **Presentation Engine** | python-pptx |
| **Browser Automation** | Playwright (screenshot capture) |
| **Web Scraping** | BeautifulSoup4, Selenium |
| **YouTube** | youtube-transcript-api, yt-dlp |
| **Auth** | JWT (HS256, access + refresh token rotation) |
| **Password Hashing** | bcrypt (via passlib) |
| **Validation** | Pydantic v2 |
| **Caching** | fastapi-cache2, LRU in-process |
| **Data** | numpy, pyarrow, pandas (optional in sandbox) |
| **Tokenizer** | tiktoken (for token counting) |

### LLM Providers Supported

| Provider | Config Key | Model Example |
|----------|-----------|---------------|
| Ollama (local) | `OLLAMA` | `llama3` |
| Google Gemini | `GOOGLE` | `models/gemini-2.5-flash` |
| NVIDIA NIM | `NVIDIA` | `qwen/qwen3.5-397b-a17b` |
| MyOpenLM (fallback) | `MYOPENLM` | custom URL |

---

## 3. High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js)                    │
│     REST + SSE + WebSocket + HTTP-only Cookie Auth       │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                 FASTAPI APPLICATION                      │
│  ┌─────────────┐  ┌───────────────┐  ┌───────────────┐ │
│  │  Middleware  │  │    Routers    │  │   WebSocket   │ │
│  │  - CORS      │  │  18+ routes   │  │  /ws/jobs     │ │
│  │  - Rate Limit│  │               │  │               │ │
│  │  - Perf Log  │  │               │  │               │ │
│  │  - Body Size │  │               │  │               │ │
│  └─────────────┘  └───────┬───────┘  └───────────────┘ │
│                           │                              │
│  ┌───────────────────────▼───────────────────────────┐ │
│  │                   SERVICE LAYER                    │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │ │
│  │  │LangGraph │  │ RAG/     │  │  Generation       │ │ │
│  │  │ Agent    │  │ ChromaDB │  │  (PPT/Flash/Quiz) │ │ │
│  │  └──────────┘  └──────────┘  └──────────────────┘ │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │ │
│  │  │  Auth    │  │  Podcast │  │  Code Sandbox     │ │ │
│  │  └──────────┘  └──────────┘  └──────────────────┘ │ │
│  └───────────────────────┬───────────────────────────┘ │
│                           │                              │
│  ┌────────────────────────▼──────────────────────────┐ │
│  │           BACKGROUND WORKER (asyncio Task)        │ │
│  │  pending → processing → embedding → completed     │ │
│  └────────────────────────┬──────────────────────────┘ │
└───────────────────────────┼─────────────────────────────┘
                            │
          ┌─────────────────┼──────────────────┐
          │                 │                  │
  ┌───────▼──────┐  ┌───────▼──────┐  ┌───────▼──────┐
  │  PostgreSQL  │  │  ChromaDB    │  │  File System │
  │  (Prisma)   │  │  (Vectors)   │  │  (uploads/   │
  │             │  │              │  │   output/)   │
  └─────────────┘  └──────────────┘  └─────────────┘
```

---

## 4. Directory Structure

```
backend/
├── app/
│   ├── main.py                  # FastAPI entry, lifespan hooks, middleware registration
│   ├── core/
│   │   ├── config.py            # Pydantic Settings singleton (all env vars)
│   │   └── utils.py             # Shared utilities
│   ├── db/
│   │   ├── chroma.py            # ChromaDB client + collection factory
│   │   └── prisma_client.py     # Prisma singleton, connect/disconnect helpers
│   ├── models/
│   │   ├── mindmap_schemas.py   # Pydantic models for Mind Map
│   │   └── model_schemas.py     # Generic API response models
│   ├── prompts/                 # All LLM prompt templates (.txt)
│   │   ├── chat_prompt.txt
│   │   ├── code_generation_prompt.txt
│   │   ├── code_repair_prompt.txt
│   │   ├── data_analysis_prompt.txt
│   │   ├── flashcard_prompt.txt
│   │   ├── mindmap_prompt.txt
│   │   ├── podcast_qa_prompt.txt
│   │   ├── podcast_script_prompt.txt
│   │   ├── ppt_prompt.txt
│   │   └── quiz_prompt.txt
│   ├── routes/                  # FastAPI routers (one file per feature)
│   │   ├── auth.py              # POST /auth/signup, /login, /refresh, /logout, /me
│   │   ├── notebook.py          # CRUD /notebooks
│   │   ├── upload.py            # POST /upload, URL/YouTube/text sources
│   │   ├── chat.py              # POST /chat (SSE streaming), chat history, sessions
│   │   ├── flashcard.py         # POST /flashcards/generate, CRUD
│   │   ├── quiz.py              # POST /quiz/generate, CRUD
│   │   ├── ppt.py               # POST /presentations/generate, CRUD
│   │   ├── mindmap.py           # POST /mindmap/generate, CRUD
│   │   ├── podcast_live.py      # Full podcast lifecycle endpoints
│   │   ├── explainer.py         # POST /explainer (video explainer generation)
│   │   ├── agent.py             # POST /agent (direct agent invocation)
│   │   ├── jobs.py              # GET /jobs, DELETE /jobs/{id}
│   │   ├── models.py            # GET /models (available LLM list)
│   │   ├── search.py            # GET /search/query (web search proxy)
│   │   ├── proxy.py             # GET /api/v1/* (reverse proxy for external services)
│   │   ├── health.py            # GET /health
│   │   ├── websocket_router.py  # WS /ws/jobs/{user_id}
│   │   └── utils.py             # Shared route helpers (require_material etc.)
│   └── services/                # Business logic
│       ├── agent/               # LangGraph multi-step agent
│       │   ├── graph.py         # State machine wiring
│       │   ├── intent.py        # Intent detection (keyword + LLM fallback)
│       │   ├── planner.py       # Execution plan generation
│       │   ├── router.py        # Tool dispatch
│       │   ├── reflection.py    # Self-critique & continuation logic
│       │   ├── state.py         # AgentState dataclass
│       │   ├── persistence.py   # Agent log persistence
│       │   ├── tools_registry.py
│       │   ├── subgraphs/       # Specialized agent sub-workflows
│       │   └── tools/           # Agent tool implementations
│       │       ├── code_repair.py
│       │       ├── data_profiler.py
│       │       ├── file_generator.py
│       │       └── workspace_builder.py
│       ├── auth/                # JWT, bcrypt, token rotation, user crud
│       ├── chat/                # Chat session management, history
│       ├── code_execution/      # Python sandbox with environment isolation
│       ├── explainer/           # PPT → video narration pipeline
│       ├── flashcard/           # Flashcard generation service
│       ├── llm_service/
│       │   ├── llm.py           # Provider factory (Ollama/Google/NVIDIA/MyOpenLM)
│       │   ├── llm_schemas.py   # LLM response schemas
│       │   └── structured_invoker.py  # Structured output with retry + repair
│       ├── mindmap/             # Mind map generation service
│       ├── podcast/             # Live podcast: script, TTS, Q&A, export
│       │   ├── session_manager.py
│       │   ├── script_generator.py
│       │   ├── tts_service.py
│       │   ├── qa_service.py
│       │   ├── export_service.py
│       │   ├── voice_map.py
│       │   └── satisfaction_detector.py
│       ├── ppt/                 # PowerPoint generation
│       ├── quiz/                # Quiz generation service
│       ├── rag/                 # Retrieval-Augmented Generation pipeline
│       │   ├── embedder.py      # Chunk upsert into ChromaDB
│       │   ├── reranker.py      # BGE reranker for result re-scoring
│       │   ├── secure_retriever.py   # User-scoped vector query
│       │   ├── context_builder.py    # Context window assembly
│       │   ├── context_formatter.py  # Formats retrieved chunks for LLM prompt
│       │   └── citation_validator.py # Source citation accuracy
│       ├── text_processing/     # Document parsers
│       │   ├── file_detector.py  # MIME-type based routing
│       │   ├── youtube_service.py
│       │   ├── web_scraping.py   # Playwright + BeautifulSoup
│       │   └── ...              # PDF (multi-strategy), DOCX, PPTX, audio, video
│       ├── tts_provider/        # TTS abstraction (edge-tts)
│       ├── yt_translation/      # YouTube video translation
│       ├── audit_logger.py      # API usage log writer
│       ├── file_validator.py    # MIME whitelist & security checks
│       ├── gpu_manager.py       # GPU resource tracking
│       ├── job_service.py       # Background job CRUD helpers
│       ├── material_service.py  # Material lifecycle (create, process, delete)
│       ├── model_manager.py     # Model download management
│       ├── notebook_name_generator.py  # AI-generated notebook names
│       ├── notebook_service.py  # Notebook CRUD helpers
│       ├── performance_logger.py  # Request performance middleware
│       ├── rate_limiter.py      # Sliding window rate limiter
│       ├── storage_service.py   # File I/O helpers
│       ├── token_counter.py     # tiktoken token usage tracking
│       ├── worker.py            # Background job processor (asyncio task)
│       └── ws_manager.py       # WebSocket connection registry
├── cli/                         # CLI management scripts
│   ├── backup_chroma.py         # Backup ChromaDB to disk
│   ├── download_models.py       # Pre-download embedding/reranker models
│   ├── export_embeddings.py     # Export vector embeddings
│   ├── import_embeddings.py     # Import vector embeddings
│   └── reindex.py               # Re-embed all materials
├── data/
│   ├── chroma/                  # ChromaDB persistence directory
│   ├── material_text/           # Extracted text cache per material
│   ├── models/                  # Downloaded HuggingFace model weights
│   ├── output/                  # Generated files (PPT, podcast, video)
│   └── uploads/                 # Uploaded source files
├── logs/                        # Rotating application logs
├── output/                      # Generated artefacts (presentations, podcast, etc.)
├── prisma/
│   └── schema.prisma            # Database schema (PostgreSQL via Prisma)
├── templates/                   # PPTX templates
└── requirements.txt
```

---

## 5. Configuration & Environment Variables

All settings are managed through `app/core/config.py` using `pydantic-settings`. A `.env` file in the `backend/` root is loaded automatically.

### Required Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (e.g. `postgresql://user:pass@localhost:5432/db`) |
| `JWT_SECRET_KEY` | 64-character random secret for JWT signing |

### LLM Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `OLLAMA` | Active provider: `OLLAMA`, `GOOGLE`, `NVIDIA`, `MYOPENLM` |
| `OLLAMA_MODEL` | `llama3` | Ollama model name |
| `GOOGLE_API_KEY` | `""` | Google Generative AI API key |
| `GOOGLE_MODEL` | `models/gemini-2.5-flash` | Google Gemini model |
| `NVIDIA_API_KEY` | `""` | NVIDIA NIM API key |
| `NVIDIA_MODEL` | `qwen/qwen3.5-397b-a17b` | NVIDIA model |

### LLM Generation Parameters

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_TEMPERATURE_STRUCTURED` | `0.1` | For deterministic structured output |
| `LLM_TEMPERATURE_CHAT` | `0.2` | For conversational responses |
| `LLM_TEMPERATURE_CREATIVE` | `0.7` | For creative content |
| `LLM_TEMPERATURE_CODE` | `0.1` | For code generation |
| `LLM_MAX_TOKENS` | `4000` | Max output tokens for structured tasks |
| `LLM_MAX_TOKENS_CHAT` | `3000` | Max output tokens for chat |

### Embedding & RAG Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | HuggingFace embedding model |
| `EMBEDDING_DIMENSION` | `1024` | Vector dimension |
| `RERANKER_MODEL` | `BAAI/bge-reranker-large` | BGE reranker model |
| `INITIAL_VECTOR_K` | `10` | Initial candidates from vector search |
| `MMR_K` | `8` | MMR diversity candidates |
| `FINAL_K` | `10` | Final chunks after reranking |
| `MAX_CONTEXT_TOKENS` | `6000` | Token budget for context window |
| `MIN_SIMILARITY_SCORE` | `0.3` | Minimum cosine similarity threshold |

### Auth & Cookie Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | JWT access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |
| `COOKIE_SECURE` | `false` | `true` in production (HTTPS only) |
| `COOKIE_SAMESITE` | `lax` | Cookie SameSite policy |

### Paths

| Variable | Default |
|----------|---------|
| `CHROMA_DIR` | `./data/chroma` |
| `UPLOAD_DIR` | `./data/uploads` |
| `MODELS_DIR` | `./data/models` |
| `MAX_UPLOAD_SIZE_MB` | `25` |

---

## 6. Application Startup Lifecycle

The FastAPI `lifespan` context manager in `main.py` runs the following initialization sequence on every server start:

```
1. Connect to PostgreSQL via Prisma
   └─ Creates connection pool

2. Warm up embedding model (thread pool)
   └─ Loads BAAI/bge-m3 into memory (avoids cold-start latency)

3. Preload reranker model (thread pool)
   └─ Loads BAAI/bge-reranker-large into memory

4. Start background job processor (asyncio.Task)
   └─ Infinite loop polling pending material_processing jobs

5. Ensure sandbox packages installed
   └─ pip install in isolated sandbox environment

5b. Clean stale sandbox temp directories
    └─ Removes /tmp/kepler_sandbox_* from previous crashes

6. Create output directories
   └─ generated/, presentations/, explainers/, podcast/

── Server now accepting requests ──

On Shutdown:
1. Graceful job processor shutdown (30s timeout)
2. Disconnect Prisma/PostgreSQL
```

---

## 7. Database Schema

All tables are managed by **Prisma** and persisted in **PostgreSQL**.

### Users (`users`)

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | Auto-generated UUID |
| `email` | VARCHAR(255) UNIQUE | User email |
| `username` | VARCHAR(100) | Display name |
| `hashed_password` | VARCHAR(255) | bcrypt hash |
| `is_active` | BOOLEAN | Account enabled flag |
| `role` | VARCHAR(50) | `user` or `admin` |
| `created_at` | DATETIME | |

### Notebooks (`notebooks`)

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | Owner |
| `name` | VARCHAR(255) | Notebook name |
| `description` | TEXT | Optional description |

### Materials (`materials`)

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID PK | |
| `user_id` | UUID FK → users | Owner |
| `notebook_id` | UUID FK → notebooks | Parent notebook (nullable) |
| `filename` | VARCHAR(255) | Original filename |
| `title` | VARCHAR(510) | Custom title (for URLs/YouTube) |
| `original_text` | TEXT | Extracted full text |
| `status` | ENUM | `pending → processing → ocr_running → transcribing → embedding → completed → failed` |
| `chunk_count` | INT | Number of vector chunks stored |
| `source_type` | VARCHAR(50) | `file`, `url`, `youtube`, `text` |
| `metadata` | TEXT (JSON) | Extraction metadata |

### Chat Sessions (`chat_sessions`)

Each chat panel conversation. Scoped to a notebook + user.

### Chat Messages (`chat_messages`)

| Column | Type | Description |
|--------|------|-------------|
| `role` | VARCHAR(20) | `user` or `assistant` |
| `content` | TEXT | Message body |
| `agent_meta` | TEXT (JSON) | Intent, tools_used, step_log |

### Response Blocks (`response_blocks`)

Paragraph-level blocks of assistant messages, enabling per-block follow-up questions.

### Generated Content (`generated_content`)

Stores all AI-generated artefacts: flashcards, quizzes, presentations, mind maps.

| Column | Type | Description |
|--------|------|-------------|
| `content_type` | VARCHAR(50) | `flashcard`, `quiz`, `presentation`, `mindmap` |
| `data` | JSON | The generated content payload |
| `material_ids` | STRING[] | Source material IDs used |

### Background Jobs (`background_jobs`)

| Column | Type | Description |
|--------|------|-------------|
| `job_type` | VARCHAR(50) | `material_processing` |
| `status` | ENUM | `pending → processing → completed/failed` |
| `result` | JSON | Processing result metadata |

### Other Tables

| Table | Purpose |
|-------|---------|
| `refresh_tokens` | JWT refresh token rotation tracking |
| `user_token_usage` | Daily token consumption tracking (per user) |
| `api_usage_logs` | Per-endpoint latency and token metrics |
| `agent_execution_logs` | Agent intent/tool/performance logs |
| `code_execution_sessions` | Python sandbox execution records |
| `research_sessions` | Web research session logs |
| `explainer_videos` | Video explainer generation records |
| `podcast_sessions` | Live podcast session with status lifecycle |
| `podcast_segments` | Individual podcast audio segments |
| `podcast_doubts` | Q&A doubts during podcast playback |
| `podcast_exports` | PDF/JSON export records |
| `podcast_bookmarks` | User bookmarks in podcast |
| `podcast_annotations` | User notes on podcast segments |

---

## 8. API Routes (Endpoints)

### Authentication (`/auth`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/signup` | Register new user |
| POST | `/auth/login` | Login → access token + HttpOnly refresh cookie |
| POST | `/auth/refresh` | Silent token refresh using HttpOnly cookie |
| POST | `/auth/logout` | Revoke refresh token family |
| GET | `/auth/me` | Get current user profile |

**Auth flow:**
- Access tokens expire in **15 minutes** (JWT, Bearer)
- Refresh tokens expire in **7 days** (HttpOnly Secure cookie, family-based rotation)
- On each refresh, the old token is marked `used=true`, a new token and new family token are issued
- Replay attacks → revoke entire token family

### Notebooks (`/notebooks`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/notebooks` | List user's notebooks |
| POST | `/notebooks` | Create notebook |
| GET | `/notebooks/{id}` | Get notebook details |
| PUT | `/notebooks/{id}` | Update name/description |
| DELETE | `/notebooks/{id}` | Delete (cascades materials, chats) |

### Upload (`/upload`, `/materials`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload` | Upload file (PDF, DOCX, PPTX, images, audio, video) |
| POST | `/upload/url` | Add web URL as material |
| POST | `/upload/youtube` | Add YouTube video as material |
| POST | `/upload/text` | Add raw text as material |
| GET | `/materials` | List materials (optionally by notebook) |
| DELETE | `/materials/{id}` | Delete material + vectors |
| PUT | `/materials/{id}` | Update material title |
| GET | `/materials/{id}/file` | Download original file (file token auth) |

**Supported file types:**
- Documents: PDF, DOCX, DOC, TXT, MD, RTF, HTML
- Spreadsheets: XLSX, XLS, CSV
- Presentations: PPTX, PPT
- Images: JPG, JPEG, PNG, GIF, BMP, TIFF, WEBP (OCR-processed)
- Audio: MP3, WAV, M4A, OGG, FLAC (Whisper transcription)
- Video: MP4, AVI, MOV, MKV (audio extracted → Whisper)

### Chat (`/chat`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat` | Send message → SSE streaming response |
| GET | `/chat/history` | Get chat messages for session |
| POST | `/chat/clear` | Clear session messages |
| GET | `/chat/sessions` | List chat sessions for notebook |
| POST | `/chat/sessions` | Create new chat session |
| DELETE | `/chat/sessions/{id}` | Delete chat session |
| POST | `/chat/block-followup` | Follow-up on a specific response block |
| POST | `/chat/suggestions` | Get autocomplete suggestions |

### Generation Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/flashcards/generate` | Generate flashcards from materials |
| GET | `/flashcards` | List saved flashcards |
| DELETE | `/flashcards/{id}` | Delete flashcard set |
| POST | `/quiz/generate` | Generate quiz from materials |
| GET | `/quiz` | List saved quizzes |
| DELETE | `/quiz/{id}` | Delete quiz |
| POST | `/presentations/generate` | Generate PowerPoint from materials |
| GET | `/presentations` | List saved presentations |
| DELETE | `/presentations/{id}` | Delete presentation |
| POST | `/mindmap/generate` | Generate mind map from materials |
| GET | `/mindmap` | List saved mind maps |

### Podcast (`/podcast`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/podcast/sessions` | Create new podcast session |
| GET | `/podcast/sessions` | List user's podcast sessions |
| GET | `/podcast/sessions/{id}` | Get session details + segments |
| POST | `/podcast/sessions/{id}/start` | Begin script + audio generation |
| DELETE | `/podcast/sessions/{id}` | Delete session |
| GET | `/podcast/sessions/{id}/audio/{segment}` | Stream audio for a segment |
| POST | `/podcast/sessions/{id}/doubts` | Ask a clarifying question (pauses podcast) |
| POST | `/podcast/sessions/{id}/bookmarks` | Bookmark a segment |
| POST | `/podcast/sessions/{id}/annotations` | Annotate a segment |
| POST | `/podcast/sessions/{id}/export` | Export as PDF or JSON |
| GET | `/podcast/voices` | List available TTS voices |
| POST | `/podcast/preview-voice` | Generate voice preview sample |

### Other Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/models` | List available LLM models |
| GET | `/jobs` | Get user's background jobs |
| POST | `/agent` | Direct agent endpoint |
| GET | `/search/query` | Web search via external service |
| GET/POST | `/api/v1/*` | Reverse proxy to external services |
| POST | `/explainer` | Generate explainer video from presentation |
| WS | `/ws/jobs/{user_id}?token=<jwt>` | WebSocket for material processing updates |

---

## 9. Authentication & Security

### JWT Token Architecture

```
Login Request
    │
    ▼
authenticate_user()
    │ bcrypt.verify(password, hash)
    ▼
create_access_token()  →  JWT (HS256, 15 min)  →  Bearer header
create_refresh_token() →  JWT (HS256, 7 days)  →  HttpOnly Secure Cookie
store_refresh_token()  →  hashed in DB (refresh_tokens table)
```

### Token Rotation (refresh endpoint)

```
Browser sends HttpOnly cookie
    │
    ▼
validate_and_rotate_refresh_token()
    ├── Verify token not expired
    ├── Verify hash matches DB record
    ├── If token already used → REVOKE entire family (replay attack)
    ├── Mark old token as used=true
    ├── Issue new token with new hash, same family
    └── Return new access_token
```

### Password Requirements

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit

### File Access Security

Files served via `/materials/{id}/file` use short-lived **file tokens** (5 minutes) separate from the main access token, preventing URL sharing.

### Upload Security

All uploaded files go through:
1. Content-Length check (max 25 MB configurable)
2. `python-magic` MIME detection (server-side, not relying on file extension)
3. MIME whitelist check against `FileTypeDetector.SUPPORTED_TYPES`
4. SSRF protection on URL uploads (blocks private RFC-1918 addresses)

---

## 10. Middleware Stack

Middleware is applied in registration order (outermost first):

```
1. Performance Monitoring   — records start time, logs latency + path
2. Rate Limiting            — sliding window per user/IP
3. Request Logging          — attaches request_id UUID, logs method+path+status+ms
4. CORS                     — allows configured origins, credentials
5. Body Size Limiter        — 100 MB hard cap
6. TrustedHostMiddleware    — (production only) validates Host header
```

### Rate Limits

| Endpoint Category | Limit |
|-------------------|-------|
| Chat (`/chat`) | 30 requests/minute/user |
| Generation (flashcard, quiz, PPT) | 5 requests/minute/user |
| Auth (login, signup) | 10 requests/minute/IP |

---

## 11. LLM Service

Located at `app/services/llm_service/llm.py`. Provides a unified `get_llm()` / `get_llm_structured()` interface over all providers.

### Factory Pattern

```python
get_llm()           # temperature=0.2, for chat
get_llm_structured() # temperature=0.1, for JSON output
get_llm_creative()   # temperature=0.7, for creative content
get_llm_code()       # temperature=0.1, for code generation
```

Each call returns a cached LangChain `ChatXxx` instance. The cache is keyed on frozen kwargs (max 16 entries).

### Structured Invoker (`structured_invoker.py`)

Used for all generation tasks (flashcards, quiz, PPT, mind map). Features:
- JSON schema validation via Pydantic models
- Automatic retry on parse errors (up to 3 attempts)
- JSON repair (`json_repair` library) before retry
- Structured output via `.with_structured_output()` or prompt-based JSON extraction

### Prompt Templates

All prompts are stored as `.txt` files in `app/prompts/` and loaded at runtime:

| File | Used For |
|------|---------|
| `chat_prompt.txt` | RAG-based chat |
| `flashcard_prompt.txt` | Flashcard generation |
| `quiz_prompt.txt` | Quiz generation |
| `ppt_prompt.txt` | Presentation generation |
| `mindmap_prompt.txt` | Mind map generation |
| `code_generation_prompt.txt` | Code generation |
| `code_repair_prompt.txt` | Code error repair |
| `data_analysis_prompt.txt` | Data analysis tasks |
| `podcast_script_prompt.txt` | Podcast script generation |
| `podcast_qa_prompt.txt` | Podcast Q&A answers |

---

## 12. RAG Pipeline

The Retrieval-Augmented Generation pipeline runs whenever a user asks a question in chat.

### Embedding Storage Flow

```
Upload → text extraction → text chunking → embed_and_store()
                                                │
                                                ▼
                                        ChromaDB.upsert()
                                        {text, metadata: {user_id, notebook_id,
                                         material_id, filename, chunk_index}}
```

**Chunking strategy:** LangChain `RecursiveCharacterTextSplitter` with `CHUNK_OVERLAP_TOKENS=150`. Minimum chunk length is 100 characters (filtered before storage).

**Embedding model:** BAAI/bge-m3 (1024-dimensional, runs locally via SentenceTransformers). ChromaDB uses its own ONNX pipeline for fast inference.

### Retrieval Flow

```
User Query
    │
    ▼
secure_retriever.py  (user_id + notebook_id filter)
    │
    ├── Initial vector search (k=10, cosine similarity)
    │
    ├── MMR (Maximal Marginal Relevance, k=8, lambda=0.5)
    │   └─ Balances relevance vs. diversity
    │
    ├── BGE Reranker (cross-encoder scoring)
    │   └─ Re-scores all 10 candidates against the query
    │
    ├── Filter: similarity < 0.3 threshold
    │
    └── context_builder.py
        └─ Assembles final context within MAX_CONTEXT_TOKENS=6000 budget
        └─ citation_validator.py → ensures citation accuracy
```

### Tenant Isolation

Every ChromaDB document has `user_id` in metadata. All queries filter by `{"user_id": {"$eq": current_user_id}}` to ensure strict data isolation between users.

---

## 13. Agent System (LangGraph)

The agent is a **LangGraph StateGraph** — a directed graph of async nodes representing a multi-step reasoning loop. It replaces a simple linear chain with a self-correcting, multi-tool agent.

### Intent Types

| Intent | Trigger | Description |
|--------|---------|-------------|
| `QUESTION` | Default | RAG-based Q&A on materials |
| `DATA_ANALYSIS` | CSV/Excel keywords | Python data analysis + charting |
| `RESEARCH` | "research, investigate, latest news" | Multi-source web research |
| `CODE_EXECUTION` | "run, execute Python" | Code sandbox execution |
| `FILE_GENERATION` | "create CSV, word report" | File generation |
| `CONTENT_GENERATION` | "make quiz, flashcards, PPT" | Content generation |
| `AGENT_TASK` | `/agent` slash command | Autonomous multi-step task |
| `WEB_RESEARCH` | `/web` slash command | 5-phase structured research |
| `CODE_GENERATION` | `/code` slash command | Code generation (no auto-run) |

### Intent Detection Flow

```
User Message
    │
    ▼
Keyword Rules (regex patterns with confidence 0.90–0.92)
    │
    ├── High confidence (≥0.85) → skip LLM, use keyword result
    │
    └── Low confidence → LLM classification (MyOpenLM fast model)
```

### Graph Nodes

```
[intent_and_plan] → [tool_router] → [reflection]
                          ↑              │
                          │              ├── continue → back to tool_router
                          │              └── respond → [generate_response]
                          │
                          └── (iterates up to MAX_AGENT_ITERATIONS)
```

**Safeguards:**
- `MAX_AGENT_ITERATIONS`: prevents infinite loops
- `TOKEN_BUDGET`: stops when too many tokens consumed
- Graceful degradation messages on budget/iteration exhaustion

### Tools Available to Agent

| Tool | Intent | Description |
|------|--------|-------------|
| `rag_tool` | QUESTION | Retrieves and answers from materials via RAG |
| `python_tool` | DATA_ANALYSIS / CODE_EXECUTION | Runs Python in sandbox |
| `data_profiler` | DATA_ANALYSIS | Profiles CSV/Excel for statistics |
| `research_tool` | RESEARCH | Iterative web research via external service |
| `quiz_tool` | CONTENT_GENERATION | Generates quiz |
| `flashcard_tool` | CONTENT_GENERATION | Generates flashcards |
| `ppt_tool` | CONTENT_GENERATION | Generates presentation |
| `code_repair` | Any (on error) | Detects and repairs broken code |
| `file_generator` | FILE_GENERATION | Creates CSV/Excel/PDF/Word files |
| `workspace_builder` | AGENT_TASK | Builds complex multi-file workspaces |

### Streaming

The agent streams intermediate steps to the client via **SSE (Server-Sent Events)**:

```json
{"type": "agent_step", "step": {"tool": "rag_tool", "intent": "QUESTION"}}
{"type": "token", "content": "Based on your materials..."}
{"type": "done", "agent_meta": {"intent": "QUESTION", "tools_used": ["rag_tool"]}}
```

---

## 14. Background Worker & Job Queue

Implemented as a single `asyncio.Task` started at application startup.

### Job Processor Loop

```python
while not shutdown:
    job = await fetch_next_pending_job()   # SELECT ... FOR UPDATE SKIP LOCKED
    if job:
        await claim_job(job)               # status → processing
        try:
            await process_material_by_id() # full extraction pipeline
            await complete_job(job)        # status → completed
        except Exception:
            await fail_job(job, error)     # status → failed
    else:
        await asyncio.sleep(2.0)           # poll every 2 seconds
```

### Concurrency

- Maximum 5 concurrent processing jobs (`MAX_CONCURRENT_JOBS`)
- PostgreSQL `FOR UPDATE SKIP LOCKED` ensures only one worker picks each job (safe for future multi-process scaling)
- Poll interval: 2 seconds
- Stuck job recovery at startup: jobs in `processing` state older than 30 minutes are reset to `pending`

### Status Lifecycle

```
pending → processing → ocr_running (images/scanned PDFs)
                     → transcribing (audio/video)
                     → embedding
                     → completed
                     (on error) → failed
```

Real-time status updates are pushed via WebSocket to the connected frontend.

---

## 15. Document Processing Pipeline

Each material type goes through a specialized extraction path:

### PDF Files

Multi-strategy extraction (attempted in order):
1. **pdfplumber** — best for tables; extracts structure
2. **PyMuPDF (fitz)** — fast text extraction with layout preservation
3. **pypdf** — fallback basic extraction
4. **OCR fallback** — if text density too low → pdf2image + Tesseract/EasyOCR

### Images

- Tesseract OCR (primary, with english+auto language)
- EasyOCR fallback for non-Latin scripts

### Audio Files

- ffmpeg extraction + format normalization
- OpenAI Whisper transcription (runs in thread pool)
- Multi-language support

### Video Files

- Audio extraction via ffmpeg
- Same Whisper transcription pipeline as audio

### YouTube Videos

- `youtube-transcript-api` — fast subtitle retrieval if available
- `yt-dlp` fallback — downloads audio → Whisper transcription
- Metadata extraction (title, description, chapters)

### Web URLs

- `requests` + BeautifulSoup — fast HTML scraping
- `Playwright` — JS-heavy sites requiring browser rendering
- SSRF protection: blocks private IP ranges, localhost, link-local

### DOCX/PPTX

- `python-docx` for Word documents
- `python-pptx` for PowerPoint (text + speaker notes)

### Spreadsheets (CSV/Excel)

- `openpyxl` for XLSX, `xlrd` for XLS
- Parquet side-car stored alongside for efficient data analysis

---

## 16. Podcast Feature (Live AI Podcast)

The live podcast feature converts notebook materials into an interactive audio experience between a "host" and "guest" AI.

### Session Modes

| Mode | Description |
|------|-------------|
| `overview` | High-level survey of materials |
| `deep-dive` | Detailed technical exploration |
| `debate` | Host and guest debate topic |
| `q-and-a` | Q&A style podcast |
| `full` | Comprehensive treatment |
| `topic` | User-specified topic |

### Generation Pipeline

```
1. User creates session (selects materials, mode, voices, language)
2. POST /podcast/sessions/{id}/start
3. script_generator.py
   └─ Retrieves context from RAG
   └─ Generates host/guest dialogue with LLM
   └─ Creates chapters with timestamps
4. tts_service.py (edge-tts)
   └─ Generates audio for each segment (host/guest voices)
   └─ Stores as .mp3 files
5. WebSocket pushes progress to frontend
6. Frontend streams audio segments progressively
```

### Interactive Features

- **Doubts system**: User pauses podcast, types a question → LLM answers → TTS generates audio response
- **Satisfaction detection**: Detects if the doubt was resolved
- **Bookmarks**: User can mark important segments
- **Annotations**: User can add notes to segments
- **Export**: Full podcast as PDF (script) or JSON

### TTS Voice System

- Backend: `edge-tts` (Microsoft Edge TTS)
- Multi-language support (mapped in `voice_map.py`)
- Gender-selectable voices (male/female)
- Preview generation for voice selection

---

## 17. WebSocket Infrastructure

### Endpoint: `/ws/jobs/{user_id}`

**Authentication:** JWT token passed as `?token=<jwt>` query parameter.

**Message Types:**

| Type | Direction | Description |
|------|-----------|-------------|
| `material_update` | Server → Client | `{material_id, status, chunk_count?}` |
| `ping` | Server → Client | Keepalive every 30 seconds |
| `error` | Server → Client | Error notification |
| `pong` | Client → Server | Keepalive response |

**Connection limits:** Max 10 connections per user (DoS protection).

### Usage Pattern

The backend's worker and material_service call `ws_manager.send_to_user(user_id, event)` whenever material status changes, giving the frontend real-time updates without polling.

---

## 18. Generation Services

### Flashcard Generation

- LLM generates question/answer pairs from material context
- Supports multiple languages
- Count configurable (default 10)
- Saved as `GeneratedContent` with `content_type="flashcard"`

### Quiz Generation

- Multiple choice questions (4 options, 1 correct)
- Difficulty level configurable
- Question count configurable
- Saved as `GeneratedContent` with `content_type="quiz"`

### PowerPoint Generation

- Uses Jinja2-style template variables
- PPTX template in `templates/`
- Generates: title slide, content slides, summary slide
- Chapter detection from material structure
- Saved as both `GeneratedContent` + `.pptx` file in `output/presentations/`

### Mind Map Generation

- Hierarchical node/edge structure
- JSON-structured `MindMapNode` schema
- Recursive up to 5 levels deep
- Returned as JSON for frontend rendering (React Flow)

### Explainer Video

- Reads generated PPT
- Generates narration script per slide
- TTS audio generation per slide
- Combines slides (rendered as images via LibreOffice) + audio → video (ffmpeg)
- Stores final `.mp4` in `output/explainers/`

---

## 19. Code Execution & Sandbox

Python code execution happens in an isolated environment:

**Security measures:**
- Separate temp directory per execution (`/tmp/kepler_sandbox_*`)
- Timeout enforced: `CODE_EXECUTION_TIMEOUT=15` seconds
- Subprocess with restricted environment
- Cleanup on completion and crash recovery at startup

**Features:**
- Standard output + stderr captured
- Chart detection (matplotlib `plt.show()` intercepted → base64 PNG)
- Data analysis integration: profiler runs first to understand structure, then Python tool generates analysis code

**Code Repair:**
- On execution error, `code_repair` tool is invoked
- LLM receives original code + stderr → generates fixed code
- Up to `MAX_CODE_REPAIR_ATTEMPTS=3` retries

---

## 20. Rate Limiting

In-memory sliding window rate limiter (per user ID / per IP):

```
chat endpoints:        30 req / 60s / user
generation endpoints:  5  req / 60s / user
auth endpoints:        10 req / 60s / IP
```

Returns `HTTP 429` with `Retry-After` header and JSON body:
```json
{"error": "Rate limit exceeded", "limit": 30, "window_seconds": 60, "retry_after": 23}
```

---

## 21. CLI Tools

Located in `backend/cli/`:

| Script | Command | Description |
|--------|---------|-------------|
| `download_models.py` | `python -m cli.download_models` | Pre-downloads embedding + reranker models |
| `backup_chroma.py` | `python -m cli.backup_chroma` | Creates timestamped backup of ChromaDB |
| `reindex.py` | `python -m cli.reindex` | Re-embeds all materials (use after model change) |
| `export_embeddings.py` | `python -m cli.export_embeddings` | Exports vectors to disk (Parquet) |
| `import_embeddings.py` | `python -m cli.import_embeddings` | Imports vectors from disk |

---

## 22. Logging & Observability

### Application Logging

- **Format:** `%(asctime)s %(name)s %(levelname)s %(message)s`
- **Handlers:** stdout + rotating file (`logs/app.log`, max 10 MB, 3 backups)
- **Noise suppression:** `httpx`, `httpcore`, `uvicorn.access` set to WARNING

### Request Logging

Every HTTP request logs: `METHOD /path STATUS_CODE elapsed_time [request_id]`

### Performance Monitoring

`performance_logger.py` middleware tracks:
- Endpoint path + method
- Response status
- Full request latency

### Audit Logging

`audit_logger.py` writes to `api_usage_logs`:
- Endpoint called
- Material IDs used
- Context / response token counts
- LLM and retrieval latency

### Token Tracking

`token_counter.py` tracks daily token usage per user in `user_token_usage` table.

---

## 23. Data Flow Diagrams

### Complete Chat Request Flow

```
Frontend
  │  POST /chat {message, material_ids, notebook_id, session_id}
  │
  ▼
FastAPI /chat route
  │
  ├── Validate material ownership
  ├── Filter completed materials only
  ├── Create/retrieve chat session
  │
  ▼
Agent Graph (LangGraph)
  │
  ├── [intent_and_plan]
  │     └── Keyword detection → QUESTION/DATA_ANALYSIS/RESEARCH/etc.
  │
  ├── [tool_router]
  │     ├── rag_tool → secure_retriever → ChromaDB → context_builder → LLM
  │     ├── python_tool → sandbox → stdout + charts
  │     ├── research_tool → external search service → synthesize
  │     └── ...
  │
  ├── [reflection]
  │     └── Good enough? → respond / continue
  │
  └── [generate_response]
        └── Synthesize all tool outputs → streamed tokens
              │
              ▼  SSE stream
Frontend receives:
  - agent step metadata (tool name, intent)
  - streamed markdown tokens
  - citations array
  - final agent_meta (tools_used, elapsed, tokens)
```

### Material Upload Flow

```
Frontend
  │  POST /upload (multipart form)
  │
  ▼
upload route
  ├── File saved to /data/uploads/{user_id}/{uuid}_{filename}
  ├── Material record created (status=pending)
  ├── BackgroundJob created (status=pending)
  └── Returns {material_id, job_id} immediately
         │
         │  (async, background)
         │
         ▼
Background Worker picks up job
  ├── status → processing
  ├── Text extraction (PDF/DOCX/audio/image/etc.)
  ├── status → embedding
  ├── Chunking → embed_and_store() → ChromaDB.upsert()
  ├── status → completed
  └── ws_manager.send_to_user() → WebSocket → Frontend updates

Frontend (WebSocket)
  └── Receives material_update events, updates UI status badges
```
