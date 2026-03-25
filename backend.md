# KeplerLab Backend - Complete Architecture and End-to-End Flow

## 1. Scope of This Document

This document maps the backend implementation under `backend/` with emphasis on:
- Runtime architecture and lifecycle
- Data model and storage layers
- Security and authentication
- Every route group and feature flow
- Cross-cutting systems (jobs, websockets, observability, code execution, agent)

Primary implementation roots:
- `backend/app/main.py`
- `backend/app/routes/*.py`
- `backend/app/services/**/*.py`
- `backend/app/core/config.py`
- `backend/prisma/schema.prisma`
- `backend/requirements.txt`

## 2. Technology Stack

- API framework: FastAPI (`fastapi`, `uvicorn`)
- Data access: Prisma Python client (`prisma-client-py`) over PostgreSQL
- Vector store: ChromaDB (`chromadb`)
- LLM and orchestration: LangChain + LangGraph
- Auth: JWT access/refresh tokens (`python-jose`, `passlib`)
- Document/media processing: OCR, Whisper, PDF/image/document parsers
- Real-time: SSE for chat/code events, WebSocket for async job/material updates

## 3. Top-Level Architecture

### 3.1 Layered Structure

- Entry and app composition:
  - `backend/app/main.py`
- HTTP/WebSocket adapters:
  - `backend/app/routes/*.py`
- Business orchestration and domain logic:
  - `backend/app/services/**`
- Data model and contracts:
  - `backend/app/models/*`, `backend/app/services/chat_v2/schemas.py`
- Persistence clients:
  - `backend/app/db/prisma_client.py`, `backend/app/db/chroma.py`
- Prompt system:
  - `backend/app/prompts/**`
- Global config:
  - `backend/app/core/config.py`

### 3.2 Core Runtime Components

- FastAPI app with lifespan startup/shutdown hooks
- Prisma connection manager with retry
- Background job processor with bounded concurrency
- SSE stream emitters for chat/agent/research/code
- WebSocket connection manager per user
- Filesystem storage for uploads, generated artifacts, explainers, podcasts, presentations

## 4. Application Startup and Lifecycle

Implemented in `backend/app/main.py`.

Startup sequence:
1. Connect Prisma DB (`connect_db`).
2. Warm embedding model (`warm_up_embeddings`) in thread pool.
3. Preload reranker model (`get_reranker`) in thread pool.
4. Start background `job_processor()` task.
5. Ensure sandbox dependencies (`ensure_packages`).
6. Cleanup stale temp sandbox directories (`/tmp/kepler_sandbox_*`, `/tmp/kepler_analysis_*`).
7. Ensure output directories (`generated`, `presentations`, `explainers`, `podcast`, `artifacts`).
8. Cleanup expired refresh tokens.

Shutdown sequence:
1. Trigger graceful worker shutdown.
2. Cancel/await worker task with timeout.
3. Disconnect Prisma.

## 5. Middleware, Error Handling, and Request Metadata

Configured in `backend/app/main.py`.

- Performance middleware (`performance_monitoring_middleware`)
- Rate limiter middleware (`rate_limit_middleware`)
- Request logger middleware:
  - Generates request id
  - Adds `X-Request-ID`
  - Logs method/path/status/latency
- CORS middleware:
  - Origins from `settings.CORS_ORIGINS`
- Trusted host middleware in production
- Global exception handlers:
  - `HTTPException` passthrough with CORS headers
  - fallback 500 with request id

## 6. Configuration Model (`core/config.py`)

Major configuration groups:
- Environment: `ENVIRONMENT`, `DEBUG`
- Storage dirs: `CHROMA_DIR`, `UPLOAD_DIR`, `ARTIFACTS_DIR`, `WORKSPACE_BASE_DIR`, outputs
- Upload limits: `MAX_UPLOAD_SIZE_MB`
- Code execution and repair: `CODE_EXECUTION_TIMEOUT`, `MAX_CODE_REPAIR_ATTEMPTS`, on-demand package allowlist
- JWT/auth/cookies: access/refresh expiry, cookie attributes
- CORS origins
- LLM provider selection and generation parameters
- Embedding/reranker/retrieval tuning
- OCR/transcription/tool timeout values
- External service endpoints (optional): web search, web scrape, image generation

Path normalization:
- Relative paths are resolved against backend project root.

Validation:
- `JWT_SECRET_KEY` and `DATABASE_URL` are required.
- `LLM_PROVIDER` must be one of `MYOPENLM`, `GOOGLE`, `NVIDIA`, `OLLAMA`.

