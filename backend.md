# KeplerLab Backend — Complete Architecture & Feature Flows

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Technology Stack](#2-technology-stack)
3. [Project Structure](#3-project-structure)
4. [Configuration & Environment Variables](#4-configuration--environment-variables)
5. [Application Startup & Lifespan](#5-application-startup--lifespan)
6. [Middleware Stack](#6-middleware-stack)
7. [Database Architecture](#7-database-architecture)
8. [Authentication Flow](#8-authentication-flow)
9. [Material Upload & Processing Pipeline](#9-material-upload--processing-pipeline)
10. [Background Worker](#10-background-worker)
11. [RAG Pipeline (Default Chat)](#11-rag-pipeline-default-chat)
12. [Chat Route — 5 Intent Paths](#12-chat-route--5-intent-paths)
13. [Agent System](#13-agent-system)
14. [Web Research Pipeline](#14-web-research-pipeline)
15. [Code Execution Sandbox](#15-code-execution-sandbox)
16. [Flashcard Generation](#16-flashcard-generation)
17. [Quiz Generation](#17-quiz-generation)
18. [Presentation (PPT) Generation](#18-presentation-ppt-generation)
19. [Mind Map Generation](#19-mind-map-generation)
20. [Podcast Live System](#20-podcast-live-system)
21. [Explainer Video Pipeline](#21-explainer-video-pipeline)
22. [Notebooks](#22-notebooks)
23. [Chat Sessions & History](#23-chat-sessions--history)
24. [Block Follow-up & Suggestions](#24-block-follow-up--suggestions)
25. [WebSocket Manager](#25-websocket-manager)
26. [LLM Service Layer](#26-llm-service-layer)
27. [Search Endpoint](#27-search-endpoint)
28. [Jobs Endpoint](#28-jobs-endpoint)
29. [Token Counting, Rate Limiting & Audit Logging](#29-token-counting-rate-limiting--audit-logging)
30. [Complete API Reference](#30-complete-api-reference)

---

## 1. System Overview

KeplerLab is a full-stack AI-powered learning platform. The backend is a **FastAPI** application that provides:

- Multi-tenant document ingestion, chunking, and vector embedding
- RAG (Retrieval-Augmented Generation) chat with citation support
- An agentic system with tool calling, reflection, and self-healing code repair
- Deep web research pipeline (DuckDuckGo + httpx + trafilatura)
- Sandboxed Python code execution with matplotlib chart capture
- Flashcard, quiz, mind map, and PPT generation from materials
- Podcast generation with multi-voice TTS (edge-tts)
- Explainer video generation from PPT (screenshots + TTS + ffmpeg)
- Block-level response interactions and prompt suggestions
- Full WebSocket support for real-time podcast Q&A
- JWT-based authentication with refresh tokens

### High-Level Component Map

```
HTTP Request
     │
     ▼
FastAPI App (main.py)
  5 Middleware layers
     │
     ▼
Route Layer (17 routers)
  /auth  /notebook  /upload  /chat  /agent
  /flashcard  /quiz  /ppt  /mindmap
  /podcast  /explainer  /search  /jobs
  /models  /websocket  /proxy  /health
     │
     ├──► Auth Service ──► PostgreSQL (Prisma)
     │
     ├──► Upload Route ──► File Validator ──► Material DB record
     │         └──► Background Job ──► Worker ──► Material Pipeline
     │                                              ├── OCR / Whisper / text extract
     │                                              ├── Chunking + Embedding (BAAI/bge-m3)
     │                                              └── ChromaDB upsert
     │
     ├──► Chat Route (5 paths)
     │         ├── RAG ──► SecureRetriever ──► ChromaDB ──► Reranker ──► LLM stream
     │         ├── AGENT ──► AgenticLoop (stream_agentic_loop)
     │         ├── WEB_RESEARCH ──► ResearchPipeline (5-phase SSE)
     │         ├── CODE_EXECUTION ──► Sandbox subprocess
     │         └── WEB_SEARCH ──► DuckDuckGo + LLM summary
     │
     ├──► Agent Route ──► LangGraph StateGraph
     │         (plan → route_and_execute → reflect → repeat or respond)
     │
     ├──► Flashcard / Quiz / Mindmap / PPT routes
     │         └── SecureRetriever ──► Generator ──► LLM ──► JSON response
     │
     ├──► Podcast Route ──► SessionManager ──► ScriptGenerator ──► TTS
     │         └── WebSocket ──► Q&A handler
     │
     ├──► Explainer Route ──► PPT screenshots ──► Script LLM ──► TTS ──► ffmpeg
     │
     └──► PostgreSQL (Prisma async) + ChromaDB
```

---

## 2. Technology Stack

| Category | Package | Version |
|---|---|---|
| Web Framework | FastAPI | 0.115.6 |
| ASGI Server | Uvicorn | 0.30.6 |
| ORM / DB Client | Prisma Python | 0.15.0 (async) |
| Vector DB | ChromaDB | 0.5.x |
| LLM Orchestration | LangChain | 0.2.16 |
| Agent Graphs | LangGraph | >= 0.2 |
| Embeddings | BAAI/bge-m3 (1024-dim) | via sentence-transformers |
| Reranker | BAAI/bge-reranker-large | via sentence-transformers + FlagEmbedding |
| LLM Providers | Ollama (local) / Google Gemini / NVIDIA API | — |
| Auth | python-jose (JWT) + passlib (bcrypt) | — |
| TTS | edge-tts | — |
| Audio Transcription | openai-whisper | — |
| Audio Processing | pydub + ffmpeg | — |
| PDF/OCR | PyMuPDF + pytesseract | — |
| Excel/CSV | openpyxl + pandas | — |
| Web Scraping | httpx + trafilatura + DuckDuckGo HTML | — |
| Background Work | asyncio.Task (built-in) | — |
| HTTP Client | httpx | — |
| Environment Config | Pydantic BaseSettings | 2.x |

### LLM Providers & Models

| Provider | Env Key | Default Model | Temperature Modes |
|---|---|---|---|
| Ollama (local) | `OLLAMA_BASE_URL` | `OLLAMA_MODEL` env var | structured=0.1, chat=0.2, creative=0.7, code=0.1 |
| Google Gemini | `GOOGLE_API_KEY` | `gemini-2.5-flash` | same modes |
| NVIDIA API | `NVIDIA_API_KEY` | `qwen/qwen3.5-397b-a17b` | same modes |
| Custom OpenLM | `OPENLM_BASE_URL` | configurable | same modes |

Active provider selected by `LLM_PROVIDER` env var (`OLLAMA` / `GOOGLE` / `NVIDIA` / `OPENLM`).

---

## 3. Project Structure

```
backend/
├── app/
│   ├── main.py               # App factory, lifespan, 17 routers registered
│   ├── core/
│   │   ├── config.py         # Pydantic BaseSettings — 50+ env vars, cached singleton
│   │   └── utils.py          # Shared utilities
│   ├── db/
│   │   ├── chroma.py         # ChromaDB client, collection factory
│   │   └── prisma_client.py  # Prisma async client singleton
│   ├── models/
│   │   ├── mindmap_schemas.py
│   │   ├── model_schemas.py  # Pydantic request/response models
│   │   └── shared_enums.py
│   ├── prompts/
│   │   ├── chat_prompt.txt
│   │   ├── code_generation_prompt.txt
│   │   ├── code_repair_prompt.txt
│   │   ├── data_analysis_prompt.txt
│   │   ├── flashcard_prompt.txt
│   │   ├── mindmap_prompt.txt
│   │   ├── podcast_qa_prompt.txt
│   │   ├── podcast_script_prompt.txt
│   │   ├── ppt_prompt.txt
│   │   ├── presentation_intent_prompt.txt
│   │   ├── presentation_strategy_prompt.txt
│   │   ├── quiz_prompt.txt
│   │   └── slide_content_prompt.txt
│   ├── routes/               # 17 routers (one per feature)
│   └── services/
│       ├── agent/            # LangGraph agent + agentic loop + tools
│       ├── auth/             # JWT auth service
│       ├── chat/             # service.py — save/load history, blocks, suggestions
│       ├── code_execution/   # sandbox.py, executor.py, security.py
│       ├── explainer/        # processor, tts, video_composer, script_generator
│       ├── flashcard/        # generator.py
│       ├── llm_service/      # llm.py — provider factory + streaming
│       ├── mindmap/          # generator
│       ├── podcast/          # session_manager, tts_service, script_generator, export
│       ├── ppt/              # generator, screenshot_service
│       ├── quiz/             # generator.py
│       ├── rag/              # pipeline, secure_retriever, embedder, reranker, context_builder
│       ├── research/         # pipeline.py
│       ├── text_processing/  # chunker, etc.
│       ├── job_service.py
│       ├── material_service.py
│       ├── notebook_service.py
│       ├── worker.py         # Background job processor
│       └── ws_manager.py     # WebSocket connection manager
├── prisma/
│   └── schema.prisma         # Full DB schema (20+ models)
├── data/
│   ├── chroma/               # ChromaDB persistent storage
│   ├── uploads/              # Raw uploaded files
│   ├── material_text/        # Extracted text cache
│   ├── models/               # Downloaded ML model weights
│   └── output/               # Generated files (PPT, podcast, explainer)
└── requirements.txt
```

---

## 4. Configuration & Environment Variables

All config is managed by a **Pydantic `BaseSettings`** class in `app/core/config.py`. A cached singleton is accessed via `get_settings()` (lru_cache).

### Key Settings Groups

**Database:**
```
DATABASE_URL              PostgreSQL DSN (required)
CHROMA_HOST               ChromaDB host (default: localhost)
CHROMA_PORT               ChromaDB port (default: 8003)
CHROMA_PERSIST_DIR        ChromaDB data path
CHROMA_COLLECTION_NAME    default: kepler_materials
```

**LLM:**
```
LLM_PROVIDER              OLLAMA | GOOGLE | NVIDIA | OPENLM
OLLAMA_BASE_URL           http://localhost:11434
OLLAMA_MODEL              llama3.2
GOOGLE_API_KEY            Gemini API key
GOOGLE_MODEL              gemini-2.5-flash
NVIDIA_API_KEY            NVIDIA NIM API key
NVIDIA_MODEL              qwen/qwen3.5-397b-a17b
```

**Retrieval:**
```
USE_RERANKER              true/false — enable BGE reranker
FINAL_K                   number of chunks in final context (default: 10)
EMBEDDING_MODEL           BAAI/bge-m3
RERANKER_MODEL            BAAI/bge-reranker-large
```

**Security:**
```
JWT_SECRET_KEY            required
JWT_ALGORITHM             HS256
ACCESS_TOKEN_EXPIRE_MINUTES   30
REFRESH_TOKEN_EXPIRE_DAYS     7
```

**Code Execution:**
```
MAX_CODE_REPAIR_ATTEMPTS     3 (agent self-healing retries)
```

**Features:**
```
SEARCH_SERVICE_URL        fallback web search endpoint
MATERIAL_UPLOAD_DIR       path for uploaded files
MATERIAL_TEXT_DIR         path for extracted text
CORS_ORIGINS              comma-separated allowed origins
```

---

## 5. Application Startup & Lifespan

`app/main.py` — `lifespan()` async context manager runs **6 startup steps** in order:

```
Step 1: Prisma connect     await prisma.connect()
Step 2: ChromaDB init      get_collection() — creates/opens collection, loads embedding model into RAM
Step 3: Worker start       asyncio.create_task(job_processor()) — background job loop
Step 4: Auth check         verify JWT secret is set
Step 5: Model warmup       optional: load embedding + reranker models
Step 6: Log config         print active LLM provider + key settings

On shutdown:
  - worker.graceful_shutdown() signal
  - await asyncio.sleep(1)   ← let in-flight requests finish
  - await prisma.disconnect()
```

### Router Registration (17 routers, all prefixed under `/api/v1`):

| Prefix | Router File | Purpose |
|---|---|---|
| `/auth` | routes/auth.py | Login, register, refresh token |
| `/notebooks` | routes/notebook.py | CRUD for notebooks |
| `/upload` | routes/upload.py | File/URL/text upload |
| `/materials` | routes/materials.py | Material management |
| `/chat` | routes/chat.py | All chat modes (RAG/Agent/Research/Code/Search) |
| `/agent` | routes/agent.py | LangGraph agent endpoint |
| `/flashcard` | routes/flashcard.py | Flashcard generation |
| `/quiz` | routes/quiz.py | Quiz generation |
| `/ppt` | routes/ppt.py | Presentation generation |
| `/mindmap` | routes/mindmap.py | Mind map generation |
| `/podcast` | routes/podcast_live.py | Podcast CRUD + generation |
| `/explainer` | routes/explainer.py | Explainer video pipeline |
| `/search` | routes/search.py | Federated search across types |
| `/jobs` | routes/jobs.py | Background job status |
| `/models` | routes/models.py | LLM model listing |
| `/ws` | routes/websocket_router.py | WebSocket connections |
| `/proxy` | routes/proxy.py | Internal proxy |
| `/health` | routes/health.py | Health check |

---

## 6. Middleware Stack

Applied in this order (outermost to innermost):

```
1. TrustedHostMiddleware      — blocks requests with invalid Host headers
2. CORSMiddleware             — configured origins from settings.CORS_ORIGINS
3. GZipMiddleware             — compress responses > 1KB
4. RequestLoggingMiddleware   — log method, path, status, elapsed ms
5. RateLimitMiddleware        — per-IP sliding window rate limiter
```

Global exception handlers add `Access-Control-Allow-Origin: *` to error responses to prevent browser CORS errors on 5xx.

---

## 7. Database Architecture

### PostgreSQL via Prisma — Full Schema

`prisma/schema.prisma` — all models with key fields:

**User**
```
id, email (unique), username, passwordHash
createdAt, updatedAt
→ hasMany: Notebook, Material, ChatSession, ChatMessage,
           RefreshToken, BackgroundJob, UserTokenUsage,
           ApiUsageLog, AgentExecutionLog,
           CodeExecutionSession, ResearchSession,
           PodcastSession, ExplainerVideo
```

**Notebook**
```
id, name, userId (FK → User)
createdAt, updatedAt
→ hasMany: Material (via join), ChatSession, ChatMessage, BackgroundJob
→ hasMany: GeneratedContent (flashcards, quizzes, PPTs, mindmaps)
```

**Material**
```
id, notebookId (FK), userId (FK)
title, filename, fileType, sourceType (file/url/youtube/text)
status: pending | processing | ocr_running | transcribing | embedding | completed | failed
fileSize, metadata (JSON — structured_data_path, structured_data_paths, page_count, etc.)
url (for web/youtube sources)
createdAt, updatedAt
```

**ChatSession**
```
id, notebookId, userId, title
createdAt, updatedAt
→ hasMany: ChatMessage
```

**ChatMessage**
```
id, notebookId, userId, chatSessionId
role: user | assistant
content (text)
agentMeta (JSON — intent, tools_used, confidence, etc.)
createdAt
→ hasMany: ResponseBlock
```

**ResponseBlock**
```
id, chatMessageId, blockIndex (ordering int), text (max 5000 chars)
— Each assistant message is split into markdown-aware blocks for block-level interactions
```

**GeneratedContent**
```
id, notebookId, userId
contentType: flashcard | quiz | mindmap | presentation
title, data (JSON — the actual generated content)
createdAt
→ manyToMany: Material (via GeneratedContentMaterial join)
```

**BackgroundJob**
```
id, userId, notebookId
jobType: material_processing
status: pending | processing | completed | failed
result (JSON — payload: material_id, file_path, source_type, etc.)
error (string on failure)
createdAt, updatedAt
```

**AgentExecutionLog**
```
id, userId, notebookId
intent, confidence, toolsUsed (array), stepsCount, tokensUsed, elapsedTime
createdAt
```

**CodeExecutionSession**
```
id, userId, sessionId, code, stdout, stderr, exitCode, timedOut
chartBase64, elapsedSeconds
createdAt
```

**ResearchSession**
```
id, userId, notebookId, sessionId
query, status, report (JSON), sourcesCount
createdAt
```

**PodcastSession**
```
id, userId, notebookId
mode: full | highlights | qa
topic, language, hostVoice, guestVoice
materialIds (array), status: created | generating | completed | failed
scriptData (JSON), audioPath
createdAt, updatedAt
→ hasMany: PodcastSegment, PodcastDoubt, PodcastBookmark, PodcastAnnotation
→ manyToMany: Material (PodcastSessionMaterial join)
```

**PodcastSegment**
```
id, sessionId, index
speaker: host | guest
text, audioPath, duration
```

**PodcastDoubt** — user Q&A questions asked during podcast playback
**PodcastBookmark** — user bookmarks at segment indices with optional notes
**PodcastAnnotation** — text notes at segment indices
**PodcastExport** — export records (mp3, transcript)

**ExplainerVideo**
```
id, userId, generatedContentId (FK → GeneratedContent)
status: pending | extracting | generating_scripts | generating_audio | composing | completed | failed
script (JSON), audioFiles (JSON), chapters (JSON)
outputPath, duration
createdAt, updatedAt
```

**UserTokenUsage** — per-user cumulative + daily token consumption

**ApiUsageLog** — per-request detailed audit log (endpoint, tokens, latency, model used)

**RefreshToken** — JWT refresh token storage with expiry timestamp

### ChromaDB — Vector Store

Collection name: `CHROMA_COLLECTION_NAME` (default `kepler_materials`)

**Every document chunk is stored with metadata:**
```json
{
  "user_id":       "uuid",
  "notebook_id":   "uuid",
  "material_id":   "uuid",
  "chunk_index":   0,
  "filename":      "lecture.pdf",
  "source_type":   "file",
  "is_structured": "false",
  "page_number":   1
}
```

`is_structured: "true"` marks CSV/Excel chunks — at retrieval time the summary placeholder is replaced with the full dataset text from disk (capped at 50,000 chars).

**Tenant isolation:** Every query carries `user_id` in the Chroma `where` filter. A post-query validation check rejects any chunk whose metadata `user_id` doesn't match the requester. Violations raise `TenantIsolationError` and are logged to `security.retrieval` logger.

**Embedding model:** BAAI/bge-m3 — 1024-dimensional dense embeddings, loaded once at startup and shared across all requests.

---

## 8. Authentication Flow

### Register: `POST /api/v1/auth/register`
```
1. Validate email uniqueness → prisma.user.find_unique(email)
2. Hash password → passlib.bcrypt.hash(password, rounds=12)
3. prisma.user.create({email, username, passwordHash})
4. Return {user_id, email, username}
```

### Login: `POST /api/v1/auth/login`
```
1. prisma.user.find_unique(email)
2. passlib.bcrypt.verify(plain_password, stored_hash)
3. On success:
   a. Create access token
      JWT HS256, exp = ACCESS_TOKEN_EXPIRE_MINUTES (default 30m)
      payload: {sub: user_id, exp: timestamp}
   b. Create refresh token
      JWT HS256, exp = REFRESH_TOKEN_EXPIRE_DAYS (default 7d)
      payload: {sub: user_id, type: "refresh", exp: timestamp}
   c. Store refresh token in prisma.refreshtoken.create({userId, token, expiresAt})
4. Return {access_token, refresh_token, token_type: "bearer"}
```

### Refresh: `POST /api/v1/auth/refresh`
```
1. Decode refresh token JWT → user_id
2. Look up RefreshToken in DB, verify not expired
3. Issue new access_token + new refresh_token
4. DELETE old RefreshToken record (rotation — one-time use)
5. INSERT new RefreshToken record
```

### Protected Routes — `Depends(get_current_user)`
```
1. Extract "Bearer <token>" from Authorization header
2. JWT decode → user_id
3. prisma.user.find_unique(user_id) — verify user exists
4. Return user object or raise HTTP 401
```

---

## 9. Material Upload & Processing Pipeline

### Upload Endpoint: `POST /api/v1/upload`

#### A) File Upload (multipart/form-data)
```
1. Receive UploadFile + notebook_id + optional material_ids
2. file_validator.validate(file):
   Allowed types: PDF, DOCX, TXT, MD, CSV, XLSX, MP3, MP4, WAV, PNG, JPG, JPEG
   Max size: configurable (default 100 MB)
3. Save file → data/uploads/{user_id}/{uuid4}/{filename}
4. prisma.material.create({
       notebookId, userId, title=filename, filename,
       fileType, status="pending", sourceType="file"
   })
5. prisma.backgroundjob.create({
       userId, notebookId, jobType="material_processing",
       status="pending",
       result={material_id, file_path, filename, source_type="file", user_id, notebook_id}
   })
6. job_queue.notify()  — wake background worker immediately
7. Return HTTP 202 {material_id, status: "pending"}
```

#### B) URL / YouTube Upload: `POST /api/v1/upload/url`
```
1. Receive {url, notebook_id}
2. source_type = "youtube" if "youtube.com" or "youtu.be" in url else "url"
3. prisma.material.create({status="pending", sourceType=source_type, url=url})
4. Create BackgroundJob with {source_type, url}
5. job_queue.notify()
6. Return HTTP 202 {material_id}
```

#### C) Text Upload: `POST /api/v1/upload/text`
```
1. Receive {text, title, notebook_id}
2. prisma.material.create({status="pending", sourceType="text"})
3. Create BackgroundJob with {source_type="text", text, title}
4. Return HTTP 202 {material_id}
```

---

## 10. Background Worker

`app/services/worker.py` — single `asyncio.Task` started at lifespan.

### Architecture

```
job_processor() [infinite loop, asyncio.Task]
    │
    ├── At startup: _recover_stuck_jobs()
    │     SQL: UPDATE background_jobs SET status='pending'
    │          WHERE status='processing' AND updated_at < NOW() - 30min
    │
    ├── Launch _cleanup_old_jobs() [sibling asyncio.Task]
    │     Every 24h: DELETE WHERE status IN (completed, failed) AND createdAt < 30d ago
    │
    └── Main loop (runs until _shutdown_event is set):
          1. Collect done tasks, surface exceptions
          2. Fetch up to (MAX_CONCURRENT_JOBS=5 - active) pending jobs:
             fetch_next_pending_job("material_processing"):
               SELECT ... WHERE status='pending' ORDER BY createdAt
               UPDATE SET status='processing'   (atomic claim)
          3. asyncio.create_task(_process_job(job)) for each fetched job
          4. If active_tasks >= 5:  asyncio.wait(FIRST_COMPLETED)
             If idle:               job_queue.wait(timeout=2.0s)
```

**Event-driven wake-up:** Upload routes call `job_queue.notify()` after creating a job, which sets an asyncio.Event — worker wakes immediately instead of waiting up to 2 seconds.

### Job Dispatch

`_process_job(job)` reads `result` JSON payload and dispatches:

```
source_type == "file"     → process_material_by_id(material_id, file_path, filename, user_id, notebook_id)
source_type == "url"      → process_url_material_by_id(material_id, url, user_id, notebook_id, "url")
source_type == "youtube"  → process_url_material_by_id(..., source_type="youtube")
source_type == "text"     → process_text_material_by_id(material_id, text_content, title, user_id, notebook_id)
```

On success: `UPDATE background_jobs SET status='completed'`
On failure: `UPDATE background_jobs SET status='failed', error=<exception message>`

**Auto-notebook rename (post-processing):** After `process_material_by_id` succeeds, if the notebook name starts with "notebook " or "untitled":
```
1. load_material_text(material_id) → extracted text from disk
2. generate_notebook_name(text[:2000]) → LLM call → short descriptive title
3. prisma.notebook.update(name=new_name)
```
Runs entirely in background — never blocks the HTTP response.

### Material Processing — File Pipeline

`process_material_by_id(material_id, file_path, filename, user_id, notebook_id)`:

```
Status transitions: pending → processing → [ocr_running | transcribing] → embedding → completed

Step 1: Extract text by file type
  ┌── PDF:
  │      Status → ocr_running
  │      PyMuPDF: fitz.open(file_path) → extract text from all pages
  │      If low text yield (scanned PDF):
  │        Render each page to PIL Image → pytesseract.image_to_string(image)
  │      text = concatenate all page texts
  │
  ├── DOCX:
  │      python-docx: Document(file_path)
  │      Extract paragraphs + table cells → text
  │
  ├── TXT / MD:
  │      Read bytes → decode UTF-8 → text
  │
  ├── CSV:
  │      pandas.read_csv(file_path)
  │      Save as parquet: data/output/generated/{material_id}.parquet
  │      Store structured_data_path in material.metadata
  │      Schema summary (column names, dtypes, row count) → stored as text in ChromaDB
  │      with is_structured="true" metadata tag
  │
  ├── XLSX:
  │      pandas.read_excel (all sheets, sheet_name=None)
  │      For each sheet: save as parquet
  │      Store {sheet_name: parquet_path} in structured_data_paths metadata
  │
  ├── MP3/WAV/M4A:
  │      Status → transcribing
  │      openai-whisper.load_model("base") [or configured size]
  │      whisper.transcribe(file_path) → {"text": "...", "segments": [...]}
  │      text = result["text"]
  │
  ├── MP4 (video):
  │      Status → transcribing
  │      ffmpeg extract audio → temp .wav file
  │      whisper.transcribe(wav_path) → text
  │
  └── PNG/JPG/JPEG:
         pytesseract.image_to_string(PIL.Image.open(file_path)) → text

Step 2: Save extracted text
  storage_service.save_material_text(material_id, text)
  → writes to data/material_text/{material_id}.txt

Step 3: Chunking
  Status → embedding
  text_processing/chunker.py:
    RecursiveCharacterTextSplitter(
        chunk_size=~500 tokens, chunk_overlap=~50 tokens,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
  → List[str] of overlapping text chunks

Step 4: Embedding + ChromaDB insert
  embedder.embed_and_store(chunks, material_id, user_id, notebook_id, filename):
    BAAI/bge-m3.encode(chunks, batch_size=32, normalize_embeddings=True)
    → float32 arrays, shape (num_chunks, 1024)
    collection.upsert(
        ids=[f"{material_id}_{i}" for i in range(N)],
        embeddings=list_of_vectors,
        documents=chunks,
        metadatas=[{
            "user_id": user_id, "notebook_id": notebook_id,
            "material_id": material_id, "chunk_index": i,
            "filename": filename, "source_type": "file",
            "is_structured": "true" if CSV/Excel else "false"
        }]
    )

Step 5: Update material
  prisma.material.update(
      where={id: material_id},
      data={status: "completed", metadata: JSON({page_count, char_count, chunk_count, ...})}
  )
```

### Material Processing — URL Pipeline

```
httpx.get(url, follow_redirects=True, timeout=30, headers=browser_headers)
trafilatura.extract(html_content, include_comments=False, include_tables=True)
If trafilatura fails: BeautifulSoup.get_text() fallback
text = cleaned article content
→ continue from Step 2 (save text + chunk + embed)
```

### Material Processing — YouTube Pipeline

```
Attempt yt-dlp transcript extraction first (fastest, no audio download)
If no transcript: yt-dlp download audio track → temp mp3
  openai-whisper.transcribe(mp3) → text
→ continue from Step 2
```

---

## 11. RAG Pipeline (Default Chat)

`app/services/rag/pipeline.py` — `stream_rag()` / `run_rag_pipeline_sync()`

Used when no `intent_override` is set (normal chat). This is the **fastest path** — zero agent overhead.

### Complete Flow

```
Client: POST /api/v1/chat  (no intent_override)
                │
                ▼
_route_rag(request, ids, session_id, current_user, start_time, debug)
                │
                ▼
stream_rag(query, material_ids, notebook_id, user_id, session_id)

EDGE CASES:
  No material_ids:
    count completed materials for user
    if count == 0: emit onboarding welcome message
    else:          emit "please select materials" message
    → yield token SSE, meta SSE, done SSE, return

Step 1: RETRIEVAL (blocking → asyncio.to_thread)
  secure_similarity_search_enhanced(
      user_id=user_id,
      query=query,
      material_ids=material_ids,
      notebook_id=notebook_id,
      use_mmr=True,
      use_reranker=settings.USE_RERANKER,
      return_formatted=True
  )

  Inside secure_similarity_search_enhanced:
    a. Cross-document detection:
       query.lower() contains CROSS_DOC_KEYWORDS:
         {'compare', 'comparison', 'difference', 'contrast', 'vs', 'versus', ...}
       → cross-doc: per_material_k=15, final_k=10
       → normal:    per_material_k=10, final_k=10

    b. Per-material ChromaDB query:
       For each material_id separately:
         collection.query(
             query_texts=[query],
             n_results=per_material_k,
             where={"$and": [{"user_id": user_id}, {"material_id": material_id}]}
         )
         → {documents: [[...]], metadatas: [[...]], distances: [[...]]}

    c. Tenant validation:
       For each result: assert metadata["user_id"] == user_id
       Drop violating chunks, log to security.retrieval logger

    d. Structured data expansion:
       For chunks with is_structured == "true":
         load_material_text(metadata["material_id"])
         Replace chunk text with full dataset text
         Cap at 50,000 chars

    e. Deduplication:
       Hash chunk content → discard exact duplicates

    f. MMR (Maximal Marginal Relevance):
       BAAI/bge-m3.encode([query] + all_chunks)
       Iteratively select chunks that maximize:
         λ * similarity(chunk, query) - (1-λ) * max_similarity(chunk, selected)
       λ = 0.7 (tunable)

    g. Reranking (if USE_RERANKER=true):
       BAAI/bge-reranker-large.predict([(query, chunk) for chunk in chunks])
       sort_by(cross_encoder_score, descending)

    h. Source diversity enforcement:
       Per material: min=1 chunk, max=3 chunks
       (Ensures no single document dominates the context)

    i. Final K selection: top FINAL_K (default 10) chunks

    j. format_context_with_citations(chunks, metadatas):
       Builds:
       "[SOURCE 1] (lecture.pdf, page 3)
       <chunk text>

       [SOURCE 2] (notes.txt)
       <chunk text>
       ..."

  Return: formatted context string

Step 2: PROMPT CONSTRUCTION
  get_chat_history(notebook_id, user_id, session_id) → last 10 messages
  format: "User: ...\nAssistant: ..."

  get_chat_prompt(context, formatted_history, query)
  Load chat_prompt.txt → fill template:
  "You are a helpful AI assistant. Use the following context...
   Context: {context}
   History: {history}
   Question: {query}
   Answer with inline citations like [SOURCE 1]..."

Step 3: LLM STREAMING
  llm = get_llm(mode="chat")  # temperature=0.2
  async for chunk in llm.astream(prompt):
      content = chunk.content
      yield _sse("token", {"content": content})
  full_response = "".join(all_chunks)

Step 4: CITATION VALIDATION
  from app.services.rag.citation_validator import validate_citations
  validate_citations(response=full_response, num_sources=chunks_used, strict=True)
  Warns in logs if model invents [SOURCE N] beyond actual count

Step 5: METADATA + DONE
  yield _sse("meta", {"intent": "RAG", "chunks_used": N, "elapsed": T})
  yield _sse("done", {"elapsed": T})

After stream (in route layer):
  _persist_and_finalize():
    chat_service.save_conversation(notebook_id, user_id, query, answer, session_id)
    → prisma.chatmessage.create x2 (user + assistant roles)
    chat_service.save_response_blocks(assistant_msg_id, answer)
    → _split_markdown_blocks(answer) → prisma.responseblock.create_many()
    chat_service.log_agent_execution(user_id, notebook_id, meta, elapsed)
    → prisma.agentexecutionlog.create()
  
  yield _sse("blocks", {"blocks": [{id, index, text}, ...]})
```

### SSE Events from RAG

| Event | `data` payload |
|---|---|
| `token` | `{"content": "<text chunk>"}` |
| `meta` | `{"intent": "RAG", "chunks_used": N, "elapsed": T}` |
| `done` | `{"elapsed": T}` |
| `error` | `{"error": "<message>"}` |
| `blocks` | `{"blocks": [{id, index, text}, ...]}` |

---

## 12. Chat Route — 5 Intent Paths

`POST /api/v1/chat` — request body:

```json
{
  "message": "user text",
  "notebook_id": "uuid",
  "material_ids": ["uuid1", "uuid2"],
  "intent_override": "AGENT|WEB_RESEARCH|CODE_EXECUTION|WEB_SEARCH|null",
  "stream": true,
  "session_id": "uuid (optional)"
}
```

**Session handling on every request:**
```
1. If session_id provided:
   prisma.chatsession.find_unique(session_id)
   Validate: session.userId == current_user.id AND session.notebookId == request.notebook_id
   If not valid: raise HTTP 403

2. Auto-title untitled sessions on first message:
   if session.title in ("", "New Chat"):
     new_title = message[:30] + ("..." if len > 30)
     prisma.chatsession.update(title=new_title)
```

**Routing — zero-overhead direct dispatch (no LLM for intent):**
```python
intent = request.intent_override.value if request.intent_override else "RAG"

if   intent == "AGENT"          → _route_agent()
elif intent == "WEB_RESEARCH"   → _route_web_research()
elif intent == "CODE_EXECUTION" → _route_code_execution()
elif intent == "WEB_SEARCH"     → _route_web_search()
else                            → _route_rag()   # default fastest path
```

### Path 1: RAG (default) — See Section 11

### Path 2: AGENT
```
_route_agent() → stream_agentic_loop(query, material_ids, notebook_id, user_id, session_id)
  SSE stream from open-loop agentic system (see Section 13)
  Collect full_response from "type: token" events
  Collect agent_meta from "type: done" event
  _persist_and_finalize(answer=full_response, meta={...agent_meta, intent:"AGENT"})
  yield "event: blocks" with persisted ResponseBlocks
```

### Path 3: WEB_RESEARCH
```
_route_web_research() → stream_research(query, user_id, notebook_id, session_id)
  5-phase SSE stream (see Section 14)
  Collect full_response from "event: token" lines
  Collect citations from "event: citations" data
  _persist_and_finalize(meta={intent:"WEB_RESEARCH", sources_count:N})
  yield "event: blocks"
```

### Path 4: CODE_EXECUTION
```
_route_code_execution():
  1. llm = get_llm(temperature=0.1)
  2. prompt = get_code_generation_prompt(request.message)
     from code_generation_prompt.txt
  3. code = await llm.ainvoke(prompt)
     Strip markdown fences (```python ... ```)
  4. yield "event: code_generating" {"code": code}
  5. result = await run_in_sandbox(code)
     [subprocess execution, 15s hard timeout — see Section 15]
  6. yield "event: code_result" {
         "stdout": ..., "stderr": ...,
         "exit_code": ..., "timed_out": ...,
         "elapsed_seconds": ...
     }
  7. Build answer:
     "```python\n{code}\n```\n\n**Output:**\n```\n{stdout}\n```"
     + "\n\n**Error:**\n```\n{error}\n```" if error
  8. _persist_and_finalize(answer, meta={intent:"CODE_EXECUTION", has_error:bool})
  9. Stream answer in 100-char chunks: yield "event: token" per chunk
  10. yield "event: done"
```

### Path 5: WEB_SEARCH
```
_route_web_search():
  1. tools_registry._web_search_impl(query, n_results=5):
     DuckDuckGo HTML search → [{title, snippet, url}]
  2. yield "event: search_results" {"results": [...]}
  3. Format context:
     "[1] Title: ...\nSnippet: ...\nURL: ...\n\n..."
  4. llm.ainvoke(summarize prompt):
     "Answer based on these results... use inline [n] citations"
  5. _persist_and_finalize(answer, meta={intent:"WEB_SEARCH", results_count:N})
  6. Stream answer in 100-char chunks as "event: token"
  7. yield "event: done"
```

---

## 13. Agent System

Two separate agent implementations:

- **`graph.py`** — LangGraph `StateGraph`, invoked by `POST /api/v1/agent`
- **`agentic_loop.py`** — Open-loop system, invoked by `/chat` with `intent_override=AGENT`

### LangGraph StateGraph (graph.py)

```
StateGraph topology:
  START ──► route_and_execute ──► reflect ──► (conditional)
                   ▲                 │
                   └── "continue" ◄──┘
                                     │
                                "respond" ──► END (LLM generates final answer)
```

**AgentState TypedDict** — all 30+ fields:
```python
# Input
user_message: str
notebook_id: str
user_id: str
material_ids: List[str]
session_id: str

# Intent
intent: str
intent_confidence: float
intent_override: str

# Planning
plan: List[dict]        # [{tool, args, label, conditional, uses_previous_output}]
current_step: int

# Execution
selected_tool: str
tool_input: dict
tool_results: List[ToolResult]
needs_retry: bool
iterations: int
step_retries: int
total_tokens: int
total_tool_calls: int

# Output
response: str
agent_metadata: dict

# Context
rag_context: str
chat_history: str
workspace_files: List[str]
generated_files: List[str]

# Code execution context
last_stdout: str
last_stderr: str
analysis_context: str
code_vars: dict
edit_history: List[dict]
step_log: List[dict]
repair_attempts: int
```

**Safety constants:**
```
MAX_AGENT_ITERATIONS = 7     graph loop iterations
MAX_TOOL_CALLS = 10          total tool calls across all iterations
TOKEN_BUDGET = 12,000        cumulative tokens (context + response)
INTENT_MIN_CONFIDENCE = 0.6  minimum confidence for intent classification
_MAX_STEP_RETRIES = 2        retries per plan step
_MIN_USEFUL_OUTPUT_LEN = 50  chars — below this is considered "empty"
```

### Open-Loop Agentic Loop (agentic_loop.py)

Used by `/chat` with `intent_override=AGENT`. Separate from the LangGraph system.

**AgentLoopState:**
```python
query: str
material_ids: List[str]
notebook_id: str
user_id: str
session_id: str
plan: List[dict]
tool_history: List[ToolCall]
artifacts: List[Artifact]
iteration: int              # max 10
final_response: str
```

**ToolCall record:**
```python
tool: str
args: dict
reasoning: str
result_summary: str
duration_ms: float
success: bool
error: str
```

**Artifact record:**
```python
type: str       # "chart" | "table" | "file"
index: int
data: str       # base64-encoded PNG for charts
filename: str
url: str
mime: str
```

**Available tools in agentic loop:**
```
rag_search          semantic search in user's materials
python_executor     LLM code generation → subprocess execution
file_generator      generate CSV/TXT/JSON downloadable files
web_search          DuckDuckGo quick search
code_repair         fix broken code using code_repair_prompt.txt
flashcard_generator create flashcard set from materials
quiz_generator      create quiz from materials
mindmap_generator   create mind map from materials
ppt_generator       redirect to Studio panel (full PPT needs UI)
```

**`stream_agentic_loop()` SSE events:**
```
type: "plan"         {steps: [...]}                 — initial plan
type: "tool_start"   {tool, reasoning, step_index}  — before tool call
type: "code_generated" {code}                       — when python_executor generates code
type: "code_stdout"  {line}                         — live stdout stream
type: "tool_result"  {tool, summary, duration_ms, success, error?}
type: "artifact"     {type, index, data, filename, mime}
type: "token"        {content}                      — final response streaming
type: "done"         {iterations, tool_count, artifacts: [...], response}
type: "error"        {error}
```

### Router Node

`app/services/agent/router.py` — `route_and_execute(state: AgentState) → AgentState`

Reads `state.plan[state.current_step]` and dispatches the tool.

**Step configuration schema:**
```json
{
  "tool": "rag_tool",
  "args": {"query": "explain photosynthesis"},
  "label": "🔍 Searching materials",
  "conditional": "if_previous_empty",
  "uses_previous_output": true
}
```

**Conditional skip (`"conditional": "if_previous_empty"`):**
```
If the previous tool result:
  - exists AND
  - result.success == True AND
  - len(result.output) >= MIN_USEFUL_OUTPUT_LEN (50 chars)
Then: skip this step, advance current_step
Use case: skip web research if RAG already found sufficient context
```

**Tool chaining (`"uses_previous_output": true`):**
```
Inject previous tool's output into args as "previous_context"
Use case: DATA_ANALYSIS flow:
  Step 1: rag_tool → "Here are the key data columns..."
  Step 2: python_tool(previous_context="Here are the key data columns...")
          → LLM uses context when generating analysis code
```

**SSE labels emitted during routing:**
```
"🔍 Searching materials"          → rag_tool
"🌐 Researching online"           → research_tool
"🐍 Writing & running Python code" → python_tool / code_executor
"📝 Generating quiz"              → quiz_tool
"🃏 Creating flashcards"          → flashcard_tool
"📊 Building presentation"        → ppt_tool
"🧠 Analyzing dataset structure"  → data_profiler
"📄 Generating file"              → file_generator
```

**Special direct dispatch (bypass tools registry):**

`data_profiler`:
```
Load parquet/CSV files for each material_id
pandas: shape, dtypes, df.describe(), missing value counts, top-5 samples
Emit adispatch_custom_event("data_profile", {profile_data})
Return profile as ToolResult
```

`file_generator`:
```
LLM generates file content (CSV, TXT, JSON, Markdown) from request
Save to data/output/generated/{uuid}.{ext}
Emit adispatch_custom_event("file_generated", {filename, download_path})
Return ToolResult with download URL
```

### Reflection Node

`app/services/agent/reflection.py` — `reflect(state: AgentState) → AgentState`

Called after every `route_and_execute`. Decides whether to continue or generate final response.

**Full decision tree:**
```
1. state.iterations += 1

2. Hard limit checks → respond immediately:
   a. state.iterations >= MAX_AGENT_ITERATIONS (7)
   b. state.total_tool_calls >= MAX_TOOL_CALLS (10)
   c. state.total_tokens >= TOKEN_BUDGET (12,000)
   Any of the above → state.response = "Hard limit reached, generating partial response"

3. Self-healing code repair:
   Conditions ALL must be true:
   - last tool was in _CODE_TOOLS: {"code_executor", "file_generator", "python_tool"}
   - last tool result: success == False
   - state.last_stderr is non-empty
   - state.repair_attempts < MAX_CODE_REPAIR_ATTEMPTS (settings, default 3)
   
   Action:
   - repair_code(stderr=last_stderr, original_code=last_code):
       Load code_repair_prompt.txt
       LLM structured call → returns {fixed_code, explanation}
   - Update plan step with fixed_code
   - state.repair_attempts += 1
   - state.needs_retry = True
   
   → return "continue" (retry the same step with repaired code)

4. Step retry logic:
   If state.needs_retry AND state.step_retries < _MAX_STEP_RETRIES (2):
     state.step_retries += 1
     reset needs_retry = False
     → return "continue" (same step index)

5. Dynamic fallback injection:
   If state.intent == "QUESTION" AND state.rag_context is empty/failed:
     Insert research_tool step at current_step + 1 in plan
     (Web fallback when RAG finds nothing)

6. Advance or respond:
   state.current_step += 1
   If current_step >= len(plan):
     → return "respond"  → END node → LLM generates final response
   Else:
     → return "continue" → route_and_execute next step
```

**`should_continue(state)` — LangGraph conditional edge:**
```python
def should_continue(state: AgentState) → Literal["continue", "respond"]:
    if state.response or state.iterations >= MAX_AGENT_ITERATIONS:
        return "respond"
    if state.current_step >= len(state.plan):
        return "respond"
    return "continue"
```

### Tools Registry

`app/services/agent/tools_registry.py`

**Registry pattern:**
```python
_TOOLS: Dict[str, Callable] = {}

def register_tool(name: str, fn: Callable) → None
def get_tool(name: str) → Callable
def get_tools_for_intent(intent: str) → Dict[str, Callable]
def list_tools() → List[str]
```

`ToolResult` TypedDict:
```python
success: bool
output: str          # human-readable; truncated to 500 chars for LLM planning context
metadata: dict       # full structured data — not truncated, used for response rendering
tool_name: str
tokens_used: int
error: Optional[str]
```

`compress_tool_result(result)`: produces a planning-context-safe version with output truncated to 500 chars.

#### rag_tool — Detailed Flow
```
1. asyncio.to_thread(
       secure_similarity_search_enhanced,
       user_id, query, material_ids, notebook_id,
       use_mmr=True, use_reranker=settings.USE_RERANKER,
       return_formatted=True
   )
   [runs in thread pool, blocking ChromaDB + embedding call]
2. If no context: return ToolResult(success=False, output="No relevant information found")
3. generate_rag_response(query, context):
   llm.invoke(rag_answer_prompt) → answer string
4. Return ToolResult(success=True, output=answer, metadata={context_chunks, sources})
```

#### quiz_tool — Detailed Flow
```
1. asyncio.to_thread(
       secure_similarity_search_enhanced,
       query="Generate comprehensive quiz questions covering the key concepts",
       ...
   )
2. asyncio.to_thread(generate_quiz, context):
   quiz_prompt.txt → LLM structured call → parse JSON
   → {title, questions: [{question, options, correct_answer, explanation}]}
3. Return ToolResult(
       success=True,
       output=f"Generated **{title}** with {N} question(s)",
       metadata={title, questions}
   )
```

#### flashcard_tool — Detailed Flow
```
1. asyncio.to_thread(
       secure_similarity_search_enhanced,
       query="Generate comprehensive flashcards covering key concepts and definitions",
       ...
   )
2. asyncio.to_thread(generate_flashcards, context):
   flashcard_prompt.txt → LLM → {title, flashcards: [{front, back}]}
3. Return ToolResult(metadata={title, flashcards})
```

#### ppt_tool — Redirect Pattern
```
Returns ToolResult(
    success=True,
    output="Please use the Studio panel to configure and generate your presentation.",
    metadata={"action": "open_studio", "topic": topic}
)
No actual PPT generation here — full PPT requires multi-step Studio UI interaction.
```

#### python_tool — Detailed Flow
```
1. Emit adispatch_custom_event("code_generating", {"tool": "python_tool"})

2. Load material data files:
   For each material_id:
     material = get_material_for_user(material_id, user_id)
     meta = json.loads(material.metadata)
     
     structured_data_paths (Excel): {sheet_name: parquet_path}
       → parquet_files.append({name: f"{basename}_{sheet}.parquet", path: path})
     
     structured_data_path (CSV): single parquet path
       → parquet_files.append({name: f"{basename}.parquet", path: path})
     
     Fallback (raw CSV, no parquet): get_material_text(mid, user_id)
       → csv_files.append({filename, content})

3. Validate files (schema-only read, no data load):
   pandas.read_parquet(path, columns=None).head(0) — validates structure
   pandas.read_csv(io.StringIO(content), nrows=0)
   Skip unreadable files with warning log

4. If no readable files: return ToolResult(success=False, error="data_validation_failed")

5. on_stdout callback: adispatch_custom_event("code_stdout", {"line": line})
   on_code_generated: adispatch_custom_event("code_generated", {"code": code})

6. generate_and_execute(
       user_query=query,
       csv_files=validated_csv,
       parquet_files=validated_parquet,
       timeout=15,
       on_stdout_line=on_stdout,
       additional_context=kwargs.get("previous_context", ""),
       on_code_generated=on_code_generated
   )

7. If intent == "DATA_ANALYSIS" and success:
   Extra LLM call (mode="chat") with analysis explanation prompt:
   "Analyze output and provide Executive Summary, Key Findings, tables, Recommendations"
   → Emit as additional context in ToolResult

8. Return ToolResult with:
   - stdout, chart_base64 (if matplotlib)
   - success, elapsed
   - metadata: {code, explanation, chart_base64}
```

---

## 14. Web Research Pipeline

`app/services/research/pipeline.py` + `app/services/agent/subgraphs/research_graph.py`

Used by `/chat` WEB_RESEARCH path and `research_tool` in the agent.

**Constants:**
```
MAX_SEARCH_QUERIES = 10
MAX_TOTAL_URLS = 15
MAX_TIME_SECONDS = 45
```

### `stream_research()` — Complete 5-Phase Flow

```
Phase 1: planning
  Emit: event: phase | data: {"phase": "planning", "status": "Generating search queries..."}
  
  LLM call (temperature=0.3):
    Prompt: "Generate 5-10 targeted search queries for: {user_query}"
    Parse JSON array of query strings
    Fallback: use [user_query] if LLM fails or JSON parse error

Phase 2: searching
  Emit: event: phase | data: {"phase": "searching", "status": "Searching the web..."}
  
  _execute_searches(queries):
    For each query (serialized to avoid DDG rate-limiting, ~0.5s delay between):
      httpx.get(
          "https://html.duckduckgo.com/html/",
          params={"q": query},
          headers={"User-Agent": browser_user_agent},
          timeout=10s
      )
      BeautifulSoup parse → extract result URLs, titles, snippets
      Deduplicate URLs across queries
      Stop when MAX_TOTAL_URLS=15 reached
    Return: {url: {title, snippet}} for up to 15 URLs

Phase 3: extracting
  Emit: event: phase | data: {"phase": "extracting", "status": "Reading web pages..."}
  
  _extract_content(url_map):
    async with httpx.AsyncClient(timeout=10) as client:
      tasks = [client.get(url) for url in urls]  # concurrent
      results = await asyncio.gather(*tasks, return_exceptions=True)
    
    For each result:
      trafilatura.extract(html, include_tables=True, include_links=False)
      Fallback: BeautifulSoup.get_text(separator=" ", strip=True)
      Filter: discard if len(text) < 100 chars
    
    Return: [{url, title, snippet, content}]

Phase 4: clustering
  Emit: event: phase | data: {"phase": "clustering", "status": "Organizing sources..."}
  Currently pass-through — placeholder for future semantic grouping
  Return sources unchanged

Phase 5: writing
  Emit: event: phase | data: {"phase": "writing", "status": "Writing research report..."}
  
  Build context string:
    For each source (up to 15):
      "[{i+1}] **{title}**\nURL: {url}\n{content[:500]}\n\n"
  
  LLM astream(research_synthesis_prompt):
    Full prompt: "Based on these {N} sources, write a comprehensive research report
                  about: {user_query}. Cite sources inline as [1], [2], etc."
    
    async for chunk in llm.astream(prompt):
      yield f"event: token\ndata: {json.dumps({'content': chunk.content})}\n\n"
  
  Emit citations:
    yield f"event: citations\ndata: {json.dumps({'citations': [...]})}\n\n"

Final:
  yield "event: done\ndata: {'sources_count': N}\n\n"

DB record:
  prisma.researchsession.create({
      userId, notebookId, sessionId,
      query, status="completed",
      report=JSON({sources, synthesis}),
      sourcesCount=N
  })
```

---

## 15. Code Execution Sandbox

`app/services/code_execution/sandbox.py`

### Security Layers (Innermost to Outermost)

```
Layer 1: Static code validation (security.py) — BEFORE execution
  Blocked modules: os, sys, subprocess, socket, ctypes, importlib, shutil, pickle
  Blocked patterns: __import__, eval(, exec(, open( for write modes
  Blocked: network calls (requests, urllib, httpx inside user code)
  Allowed: pandas, numpy, matplotlib, scikit-learn, seaborn, math, json, re, datetime

Layer 2: Subprocess isolation
  Command: [sys.executable, "_run.py"]  (same venv → all packages available)
  Working directory: /tmp/kepler_sandbox_{uuid}/
  Sanitized environment (strips all credentials):
    DATABASE_URL, JWT_SECRET_KEY, GOOGLE_API_KEY, NVIDIA_API_KEY,
    AWS_SECRET_ACCESS_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY
  Thread count control: OPENBLAS_NUM_THREADS=4, MKL_NUM_THREADS=4, OMP_NUM_THREADS=4

Layer 3: OS resource limits (Linux, preexec_fn)
  RLIMIT_CPU:   soft=30s, hard=60s  (prevents infinite CPU loops)
  RLIMIT_FSIZE: 50 MB               (prevents disk exhaustion)
  RLIMIT_NOFILE: 128                (limits file descriptor leaks)
  Note: RLIMIT_AS NOT set (numpy/pandas need virtual address space)
  Note: RLIMIT_NPROC NOT set (OpenBLAS needs threads on Linux)

Layer 4: Asyncio timeout
  asyncio.wait_for(process.communicate(), timeout=15s)
  On timeout: process.kill() → return ExecutionResult(timed_out=True)
```

### Wrapper Script (injected around user code)

```python
# --- Injected header ---
import matplotlib; matplotlib.use("Agg")  # non-interactive, no display needed
import matplotlib.pyplot as _plt_orig

def _capture_show(*args, **kwargs):
    buf = io.BytesIO()
    _plt_orig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
    b64 = base64.b64encode(buf.read()).decode()
    print(f"__CHART_BASE64__{b64}__END_CHART__")  # captured in stdout
    _plt_orig.clf(); _plt_orig.close("all")

_plt_orig.show = _capture_show
import matplotlib.pyplot as plt; plt.show = _capture_show

# --- User code runs here ---
{user_code}
```

### Execution Paths

**Streaming (on_stdout_line callback provided):**
```
_stream_stdout():
  async for raw_line in process.stdout:
    await on_stdout_line(decoded_line)   # live stream to SSE/WebSocket

_collect_stderr():
  data = await process.stderr.read(MAX_OUTPUT_SIZE=1MB)

asyncio.wait_for(gather(_stream_stdout, _collect_stderr), timeout=15)
```

**Buffered (no callback):**
```
stdout_bytes, stderr_bytes = await asyncio.wait_for(
    process.communicate(), timeout=15
)
```

**Chart extraction from stdout:**
```python
if "__CHART_BASE64__" in stdout:
    match = re.search(r"__CHART_BASE64__(.+?)__END_CHART__", stdout)
    chart_base64 = match.group(1).strip()
    stdout = re.sub(r"__CHART_BASE64__.+?__END_CHART__", "", stdout).strip()
```

**ExecutionResult:**
```python
stdout: str            # clean stdout (chart marker removed)
stderr: str            # error output
exit_code: int         # process exit code
timed_out: bool        # True if asyncio timeout hit
chart_base64: str      # base64 PNG if matplotlib figure detected
elapsed_seconds: float # wall clock time
error: str             # exception message if subprocess failed to start
```

**Cleanup:** script file and temp directory deleted in `finally` block.

---

## 16. Flashcard Generation

### Route: `POST /api/v1/flashcard/generate`

```
Request: {notebook_id, material_ids, topic?, num_cards?}

1. Validate material ownership (each material must belong to user + notebook)
2. RAG retrieval:
   secure_similarity_search_enhanced(
       query="Generate comprehensive flashcards covering key concepts and definitions",
       material_ids, use_mmr=True, use_reranker=True, return_formatted=True
   )
3. generate_flashcards(context, num_cards?):
   flashcard_prompt.txt → LLM structured call (temperature=0.1):
     "Create N study flashcards from the following content.
      Return JSON: {title, flashcards: [{front, back}]}"
   parse_json_robust(response)
   → {title, flashcards: [{front: "Q?", back: "A."}, ...]}
4. prisma.generatedcontent.create({
       notebookId, userId,
       contentType="flashcard",
       title=result.title,
       data=json.dumps(result)
   })
5. prisma.generatedcontentmaterial.create_many(
       [{generatedContentId, materialId} for each material]
   )
6. Return {id, title, flashcards: [...], material_ids, created_at}
```

### Route: `GET /api/v1/flashcard/{content_id}`
```
prisma.generatedcontent.find_unique(id, include={materials: true})
Verify content.userId == current_user.id
Return {id, title, flashcards: [...], material_ids}
```

### Route: `DELETE /api/v1/flashcard/{content_id}`
```
Delete GeneratedContentMaterial join records
Delete GeneratedContent record
Return {deleted: true}
```

### Route: `GET /api/v1/flashcard?notebook_id=...`
```
prisma.generatedcontent.find_many(
    where={notebookId, userId, contentType="flashcard"}
)
Return list of flashcard sets
```

---

## 17. Quiz Generation

### Route: `POST /api/v1/quiz/generate`

```
Request: {notebook_id, material_ids, topic?, num_questions?, difficulty?: easy|medium|hard}

1. secure_similarity_search_enhanced(
       query="Generate comprehensive quiz questions covering the key concepts",
       material_ids, use_mmr=True
   )
2. generate_quiz(context, num_questions?, difficulty?):
   quiz_prompt.txt → LLM structured call (temperature=0.1):
     "Create N quiz questions at {difficulty} level.
      Mix: multiple choice (4 options), true/false, short answer.
      Return JSON: {title, questions: [{
          question, type, options?, correct_answer, explanation
      }]}"
   parse_json_robust(response)
3. Save to GeneratedContent (contentType="quiz")
4. Return {id, title, questions: [...], material_ids}
```

---

## 18. Presentation (PPT) Generation

### Route: `POST /api/v1/ppt/generate`

Multi-stage LLM pipeline:

```
Request: {notebook_id, material_ids, topic?, num_slides?, theme?, audience?}

Stage 1: Intent Classification
  LLM + presentation_intent_prompt.txt:
  "Classify this presentation intent: {topic}"
  → {intent: "educational|business|technical", key_themes: [...], target_audience: ...}

Stage 2: Strategy / Outline
  LLM + presentation_strategy_prompt.txt:
  Input: intent + extracted RAG context (lightweight retrieval)
  → {
      outline: [{title, key_points: [...], slide_type: "title|content|comparison|conclusion"}],
      suggested_slides: N,
      narrative_arc: "..."
    }

Stage 3: Full RAG Context
  secure_similarity_search_enhanced(topic or general, material_ids, use_reranker=True)

Stage 4: Per-Slide Content Generation
  For each slide in outline (concurrent LLM calls):
    slide_content_prompt.txt:
    "Generate rich content for slide '{title}'. Key points: {key_points}. Context: {rag_context}"
    → {
        title, bullets: ["..."], notes: "speaker notes",
        suggested_layout: "two_column|image_right|full_text"
    }

Stage 5: Assemble Presentation Data
  {
    title: "Main title",
    theme: selected_theme,
    slides: [{
        title, bullets, notes,
        html: "<div>rendered HTML for screenshot</div>",
        layout: suggested_layout
    }]
  }

Stage 6: Persist
  prisma.generatedcontent.create({
      contentType="presentation",
      data=json.dumps(presentation_data)
  })

Stage 7: Return
  {id, title, slides: [...], download_url?, created_at}
```

---

## 19. Mind Map Generation

### Route: `POST /api/v1/mindmap/generate`

```
Request: {notebook_id, material_ids, topic?, depth?}

1. secure_similarity_search_enhanced(topic query, material_ids)
2. generate_mindmap(context, topic, depth?):
   mindmap_prompt.txt → LLM structured call:
   "Create a hierarchical mind map for: {topic}"
   → JSON tree:
   {
     "title": "...",
     "root": {
       "label": "Central Topic",
       "id": "root",
       "children": [
         {"label": "Branch 1", "id": "b1", "children": [
           {"label": "Leaf 1.1", "id": "l1"},
           {"label": "Leaf 1.2", "id": "l2"}
         ]},
         {"label": "Branch 2", "id": "b2", "children": [...]}
       ]
     }
   }
3. prisma.generatedcontent.create({contentType="mindmap", data=JSON})
4. Return {id, title, root: {...}}
```

---

## 20. Podcast Live System

`app/services/podcast/` — multi-service architecture with WebSocket support.

### Session Lifecycle States

```
created ──► generating ──► completed
                      └──► failed
```

### Route: `POST /api/v1/podcast/sessions` — Create Session

```
Request: {notebook_id, mode, topic?, language?, host_voice?, guest_voice?, material_ids?}

1. validate_voice(host_voice, language) — check against edge-tts voice list
2. get_default_voices(language):
   en: host=en-US-GuyNeural, guest=en-US-JennyNeural
   (language-specific defaults from voice_map.py)
3. prisma.podcastsession.create({
       userId, notebookId, mode, topic, language,
       hostVoice, guestVoice, materialIds=material_ids or [],
       status="created"
   })
4. Return serialized session dict
```

### Route: `POST /api/v1/podcast/sessions/{id}/generate` — Start Generation

```
1. Update: status "created" → "generating"
   prisma.podcastsession.update({status: "generating"})
2. ws_manager.broadcast(user_id, {event: "podcast_status", status: "generating"})

3. RAG context:
   secure_similarity_search_enhanced(
       topic or "main themes and key points",
       material_ids
   )

4. generate_podcast_script(context, topic, mode, language):
   podcast_script_prompt.txt → LLM (temperature=0.7, creative mode):
   "Create an engaging {mode} podcast between a host and guest about: {topic}.
    Use this content: {context}
    Return JSON: {
       title, description,
       segments: [{speaker: 'host'|'guest', text: '...'}]
    }"
   parse_json_robust(response)
   → {title, description, segments: [{speaker, text}]}

5. synthesize_all_segments(session_id, segments, host_voice, guest_voice):
   Create output directory: data/output/podcast/{session_id}/
   
   For each segment in segments:
     voice = host_voice if speaker=="host" else guest_voice
     output_path = data/output/podcast/{session_id}/segment_{i}.mp3
     
     edge-tts: Communicate(text=segment.text, voice=voice)
     await communicate.save(output_path)
     
     duration = pydub.AudioSegment.from_mp3(output_path).duration_seconds
     
     prisma.podcastsegment.create({
         sessionId, index=i,
         speaker, text, audioPath=output_path, duration
     })
   
   ws_manager.broadcast(user_id, {
       event: "podcast_progress",
       completed: i+1, total: len(segments)
   })

6. Concatenate (ffmpeg concat demuxer):
   Create concat_list.txt: "file 'segment_0.mp3'\nfile 'segment_1.mp3'\n..."
   ffmpeg -f concat -safe 0 -i concat_list.txt -c copy full_podcast.mp3
   final_path = data/output/podcast/{session_id}/full_podcast.mp3

7. Update session:
   prisma.podcastsession.update({
       status: "completed",
       audioPath: final_path,
       scriptData: json.dumps({title, description, segments})
   })

8. ws_manager.broadcast(user_id, {event: "podcast_ready", session_id, audio_path: final_path})
```

### Route: `GET /api/v1/podcast/sessions/{id}` — Full State

```
Returns: {
  id, status, mode, topic, language, hostVoice, guestVoice, materialIds,
  scriptData, audioPath, createdAt, updatedAt,
  segments: [{index, speaker, text, audioPath, duration}],
  doubts: [{segmentIndex, question, answer, createdAt}],
  bookmarks: [{segmentIndex, note, createdAt}],
  annotations: [{segmentIndex, text, createdAt}]
}
```

### WebSocket: Podcast Q&A — `WS /api/v1/ws/podcast/{session_id}`

```
Client sends WebSocket message: {
    "type": "doubt",
    "question": "What does the host mean by X?",
    "segment_index": 3
}

Server:
1. Validate session ownership
2. Load segment: prisma.podcastsegment.find_first(where={sessionId, index=segment_index})
3. Build context from segment.text + nearby segments (±2)
4. qa_service.answer_doubt(question, context, session_id):
   podcast_qa_prompt.txt → LLM astream:
   "Based on segment {N}: '{segment_text}',
    answer: {question}"
   
   For each streaming chunk:
     ws.send_text(json.dumps({"type": "answer_chunk", "content": chunk.content}))
5. Persist:
   prisma.podcastdoubt.create({sessionId, segmentIndex, question, answer=full_answer})
6. satisfaction_detector.check(question, answer) → bool
   If not satisfied: ws.send_text({"type": "follow_up_suggestion", ...})
7. ws.send_text({"type": "answer_done"})
```

### Bookmarks & Annotations

```
POST /api/v1/podcast/{session_id}/bookmarks
  {segment_index, note?}
  → prisma.podcastbookmark.create({sessionId, segmentIndex, note})

GET /api/v1/podcast/{session_id}/bookmarks
  → prisma.podcastbookmark.find_many(where={sessionId}, order={segmentIndex: asc})

POST /api/v1/podcast/{session_id}/annotations
  {segment_index, text}
  → prisma.podcastannotation.create({sessionId, segmentIndex, text})
```

### Export: `POST /api/v1/podcast/{session_id}/export`

```
{format: "mp3" | "transcript"}

mp3:
  Validate audioPath exists on disk
  FileResponse(audioPath, media_type="audio/mpeg", filename="{title}.mp3")

transcript:
  Load all segments ordered by index
  Format: "**Host:** {text}\n\n**Guest:** {text}\n\n..."
  Return as text/plain download

prisma.podcastexport.create({sessionId, format, path=audioPath})
```

---

## 21. Explainer Video Pipeline

`app/services/explainer/processor.py`

### Route: `POST /api/v1/explainer/generate`

```
Request: {generated_content_id}  ← must be a "presentation" GeneratedContent

1. prisma.generatedcontent.find_unique(id)
2. Validate: content.userId == current_user.id
3. Validate: content.contentType == "presentation"
4. prisma.explainervideo.create({
       userId, generatedContentId, status="pending"
   })
5. asyncio.create_task(process_explainer_video(explainer_id, content.data))
6. Return HTTP 202 {explainer_id, status: "pending"}
```

Client polls `GET /api/v1/explainer/{explainer_id}` for status updates.

### Background: `process_explainer_video(explainer_id, presentation_data)`

```
Status: pending → extracting → generating_scripts → generating_audio → composing → completed

Step 1: extracting
  _update_status(explainer_id, "extracting")
  
  _extract_slides_from_presentation(presentation_data):
    For each slide in data["slides"]:
      title = slide["title"]
      content = join(bullets + notes + content)
      html = slide["html"]
    → List[{slide_number, title, content, html}]
  
  Create output dirs:
    data/output/explainers/{explainer_id}/slides/
    data/output/explainers/{explainer_id}/audio/
    data/output/explainers/{explainer_id}/videos/
  
  ScreenshotService.capture_slides(presentation_data, output_dir):
    For each slide HTML:
      WeasyPrint/Playwright render → PNG
      Save: slides/slide_{i}.png

Step 2: generating_scripts
  _update_status(explainer_id, "generating_scripts")
  
  generate_slide_scripts_async(slides):
    Concurrent LLM calls (asyncio.gather) for each slide:
      Prompt: "You are a teacher. Create a clear 30-60 second narration for:
               Slide title: {title}
               Content: {content}"
      LLM (temperature=0.7, creative)
      → {slide_number, narration_text}
  
  Update DB: explainervideo.script = json.dumps(scripts)

Step 3: generating_audio
  _update_status(explainer_id, "generating_audio")
  
  voice = get_voice_id(language)  # from voice_map.py, default en-US
  
  For each script:
    output_path = audio/slide_{i}.mp3
    generate_audio_file(narration_text, voice, output_path):
      edge-tts.Communicate(narration_text, voice)
      await communicate.save(output_path)
    
    duration = get_audio_duration(output_path):
      pydub.AudioSegment.from_file(output_path).duration_seconds
  
  Update DB: audioFiles = json.dumps([{slide_number, audio_path, duration}])

Step 4: composing
  _update_status(explainer_id, "composing")
  
  total_duration = 0
  chapters = []
  
  For each slide:
    compose_slide_video(slide_image_path, audio_path, video_output_path):
      ffmpeg command:
        -loop 1 -i slide_{i}.png
        -i slide_{i}.mp3
        -c:v libx264 -c:a aac
        -t {duration} -pix_fmt yuv420p
        -vf scale=1920:1080  (normalized resolution)
        videos/slide_{i}.mp4
    
    chapters.append({"time_offset": total_duration, "title": slide.title})
    total_duration += duration
  
  Update DB: chapters = json.dumps(chapters)
  
  concatenate_videos(video_paths, output_path):
    Write concat.txt: "file 'videos/slide_0.mp4'\n..."
    ffmpeg -f concat -safe 0 -i concat.txt
           -c copy explainer.mp4
    Final: data/output/explainers/{explainer_id}/explainer.mp4

Step 5: completed
  _update_status(explainer_id, "completed",
      outputPath=final_mp4_path,
      duration=total_duration
  )
```

### Route: `GET /api/v1/explainer/{id}`

```
prisma.explainervideo.find_unique(id, include={generatedContent: true})
Validate ownership
Return: {
    id, status, outputPath, duration, chapters, createdAt,
    presentation_title, slide_count
}
```

---

## 22. Notebooks

### CRUD Routes

```
POST /api/v1/notebooks
  prisma.notebook.create({name, userId})
  Return {id, name, createdAt}

GET /api/v1/notebooks
  prisma.notebook.find_many(
      where={userId},
      include={materials: {where: {status: "completed"}}},
      order={updatedAt: desc}
  )
  Return [{id, name, createdAt, materials: [{id, title, filename, status}]}]

GET /api/v1/notebooks/{id}
  prisma.notebook.find_unique(
      where={id},
      include={materials: true}
  )
  Validate: notebook.userId == current_user.id
  Return full notebook with all materials

PUT /api/v1/notebooks/{id}
  Validate ownership
  prisma.notebook.update(where={id}, data={name: new_name})

DELETE /api/v1/notebooks/{id}
  Validate ownership
  Cascade deletes in order:
  1. collection.delete(where={"notebook_id": id})  ← ChromaDB chunks
  2. prisma.responseblock.delete_many (via message ids)
  3. prisma.chatmessage.delete_many(where={notebookId: id})
  4. prisma.chatsession.delete_many(where={notebookId: id})
  5. prisma.backgroundjob.delete_many(where={notebookId: id})
  6. prisma.material.delete_many(where={notebookId: id})
  7. prisma.generatedcontent.delete_many(where={notebookId: id})
  8. prisma.notebook.delete(where={id})
  Return {deleted: true}
```

---

## 23. Chat Sessions & History

### Session Management

```
GET /api/v1/chat/sessions/{notebook_id}
  prisma.chatsession.find_many(
      where={notebookId, userId},
      order={createdAt: desc},
      include={chatMessages: {take: 3, order_by: {createdAt: asc}}}
  )
  Return: [{id, title, createdAt, messages_text (first 3 msgs preview)}]

POST /api/v1/chat/sessions
  {notebook_id, title?}
  prisma.chatsession.create({notebookId, userId, title: title or "New Chat"})
  Return {session_id}

DELETE /api/v1/chat/sessions/{session_id}
  Cascade:
  1. prisma.responseblock.delete_many (via message ids)
  2. prisma.chatmessage.delete_many({chatSessionId, userId})
  3. prisma.chatsession.delete_many({id, userId})
  Return {deleted: true}
```

### Message History

```
GET /api/v1/chat/history/{notebook_id}?session_id=...
  prisma.chatmessage.find_many(
      where={notebookId, userId, chatSessionId?: session_id},
      order={createdAt: asc},
      include={responseBlocks: true}
  )
  Return: [{
      id, role, content, created_at,
      agent_meta: (parsed agentMeta JSON),
      blocks: [{id, index, text}] (sorted by blockIndex, only for assistant)
  }]

DELETE /api/v1/chat/history/{notebook_id}?session_id=...
  Find all messages → collect ids
  Delete ResponseBlocks for all message ids
  Delete ChatMessages
  Return {cleared: true}
```

### Response Block System

Every assistant message is split into `ResponseBlock` records via `_split_markdown_blocks()`:

```
Algorithm handles:
  ┌── Fenced code blocks (``` or ~~~):
  │     Detect opening fence → collect ALL lines → closing fence → flush as ONE block
  │     Code blocks are never split
  │
  ├── Tables (lines starting with |):
  │     Group all consecutive | lines as one block
  │
  ├── Headings (# to ######):
  │     Always start a new block
  │
  ├── Horizontal rules (--- *** ___):
  │     Flush before + after
  │
  ├── Blockquotes (> lines):
  │     Group consecutive > lines
  │
  ├── Lists (- * + or 1. 2.):
  │     Group list items + continuations (2+ space indented)
  │
  └── Regular paragraphs:
        Split on 2+ consecutive blank lines
        Type changes (list→paragraph, blockquote→paragraph) force flush

Max block text: 5000 chars (truncated at DB insert)
Each block: prisma.responseblock.create({chatMessageId, blockIndex, text})
```

---

## 24. Block Follow-up & Suggestions

### Block Follow-up: `POST /api/v1/chat/block-followup`

```
Request: {block_id, action: "ask"|"simplify"|"translate"|"explain", question?}

1. Ownership validation:
   prisma.responseblock.find_unique(block_id, include={chatMessage: {include: {notebook}}})
   Verify: block.chatMessage.notebook.userId == current_user.id
   Raise 404 if not found, 403 if not owned

2. block_followup_stream(block_id, action, question):
   Load block.text from DB
   
   Build action-specific prompt:
     ask:       "Based on: '{block_text}'\nAnswer: {question}"
     simplify:  "Simplify this paragraph for easier understanding: '{block_text}'"
     translate: "Translate to {question}: '{block_text}'"
     explain:   "Explain in much more depth with examples: '{block_text}'"
   
   llm = get_llm()  # chat temperature 0.2
   async for chunk in llm.astream(prompt):
     yield chunk.content

3. Stream as "event: token\ndata: {content: chunk}\n\n"

4. After stream: persist full response as new sibling ResponseBlock:
   max_block = find child block with max blockIndex for same chatMessageId
   next_idx = max_block.blockIndex + 1
   prisma.responseblock.create({
       chatMessageId: parent_block.chatMessageId,
       blockIndex: next_idx,
       text: f"[{action}] {full_response}"
   })

5. yield "event: done\ndata: {}\n\n"
```

### Prompt Suggestions: `POST /api/v1/chat/suggestions`

```
Request: {partial_input, notebook_id}

1. prisma.notebook.find_unique(notebook_id, include={materials: true})
2. Build context: notebook title + material titles list

3. LLM prompt (structured, temperature=0.1):
   "You are an AI prompt engineer for an educational platform.
   Notebook: '{title}'. Materials: '{titles}'.
   Partial input: '{partial_input}'
   Generate 3-5 powerful, context-aware prompt completions.
   Return: [{suggestion, confidence}]"

4. Score blending:
   overlap_score = word_intersection(partial_input, suggestion) / len(partial_words)
   final_confidence = (llm_confidence + overlap_score) / 2

5. Sort by final_confidence desc, return top 5
   [{suggestion, confidence}]
```

---

## 25. WebSocket Manager

`app/services/ws_manager.py` — `ws_manager` global singleton.

```python
class ConnectionManager:
    _connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(user_id: str, ws: WebSocket):
        await ws.accept()
        _connections[user_id].append(ws)
    
    def disconnect(user_id: str, ws: WebSocket):
        _connections[user_id].remove(ws)
        if not _connections[user_id]: del _connections[user_id]
    
    async def broadcast(user_id: str, message: dict):
        """Send message to ALL connections for a user (multi-tab support)."""
        for ws in _connections.get(user_id, []):
            try:
                await ws.send_text(json.dumps(message))
            except (WebSocketDisconnect, Exception):
                pass
    
    async def send_personal(user_id: str, message: dict):
        """Send to first connection only (legacy single-tab)."""
```

**WebSocket endpoint:** `WS /api/v1/ws/{user_id}`

Used for:
- Podcast generation progress events
- Podcast Q&A streaming (doubt answering)
- Real-time job status updates (material processing)

---

## 26. LLM Service Layer

`app/services/llm_service/llm.py`

```python
def get_llm(mode: str = "chat", temperature: float = None) -> BaseChatModel:
    """
    mode → temperature:
      "chat"       →  0.2  (factual answers, focused)
      "structured" →  0.1  (JSON output, near-deterministic)
      "creative"   →  0.7  (varied, expressive — podcast scripts, PPT)
      "code"       →  0.1  (deterministic code generation)
    
    Providers (controlled by LLM_PROVIDER env):
      OLLAMA: ChatOllama(
          base_url=settings.OLLAMA_BASE_URL,
          model=settings.OLLAMA_MODEL,
          temperature=temperature
      )
      GOOGLE: ChatGoogleGenerativeAI(
          model=settings.GOOGLE_MODEL,
          google_api_key=settings.GOOGLE_API_KEY,
          temperature=temperature
      )
      NVIDIA: ChatOpenAI(
          base_url=settings.NVIDIA_BASE_URL,
          api_key=settings.NVIDIA_API_KEY,
          model=settings.NVIDIA_MODEL
      )
      OPENLM: ChatOpenAI(
          base_url=settings.OPENLM_BASE_URL,
          model=settings.OPENLM_MODEL
      )
    """

def get_llm_structured() → BaseChatModel:
    return get_llm(mode="structured")  # temperature=0.1

def get_model_token_limit(model_name: str) → int:
    """Lookup table: model_name → context_window_size"""

def estimate_token_count(text: str) → int:
    """Rough estimate: len(text.split()) * 1.3"""
```

All LLM instances support:
- `.invoke(prompt)` — sync single response
- `.ainvoke(prompt)` — async single response
- `.astream(prompt)` — async token-by-token generator
- LangChain custom events via `adispatch_custom_event()` (used by agent tools for SSE)

---

## 27. Search Endpoint

### Route: `POST /api/v1/search`

```
Request: {
    query: str,
    notebook_id?: str,
    search_types: ["materials", "content", "sessions"]
}

materials search:
  secure_similarity_search_enhanced(query, material_ids=all_user_materials)
  → [{material_id, title, filename, snippet, relevance_score}]

content search (generated content):
  prisma.generatedcontent.find_many(where={
      userId,
      notebookId?: notebook_id,
      data: {string_contains: query}  ← full-text scan
  })
  → [{id, contentType, title, snippet: data[:200]}]

sessions search (chat history):
  prisma.chatmessage.find_many(where={
      userId,
      content: {contains: query, mode: "insensitive"}
  })
  → [{session_id, message_preview: content[:100], notebook_id}]

Return: {
    results: {
        materials: [...],
        content: [...],
        sessions: [...]
    },
    total: N
}
```

---

## 28. Jobs Endpoint

```
GET /api/v1/jobs?notebook_id=...&status=...
  prisma.backgroundjob.find_many(where={userId, notebookId?, status?})
  Return: [{id, status, jobType, createdAt, updatedAt, error?}]

GET /api/v1/jobs/{job_id}
  prisma.backgroundjob.find_unique(where={id})
  Validate: job.userId == current_user.id
  Return: {id, status, jobType, result, error, createdAt, updatedAt}

DELETE /api/v1/jobs/{job_id}
  Only completed or failed jobs can be deleted
  prisma.backgroundjob.delete(where={id})
```

---

## 29. Token Counting, Rate Limiting & Audit Logging

### Token Counter

`app/services/token_counter.py`

```python
def estimate_token_count(text: str) → int:
    """Rough heuristic: word_count * 1.3"""
    words = len(text.split())
    return int(words * 1.3)

async def track_token_usage(user_id: str, tokens: int) → None:
    """Upsert UserTokenUsage:
       - If today's record exists: increment total_tokens
       - If new day: create new daily record
       Best-effort — never raises.
    """

async def get_token_usage(user_id: str) → dict:
    """Return {total_tokens, daily_tokens, date}"""
```

### Rate Limiter

`app/services/rate_limiter.py` — `RateLimitMiddleware`

```
Per-IP sliding window:
  Heavy endpoints (/chat, /agent, /ppt, /podcast, /explainer):
    10 requests per 60 seconds
  Normal endpoints:
    60 requests per 60 seconds

Implementation:
  _requests: Dict[str, deque[float]] = {}  # IP → [timestamp, ...]
  
  On each request:
    ip = request.client.host
    now = time.time()
    window = _requests[ip]
    # Remove timestamps older than 60s
    while window and window[0] < now - 60: window.popleft()
    if len(window) >= limit: return Response(429)
    window.append(now)
    continue
```

### Audit Logger

`app/services/audit_logger.py`

```python
async def log_api_usage(
    user_id: str,
    endpoint: str,
    material_ids: List[str],
    context_token_count: int,
    response_token_count: int,
    model_used: str,
    llm_latency: float,
    retrieval_latency: float,
    total_latency: float,
) → None:
    """Insert ApiUsageLog row. Best-effort — never raises to caller."""
    await prisma.apiusagelog.create(data={...})
```

---

## 30. Complete API Reference

### Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/auth/register` | None | Create account |
| POST | `/api/v1/auth/login` | None | Login → tokens |
| POST | `/api/v1/auth/refresh` | None (refresh token in body) | Refresh access token |
| GET | `/api/v1/auth/me` | Bearer | Current user profile |
| POST | `/api/v1/auth/logout` | Bearer | Revoke refresh token |

### Notebooks

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/notebooks` | Bearer | List user notebooks + materials |
| POST | `/api/v1/notebooks` | Bearer | Create notebook |
| GET | `/api/v1/notebooks/{id}` | Bearer | Get notebook details |
| PUT | `/api/v1/notebooks/{id}` | Bearer | Rename notebook |
| DELETE | `/api/v1/notebooks/{id}` | Bearer | Delete + cascade |

### Upload & Materials

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/upload` | Bearer | Upload file (multipart) |
| POST | `/api/v1/upload/url` | Bearer | Add URL or YouTube |
| POST | `/api/v1/upload/text` | Bearer | Add plain text |
| GET | `/api/v1/materials` | Bearer | List materials for notebook |
| GET | `/api/v1/materials/{id}` | Bearer | Get material metadata |
| DELETE | `/api/v1/materials/{id}` | Bearer | Delete material + chunks |
| GET | `/api/v1/materials/{id}/status` | Bearer | Poll processing status |

### Chat (all return SSE stream or JSON)

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/chat` | Bearer | Chat (RAG/Agent/Research/Code/Search) — SSE |
| POST | `/api/v1/chat/block-followup` | Bearer | Block follow-up action — SSE |
| POST | `/api/v1/chat/suggestions` | Bearer | Prompt auto-complete |
| GET | `/api/v1/chat/history/{notebook_id}` | Bearer | Full message history |
| DELETE | `/api/v1/chat/history/{notebook_id}` | Bearer | Clear history |
| GET | `/api/v1/chat/sessions/{notebook_id}` | Bearer | List chat sessions |
| POST | `/api/v1/chat/sessions` | Bearer | Create session |
| DELETE | `/api/v1/chat/sessions/{session_id}` | Bearer | Delete session + messages |

### Agent

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/agent` | Bearer | LangGraph StateGraph agent — SSE |

### Content Generation

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/flashcard/generate` | Bearer | Generate flashcard set |
| GET | `/api/v1/flashcard` | Bearer | List flashcard sets for notebook |
| GET | `/api/v1/flashcard/{id}` | Bearer | Get flashcard set |
| DELETE | `/api/v1/flashcard/{id}` | Bearer | Delete |
| POST | `/api/v1/quiz/generate` | Bearer | Generate quiz |
| GET | `/api/v1/quiz` | Bearer | List quizzes |
| GET | `/api/v1/quiz/{id}` | Bearer | Get quiz |
| DELETE | `/api/v1/quiz/{id}` | Bearer | Delete |
| POST | `/api/v1/ppt/generate` | Bearer | Generate presentation (multi-stage) |
| GET | `/api/v1/ppt/{id}` | Bearer | Get presentation |
| DELETE | `/api/v1/ppt/{id}` | Bearer | Delete |
| POST | `/api/v1/mindmap/generate` | Bearer | Generate mind map |
| GET | `/api/v1/mindmap/{id}` | Bearer | Get mind map |
| DELETE | `/api/v1/mindmap/{id}` | Bearer | Delete |

### Podcast

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/podcast/sessions` | Bearer | List podcast sessions |
| POST | `/api/v1/podcast/sessions` | Bearer | Create session |
| GET | `/api/v1/podcast/sessions/{id}` | Bearer | Get full session |
| POST | `/api/v1/podcast/sessions/{id}/generate` | Bearer | Start generation |
| DELETE | `/api/v1/podcast/sessions/{id}` | Bearer | Delete session |
| POST | `/api/v1/podcast/{id}/bookmarks` | Bearer | Add bookmark |
| GET | `/api/v1/podcast/{id}/bookmarks` | Bearer | List bookmarks |
| POST | `/api/v1/podcast/{id}/annotations` | Bearer | Add annotation |
| GET | `/api/v1/podcast/{id}/annotations` | Bearer | List annotations |
| POST | `/api/v1/podcast/{id}/export` | Bearer | Export MP3 or transcript |

### Explainer

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/explainer/generate` | Bearer | Start explainer video generation |
| GET | `/api/v1/explainer/{id}` | Bearer | Get status + output path |
| DELETE | `/api/v1/explainer/{id}` | Bearer | Delete + cleanup files |

### Utility

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/v1/search` | Bearer | Federated search |
| GET | `/api/v1/jobs` | Bearer | List background jobs |
| GET | `/api/v1/jobs/{id}` | Bearer | Job details + status |
| DELETE | `/api/v1/jobs/{id}` | Bearer | Delete completed/failed job |
| GET | `/api/v1/models` | Bearer | List available LLM models |
| GET | `/api/v1/health` | None | Health check |
| WS | `/api/v1/ws/{user_id}` | None (user_id in path) | WebSocket |

---

## Appendix A: SSE Response Format

All streaming endpoints use `StreamingResponse(media_type="text/event-stream")` with headers:
```
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no    ← disables nginx/proxy buffering for true streaming
```

Standard SSE format:
```
event: <type>
data: <json string>

```
(empty line terminates each event)

**All event types by endpoint:**

| Endpoint | Event Types |
|---|---|
| RAG chat | `token`, `meta`, `done`, `error`, `blocks` |
| AGENT chat | `plan`, `tool_start`, `tool_result`, `code_generated`, `code_stdout`, `artifact`, `token`, `done`, `error`, `blocks` |
| WEB_RESEARCH | `phase`, `token`, `citations`, `done`, `error`, `blocks` |
| CODE_EXECUTION | `code_generating`, `code_result`, `token`, `done`, `error` |
| WEB_SEARCH | `search_results`, `token`, `done`, `error` |
| Block followup | `token`, `done`, `error` |

---

## Appendix B: Key Design Patterns

### Async-to-Thread Pattern
All blocking operations (ChromaDB, embedding model inference, pandas, file I/O) use:
```python
result = await asyncio.to_thread(blocking_function, arg1, arg2)
```
This keeps the event loop non-blocking for all concurrent HTTP requests.

### Tenant Isolation Pattern
ChromaDB enforces per-user isolation at the query level:
```python
where = {"$and": [{"user_id": user_id}, {"material_id": {"$in": material_ids}}]}
```
Post-retrieval validation drops any chunk with mismatched `user_id`.

### Graceful Degradation Pattern
Every non-critical operation (audit logging, token tracking, block saving) is wrapped:
```python
try:
    await some_operation()
except Exception as exc:
    logger.warning("Operation failed (non-fatal): %s", exc)
    # Never raise — caller proceeds without this data
```

### Event-Driven Worker Pattern
Instead of polling every 2 seconds:
```python
# Upload route:
job_queue.notify()  # sets asyncio.Event

# Worker:
await job_queue.wait(timeout=2.0)  # wakes immediately on notify, else polls
self._event.clear()
```

### Self-Healing Code Pattern
Agent automatically repairs failing code:
```
failed code + stderr → code_repair_prompt.txt → LLM → fixed code → retry
Max attempts: MAX_CODE_REPAIR_ATTEMPTS (default 3)
```