## 7. Data Architecture

## 7.1 Primary Storage Layers

- PostgreSQL (system of record): users, notebooks, materials, chat, generated content, podcast, jobs, artifacts, logs
- ChromaDB: embeddings/chunks for RAG retrieval
- Filesystem:
  - Upload raw files
  - Material extracted text sidecar
  - Generated files/artifacts
  - Explainers and podcast audio/video exports

## 7.2 Prisma Models (from `prisma/schema.prisma`)

Core entities:
- `User`
- `Notebook`
- `Material`
- `ChatSession`
- `ChatMessage`
- `ResponseBlock`
- `GeneratedContent`
- `GeneratedContentMaterial` (join)
- `BackgroundJob`
- `RefreshToken`
- `ExplainerVideo`
- `PodcastSession`, `PodcastSegment`, `PodcastDoubt`, `PodcastExport`, `PodcastBookmark`, `PodcastAnnotation`
- `PodcastSessionMaterial` (join)
- `Artifact`
- analytics/ops models:
  - `ApiUsageLog`, `UserTokenUsage`, `AgentExecutionLog`, `CodeExecutionSession`, `ResearchSession`

Key status enums:
- `MaterialStatus`: pending -> processing/ocr/transcribing/embedding -> completed/failed
- `JobStatus`: pending -> processing/... -> completed/failed
- `PodcastSessionStatus`
- `VideoStatus`, `ExportStatus`

## 8. Authentication and Session Security

Routes in `routes/auth.py`, logic in `services/auth/service.py` and `services/auth/security.py`.

Flow:
1. Signup validates password complexity and username length.
2. Login verifies bcrypt hash, issues access + refresh tokens.
3. Refresh token is stored hashed in DB with family id.
4. Refresh endpoint rotates token (single-use semantics).
5. Reuse detection revokes token family.
6. Logout revokes all user refresh tokens and clears cookie.

Token details:
- Access token type: `access`
- Refresh token type: `refresh`
- JWT includes `exp`, `jti`, and for refresh: `family`

Request auth extraction:
- Bearer token header or `token` query param (for special channels)

## 9. Realtime Channels

## 9.1 SSE

Used by:
- `/chat` streamed responses
- `/chat/block-followup`
- `/code-execution/execute-code`
- Agent and research step events

SSE helpers in `services/chat_v2/streaming.py`:
- `token`, `tool_start`, `tool_result`, `blocks`, `meta`, `done`, `error`, plus specialized events

## 9.2 WebSocket

Route: `GET ws://.../ws/jobs/{user_id}` in `routes/websocket_router.py`.

Behavior:
- Auth via query token or initial auth message `{type:'auth', token}`
- Rejects mismatched user id
- Ping/pong keepalive
- Uses `services/ws_manager.py` to track per-user sockets and broadcast updates

Used for:
- Material status updates from processing pipeline
- Notebook rename push events
- Podcast events (frontend multiplexes these)

## 10. Asynchronous Job Processing

Services:
- `services/job_service.py`
- `services/worker.py`

Design:
- Job records stored in `BackgroundJob`
- Worker loop polls and also wakes via in-memory event `job_queue.notify()`
- Concurrency limit: `MAX_CONCURRENT_JOBS = 5`
- Claiming is atomic via raw SQL `FOR UPDATE SKIP LOCKED`
- Stuck-job recovery on startup
- Periodic cleanup of old jobs

Job types observed:
- `material_processing`
- `presentation` (async presentation generation)

## 11. Material Ingestion and Indexing Pipeline

Entry routes:
- `POST /upload`
- `POST /upload/batch`
- `POST /upload/url`
- `POST /upload/text`

Main flow:
1. Validate input and enforce constraints.
2. Persist upload into user folder.
3. Create `Material` record (status pending).
4. Create `BackgroundJob` with payload.
5. Notify worker queue.
6. Worker dispatches by source type:
   - file -> `process_material_by_id`
   - url/youtube -> `process_url_material_by_id`
   - text -> `process_text_material_by_id`
7. Extraction, chunking, embedding, status updates.
8. Emit WS material updates.
9. Optional background AI title and notebook-name refinement.

Important details:
- URL upload has SSRF defenses:
  - protocol validation
  - hostname/IP resolution
  - private network block
- Structured files (csv/xlsx/...) have special summary chunk fast-path.
- Full extracted text is stored separately through `storage_service`.

## 12. Chat V2 System

Router alias:
- `routes/chat.py` re-exports `services/chat_v2/router.py`.

Endpoints:
- `POST /chat`
- `POST /chat/block-followup`
- `POST /chat/optimize-prompts`
- `POST /chat/suggestions`
- `POST /chat/empty-suggestions`
- `GET/DELETE /chat/history/{notebook_id}`
- `GET/POST/DELETE /chat/sessions...`
- `DELETE/PATCH /chat/message/{message_id}`

### 12.1 Capability Routing

In `services/chat_v2/router_logic.py`, request is mapped to:
- `NORMAL_CHAT`
- `RAG`
- `WEB_SEARCH`
- `WEB_RESEARCH`
- `CODE_EXECUTION`
- `AGENT`

Decision signals:
- explicit `intent_override`
- `/agent` prefix
- selected materials
- regex keyword families for code/data/web

### 12.2 Chat Orchestration (`orchestrator.py`)

For each message:
1. Route capability.
2. For tool-based capabilities, execute tool generator(s).
3. Build LLM prompt/messages with history/context.
4. Stream tokens via SSE.
5. Emit `meta`, save response blocks, emit `done`.
6. Persist user + assistant messages + metadata.

RAG special-case:
- If no relevant chunks, returns explicit guidance message.

### 12.3 Message Persistence

`message_store` responsibilities:
- ensure/create chat session
- save user and assistant messages
- save block-level segmentation in `ResponseBlock`
- history/session retrieval and deletion

## 13. Agentic System (LangGraph)

Primary file: `services/agent/agent_orchestrator.py`.

Graph nodes:
- `analyse`
- `planner`
- `execute_step`
- `reflect`
- `advance_step`
- `direct_response`
- `synthesize`

Safety limits:
- max steps, max tool calls, max retries per step, global timeout

Execution model:
- Agent graph runs in background task
- SSE events queued and drained to client stream
- Keepalive events prevent idle disconnects

Tool registry (`tools_registry.py`):
- `rag`
- `web_search`
- `research`
- `python_auto` (generate + execute code + artifacts)

Resource-aware planning:
- `resource_router.py` classifies selected materials as dataset/document/other
- steering influences tool choices and plan generation

Reflection/self-heal:
- On failures, reflection may retry, replan, continue, or complete

Persistence:
- Saves user/assistant messages
- links generated artifact ids to final assistant message
- saves response blocks

## 14. RAG, Search, and Research

### 14.1 RAG

- Retrieval pipelines under `services/rag/*`
- Embedding and vector storage via Chroma
- Context formatting and citation validation utilities

### 14.2 Web Search

Route: `POST /search/web`
- Primary mode: optional external endpoint (`WEB_SEARCH_ENDPOINT`)
- Fallback mode: DuckDuckGo (`core/web_search.py`)

### 14.3 Deep Research

Tool service: `services/tools/research_tool.py` and `services/research/*`
- Multi-query research workflow
- emits iterative SSE phases and source events
- can output PDF/report artifacts

## 15. Code Execution and Artifacts

Route group: `routes/code_execution.py`.

Endpoints:
- `POST /code-execution/execute-code`
- `POST /code-execution/run-generated`

Flow:
1. Validate and sanitize code.
2. Execute in sandbox with timeout.
3. Auto-install approved missing modules (on-demand).
4. On failure, attempt LLM repair suggestions.
5. Detect output files in work dir.
6. Register each output as `Artifact` in DB and persistent storage.
7. Stream execution/artifact events via SSE.
8. Persist execution summary in `CodeExecutionSession`.

Artifact serving:
- route: `GET /artifacts/{artifact_id}`
- serves from `workspacePath` with stored MIME

## 16. Learning Generation Features

## 16.1 Flashcards (`/flashcard`)

Flow:
1. Validate selected materials.
2. Load material text(s).
3. Optional topic focus + difficulty/count/instructions.
4. Invoke `flashcard.generator`.
5. Return generated cards.

## 16.2 Quiz (`/quiz`)

Same pattern as flashcards with quiz generator parameters.

## 16.3 Presentation (`/presentation`)

Endpoints:
- `POST /presentation` synchronous
- `POST /presentation/async` background job
- `GET /presentation/slides/{user_id}/{presentation_id}/{filename}`

Flow:
1. Resolve material text.
2. Generate slide deck payload (`ppt/generator.py`).
3. For async path, job status polled via `/jobs/{job_id}`.

## 16.4 Explainer Video (`/explainer`)

Endpoints:
- check existing presentations
- generate explainer
- poll status
- stream final mp4 file

Flow:
1. Validate language/voice options.
2. Reuse existing presentation or generate a new one.
3. Create `ExplainerVideo` row with pending status.
4. Background task renders script/audio/video.
5. Status endpoint reports progress map.
6. Video endpoint serves final mp4 after completion.

## 16.5 Podcast Live (`/podcast`)

Capabilities:
- session create/get/list/update/delete
- generation start
- segment and audio file serving
- question/doubt handling
- bookmarks and annotations
- exports (pdf/json)
- summary generation
- language/voice discovery and preview
- satisfaction intent check

Backed by:
- `services/podcast/session_manager.py`
- `qa_service.py`
- `export_service.py`
- `tts_service.py`
- `satisfaction_detector.py`

## 17. Notebook and Content Management

Routes in `routes/notebook.py`:
- CRUD notebooks
- save/list/delete/update generated content

Behavior highlights:
- Notebook delete includes cleanup of messages, sessions, generated content, materials, and best-effort vector/file cleanup.
- Generated content stores typed blobs (`flashcards`, `quiz`, `presentation`, etc.).

## 18. Materials Management

Routes in `routes/materials.py`:
- list materials by notebook
- patch title/filename
- delete material (db + chroma + file storage)
- fetch full extracted text

Delete operation in `material_service.py` is step-wise and attempts partial-failure signaling.

## 19. File Proxy and Viewer Support

Routes in `routes/proxy.py` (`/api/v1/*`):
- generic https proxy with restricted headers
- file type inspection endpoint
- file proxy specifically for pdf/text

Security controls:
- HTTPS only
- local/private network protection
- extension-kind gating for file viewer path

## 20. Health and Model Management

Health routes:
- `/health`
- `/health/simple`

Checks include:
- DB query
- Chroma collection count
- LLM provider readiness sanity

Model routes:
- `/models/status`
- `/models/reload` (admin only)

## 21. Route Registry (Main App Wiring)

Routers mounted in `main.py`:
- `health`, `auth`, `models`
- `notebooks`, `upload`, `materials`
- `flashcard`, `quiz`, `chat`
- `jobs`, `presentation`, `search`
- `proxy`, `explainer`, `podcast`
- `code-execution`, `artifacts`
- websocket `ws`

## 22. End-to-End Feature Flows Summary

### 22.1 Upload -> Process -> Chat over Material

1. User uploads file/url/text to upload route.
2. Backend persists `Material` + `BackgroundJob`.
3. Worker extracts text, chunks, embeds, marks completed.
4. WS pushes material completion to frontend.
5. User selects source and sends chat message.
6. Chat capability routes to RAG.
7. RAG retrieves context and LLM streams response via SSE.
8. Message and response blocks are persisted.

### 22.2 Agent with Artifact Output

1. User sends `/agent` or intent override.
2. Agent analyzes resources and plans steps.
3. Tool loop executes (`python_auto`, `research`, etc.).
4. Artifacts are created and registered.
5. Agent synthesizes final answer.
6. Metadata, blocks, artifacts links are saved.
7. SSE stream completes with `agent_done` + `done`.

### 22.3 Studio Generation (Quiz/Flashcards/Presentation/Explainer/Podcast)

1. Frontend chooses materials and generation action.
2. Backend validates material access/text availability.
3. Generation service creates output.
4. Result may be persisted as `GeneratedContent` and/or feature-specific table.
5. Frontend can revisit from notebook history.

## 23. Operational and Reliability Notes

- DB connect retries with backoff.
- Worker stuck-job recovery on startup.
- Job cleanup cron.
- Global request logging with request ids.
- SSE keepalive in long-running agent flows.
- Multiple non-fatal startup warmups to reduce first-request latency.

## 24. Security Surfaces and Controls

- JWT access + rotating refresh tokens
- Refresh token hash storage and reuse detection
- CORS and optional trusted host middleware
- Upload validation and content checks
- URL ingestion and proxy SSRF defenses
- Code execution validation/sandboxing
- WebSocket auth + user-id binding
- Path traversal prevention via `safe_path`

## 25. Backend Feature Inventory Checklist

Covered route groups:
- auth
- notebooks
- upload
- materials
- flashcard
- quiz
- chat
- jobs
- presentation
- search
- proxy
- explainer
- podcast
- code execution
- artifacts
- websocket
- models
- health

Covered service families:
- auth
- material processing
- notebook/content
- chat_v2
- agent
- rag
- tools
- code_execution
- podcast
- ppt
- explainer
- worker/job/ws manager

This gives end-to-end architecture and flow coverage for the backend implementation in this workspace.
