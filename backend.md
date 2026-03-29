# KeplerLab Backend Documentation

## 1) Backend At A Glance

KeplerLab backend is a FastAPI service that combines:
- Authenticated notebook and material management
- Background ingestion and processing pipeline
- Hybrid RAG retrieval over Chroma embeddings
- Streaming chat orchestration with multiple capabilities
- Agentic multi-step tool execution
- Sandboxed code generation/execution and artifact serving
- Skills execution engine
- Podcast generation and interactive playback support

Primary code root:
- `backend/app/main.py`
- `backend/app/routes/`
- `backend/app/services/`
- `backend/app/core/`
- `backend/app/db/`
- `backend/prisma/schema.prisma`

## 2) Runtime Stack And Dependencies

Core runtime:
- Python FastAPI + Uvicorn
- Prisma (async client) for PostgreSQL
- ChromaDB for vector retrieval
- LangChain wrappers for LLM providers

LLM providers supported via config:
- OLLAMA
- GOOGLE
- NVIDIA
- MYOPENLM

Major AI and processing dependencies (from `backend/requirements.txt`):
- langchain, langgraph
- sentence-transformers, transformers, torch
- chromadb
- trafilatura, ddgs (web search)
- whisper, ffmpeg-python, edge-tts
- pytesseract, easyocr
- python-docx, openpyxl, pdfplumber, pypdf, python-pptx

## 3) Process Lifecycle

Startup sequence (`app/main.py`):
1. Connects Prisma DB
2. Warms embedding model
3. Preloads reranker model
4. Starts background `job_processor()` task
5. Ensures sandbox packages are installed
6. Cleans stale temp sandbox directories
7. Ensures output/artifact directories exist
8. Cleans expired refresh tokens

Shutdown sequence:
1. Signals worker graceful shutdown
2. Waits (bounded timeout) for in-flight jobs
3. Disconnects Prisma

Middleware stack:
- Performance monitoring middleware
- Rate limiting middleware
- Request logging middleware with request ID and timing
- CORS middleware
- TrustedHost middleware in production

## 4) Configuration Model

Main config source: `backend/app/core/config.py`.

Key groups:
- Environment and CORS: `ENVIRONMENT`, `CORS_ORIGINS`
- Auth/JWT: `JWT_SECRET_KEY`, access/refresh TTLs, cookie settings
- Upload and storage: `UPLOAD_DIR`, `MAX_UPLOAD_SIZE_MB`, `ARTIFACTS_DIR`, `GENERATED_OUTPUT_DIR`
- LLM routing: provider/model keys, temperatures, token limits
- Retrieval tuning: `INITIAL_VECTOR_K`, `LEXICAL_K`, `RERANK_CANDIDATES_K`, `MMR_K`, `FINAL_K`, `MIN_SIMILARITY_SCORE`
- Sandbox execution limits: timeout, memory/cpu, file size, docker preference
- External endpoints: `WEB_SEARCH_ENDPOINT`, image/web scrape endpoints

Path values are normalized to absolute paths during config validation.

## 5) Storage And Data Architecture

### 5.1 PostgreSQL (Prisma)

Main entities (from `backend/prisma/schema.prisma`):
- Identity: `User`, `RefreshToken`
- Workspace: `Notebook`, `Material`, `NotebookSourceSelection`
- Chat: `ChatSession`, `ChatMessage`, `ResponseBlock`
- Generated outputs: `GeneratedContent`, `GeneratedContentMaterial`
- Execution/session logs: `BackgroundJob`, `CodeExecutionSession`, `ResearchSession`, `AgentExecutionLog`, `ApiUsageLog`, `UserTokenUsage`
- Podcast: `PodcastSession`, `PodcastSegment`, `PodcastDoubt`, `PodcastBookmark`, `PodcastAnnotation`, `PodcastExport`, `PodcastSessionMaterial`
- Artifacts: `Artifact`
- Skills: `Skill`, `SkillRun`

### 5.2 Chroma Vector Store

Chroma stores chunk embeddings with metadata fields used for tenant-safe filtering:
- `user_id`
- `notebook_id`
- `material_id`
- filename/section metadata

### 5.3 File System Stores

- Raw uploads under `UPLOAD_DIR/user_id`
- Material full text in storage service paths
- Generated outputs under `output/`
- Persistent artifacts under `ARTIFACTS_DIR`
- Temporary execution directories under `/tmp/kepler_*`

## 6) Security Model

Auth and session control:
- Access token (Bearer) required on protected routes
- Refresh token in HttpOnly cookie with rotation
- Refresh token family revocation on reuse detection
- Automatic expired token cleanup

Tenant/data isolation:
- Per-user notebook/material ownership checks in routes
- Retrieval hard-fails if `user_id` filter is missing
- Result ownership re-validation after retrieval

Network and URL protections:
- URL upload blocks private/internal target IP ranges
- Proxy/file-viewer requires HTTPS and blocks localhost/private ranges

Code execution safeguards:
- Static code validation with blocked imports/calls
- Sandboxed execution with limits (timeout, resources)
- Restricted package install behavior

WebSocket safeguards:
- Token authentication and path user-id match enforced
- Max connection limit per user

## 7) API Surface (Complete Route Map)

### Auth
- `POST /auth/signup`
- `POST /auth/login`
- `POST /auth/refresh`
- `GET /auth/me`
- `POST /auth/logout`

### Health and Models
- `GET /health`
- `GET /health/simple`
- `GET /models/status`
- `POST /models/reload`

### Notebooks and Generated Content
- `GET /notebooks`
- `POST /notebooks`
- `GET /notebooks/{notebook_id}`
- `PUT /notebooks/{notebook_id}`
- `DELETE /notebooks/{notebook_id}`
- `POST /notebooks/{notebook_id}/thumbnail`
- `POST /notebooks/{notebook_id}/content`
- `GET /notebooks/{notebook_id}/content`
- `DELETE /notebooks/{notebook_id}/content/{content_id}`
- `PUT /notebooks/{notebook_id}/content/{content_id}`
- `PATCH /notebooks/{notebook_id}/content/{content_id}/rating`

### Upload and Materials
- `POST /upload`
- `POST /upload/batch`
- `POST /upload/url`
- `POST /upload/text`
- `GET /upload/supported-formats`
- `GET /materials`
- `PATCH /materials/{material_id}`
- `DELETE /materials/{material_id}`
- `GET /materials/{material_id}/text`
- `GET /jobs/{job_id}`

### Chat (chat_v2 router)
- `POST /chat`
- `POST /chat/transcribe-audio`
- `POST /chat/block-followup`
- `POST /chat/optimize-prompts`
- `POST /chat/suggestions`
- `POST /chat/empty-suggestions`
- `GET /chat/source-selection/{notebook_id}`
- `PUT /chat/source-selection`
- `GET /chat/history/{notebook_id}`
- `DELETE /chat/history/{notebook_id}`
- `GET /chat/sessions/{notebook_id}`
- `POST /chat/sessions`
- `DELETE /chat/sessions/{session_id}`
- `DELETE /chat/message/{message_id}`
- `PATCH /chat/message/{message_id}`

### Generation Features
- `POST /flashcard`
- `POST /flashcard/suggest`
- `POST /quiz`
- `POST /quiz/suggest`
- `POST /mindmap`

### Search and Proxy
- `POST /search/web`
- `GET|HEAD /api/v1/proxy`
- `GET /api/v1/file-viewer/info`
- `GET|HEAD /api/v1/file-viewer/proxy`

### Podcast
- `POST /podcast/session`
- `GET /podcast/session/{session_id}`
- `GET /podcast/sessions/{notebook_id}`
- `PATCH /podcast/session/{session_id}`
- `DELETE /podcast/session/{session_id}`
- `POST /podcast/session/{session_id}/start`
- `GET /podcast/session/{session_id}/segment/{segment_index}/audio`
- `GET /podcast/session/{session_id}/audio/{filename}`
- `POST /podcast/session/{session_id}/question`
- `GET /podcast/session/{session_id}/doubts`
- `POST /podcast/session/{session_id}/bookmark`
- `GET /podcast/session/{session_id}/bookmarks`
- `DELETE /podcast/session/{session_id}/bookmark/{bookmark_id}`
- `POST /podcast/session/{session_id}/annotation`
- `DELETE /podcast/session/{session_id}/annotation/{annotation_id}`
- `POST /podcast/session/{session_id}/export`
- `GET /podcast/export/{export_id}`
- `GET /podcast/export/file/{session_id}/{filename}`
- `POST /podcast/session/{session_id}/summary`
- `GET /podcast/voices`
- `GET /podcast/voices/all`
- `GET /podcast/languages`
- `POST /podcast/voice/preview`
- `POST /podcast/session/{session_id}/satisfaction`

### Skills
- `POST /skills`
- `GET /skills`
- `GET /skills/templates`
- `POST /skills/validate`
- `POST /skills/suggest-tags`
- `POST /skills/generate-draft`
- `GET /skills/runs`
- `GET /skills/runs/{run_id}`
- `GET /skills/{skill_id}`
- `PUT /skills/{skill_id}`
- `DELETE /skills/{skill_id}`
- `POST /skills/{skill_id}/run`

### Code Execution and Artifacts
- `POST /code-execution/execute-code`
- `POST /code-execution/run-generated`
- `GET /artifacts/{artifact_id}`

### AI Resource Builder
- `POST /ai-resource-builder`

### WebSocket
- `WS /ws/jobs/{user_id}`

## 8) Material Ingestion Flow (File, URL, Text)

Entry routes:
- `/upload`
- `/upload/batch`
- `/upload/url`
- `/upload/text`

Common flow:
1. Validate request and ownership context
2. Create `Material` row with `status=pending`
3. Create `BackgroundJob` row with processing payload
4. Notify worker queue
5. Worker picks next pending job (`FOR UPDATE SKIP LOCKED`)
6. Worker dispatches by source type:
   - file -> `process_material_by_id`
   - url/web/youtube -> `process_url_material_by_id`
   - text -> `process_text_material_by_id`
7. Status progression emits WS updates:
   - `pending`
   - `processing`
   - optional `ocr_running` / `transcribing`
   - `embedding`
   - `completed` or `failed`
8. Extracted text is persisted, chunked, embedded, validated
9. Material summary and chunk count saved to DB
10. Optional background AI title/notebook name refinement

Important small details:
- Structured files (csv/xlsx/tsv/ods) use a summary-chunk fast path
- Embedding integrity check validates expected vs stored chunks
- Failed processing explicitly stores error and status

## 9) Chat And Capability Orchestration

Chat request enters `POST /chat`.

Router behavior:
- Validates notebook ownership
- Resolves material IDs:
  - explicit IDs from request, or
  - persisted notebook source selection fallback
- Filters to completed materials only
- Ensures/creates chat session
- Starts SSE stream from orchestrator

Capability routing (`router_logic.py`) chooses one of:
- `NORMAL_CHAT`
- `RAG`
- `WEB_SEARCH`
- `WEB_RESEARCH`
- `CODE_EXECUTION`
- `AGENT`
- `IMAGE_GENERATION`
- `SKILL_EXECUTION`

Routing nuance:
- If materials selected, many external/code intent overrides are redirected to RAG unless explicitly `/agent`
- Data-analysis style prompts with selected materials route to AGENT, not plain RAG

Persistence:
- User and assistant messages persisted in `ChatMessage`
- Assistant responses split into `ResponseBlock` rows
- Artifacts linked to messages

## 10) RAG Retrieval Internals

RAG entry point: `services/tools/rag_tool.py`.

Retriever core: `secure_similarity_search_enhanced()` in `services/rag/secure_retriever.py`.

Pipeline details:
1. Enforce tenant filter contains `user_id`
2. Build dense candidates from query variants
3. Build lexical candidates (BM25-like)
4. Fuse ranks with RRF
5. Optional MMR for diversity
6. Optional reranker (cross-encoder)
7. Score normalization and threshold filtering
8. Multi-source balancing across materials for cross-document queries
9. Format context with citations and source markers

Cross-document detection checks compare/contrast style language and changes balancing behavior.

## 11) Search Feature Architecture And Complete Flow

This section covers the full search capability from all search entry points.

### 11.1 Search Feature Components

Search-related backend modules:
- API route: `app/routes/search.py`
- Core search+scrape utilities: `app/core/web_search.py`
- Chat web-search tool: `app/services/tools/web_search_tool.py`
- Deep research stream: `app/services/research/pipeline.py`
- Capability routing: `app/services/chat_v2/router_logic.py`
- Proxy + file viewer support: `app/routes/proxy.py`

Search-related frontend callers (for context):
- Sidebar source discovery (`webSearch` -> `/search/web`)
- Chat `/web` and `/research` intents via `/chat`

### 11.2 Flow A: Source Discovery Search (`POST /search/web`)

Use case:
- User searches web from Sources panel and imports links as notebook materials.

Detailed sequence:
1. Client sends query and optional `file_type`.
2. Route appends `filetype:<type>` to query when provided.
3. Route first tries external endpoint if `WEB_SEARCH_ENDPOINT` is set.
4. If external endpoint fails, route falls back to local DDG search.
5. DDG function behavior:
   - backend list from `DDGS_BACKENDS` (default `duckduckgo,brave,auto`)
   - retry on rate-limit-like failures (429/202/timeout markers)
   - simplified-query fallback if initial query too verbose
6. Results normalized to:
   - title
   - link/url
   - snippet
7. Client shows selectable results.
8. User adds selected results.
9. Each selected URL is sent to `/upload/url`.
10. URL becomes `Material` + background processing job.
11. Worker extracts content and completes embedding.
12. Material appears in source list and can be selected for RAG chat.

### 11.3 Flow B: In-Chat Web Search Tool (`WEB_SEARCH` capability)

Use case:
- User asks web/current-events question, often with `/web`.

Detailed sequence:
1. `/chat` stream request arrives.
2. Capability router classifies as `WEB_SEARCH` unless material-selection rules force `RAG`.
3. Orchestrator calls `web_search_tool.execute()`.
4. Tool emits `tool_start` SSE.
5. Tool uses LLM to generate 4-5 diverse search queries.
6. Per round (max 2 rounds):
   - run DDG searches in parallel
   - dedupe unseen URLs
   - score/filter domains (preferred vs low-signal)
   - scrape selected URLs via `fetch_url_content()` (Trafilatura)
   - fallback to snippet when full scrape fails
   - emit `web_search_update` SSE with status and URL progress
7. Tool runs completeness check via LLM:
   - determines if answer is complete
   - confidence threshold and stagnation stop rules
   - optional follow-up query generation
8. Tool emits `web_sources` SSE with source list.
9. Tool returns `ToolResult` with synthesized context payload.
10. Orchestrator builds synthesis prompt (`get_web_search_synthesis_prompt`) and streams answer tokens.
11. Meta and done events emitted; chat persisted.

Streaming event detail for web search path:
- `tool_start`
- repeated `web_search_update`
- `web_sources`
- streamed `token`
- `meta`
- `done`

### 11.4 Flow C: Deep Research (`WEB_RESEARCH` capability)

Use case:
- User asks for comprehensive/deep research, often `/research`.

Detailed sequence:
1. Capability routes to `WEB_RESEARCH`.
2. Orchestrator runs `research_tool` -> `research.pipeline.stream_research()`.
3. Pipeline emits `research_start` and phase updates.
4. Query decomposition creates initial sub-questions.
5. Multi-query DDG search and dedupe over rounds.
6. URL fetching streams `research_source` events as pages arrive.
7. Gap analysis identifies missing angles for follow-up queries.
8. After source collection, report is streamed token-by-token.
9. Citations emitted as structured list.
10. PDF report generation attempted and emitted as `research_pdf` event.
11. Research session persisted in DB.

### 11.5 Flow D: Search-Adjacent Document Preview And Proxy

Proxy/file-viewer endpoints support safe preview of discovered files.

`/api/v1/file-viewer/info`:
- Validates URL
- Classifies file kind (pdf/office/text/other)
- For office docs, returns Office online embed URL

`/api/v1/file-viewer/proxy`:
- Proxies PDF/text files with safe headers and CORS allow
- Blocks unsupported kinds

`/api/v1/proxy`:
- General HTTPS page proxy with restricted headers

These endpoints help search results and URLs become browsable without exposing local network surfaces.

### 11.6 Search Feature Reliability Controls

- Fallback from external endpoint to local DDG
- Multi-backend DDG strategy
- Retry and timeout guards
- Domain quality filtering
- Iterative completeness stopping rules
- Snippet fallback when scraping fails
- Secure URL validation against private ranges
- SSE progress events to keep UX responsive

## 12) Agent System Flow

Agent orchestrator (`services/agent/agent_orchestrator.py`) uses deterministic phases:
1. Analyze task and resource profile
2. Build/normalize plan
3. Execute each step with tool selection
4. Reflect after step failures (retry/replan/continue/complete)
5. Synthesize final response or artifact-focused completion

Tool registry includes:
- `rag`
- `web_search`
- `research`
- `python_auto` (generate + execute)

Key limits:
- Max steps
- Max tool calls
- Max retries per step
- Agent timeout

Resource router classifies selected materials into dataset vs document groups to bias tool selection.

## 13) Code Execution And Artifacts

Execution API:
- `/code-execution/execute-code`
- `/code-execution/run-generated`

Flow:
1. Validate/sanitize code
2. Run in sandbox with timeout/resource controls
3. Optional auto-install approved missing packages
4. Optional LLM code repair attempts
5. Detect generated files
6. Register files as `Artifact` rows
7. Emit SSE events (`execution_*`, `artifact`)
8. Persist `CodeExecutionSession`

Artifact serving:
- `GET /artifacts/{artifact_id}` returns file from persisted workspace path

## 14) Skills System Flow

CRUD endpoints manage markdown-defined skills.

Execution endpoint `/skills/{skill_id}/run`:
- streams step lifecycle SSE
- status, step start/result/error/skipped, artifacts, done
- records execution in `SkillRun`

Validation endpoint checks markdown shape and variable declarations.

## 15) Podcast Flow

Podcast routes manage full lifecycle:
1. Create session with mode/language/voices/material IDs
2. Start generation
3. Stream progress via WS messages to user channel
4. Fetch and play segment audio
5. Handle live doubts/questions
6. Bookmarks and annotations
7. Export and summary

DB entities capture persistent progress and media metadata.

## 16) Real-Time Event Contracts

### 16.1 SSE (chat and tools)

Common events:
- `token`
- `tool_start`
- `tool_result`
- `error`
- `done`
- `meta`
- `blocks`
- `code_block`
- `artifact`
- `web_search_update`
- `web_sources`
- `research_*`
- `agent_*`
- `skill_*`

### 16.2 WebSocket (`/ws/jobs/{user_id}`)

Primary message categories:
- `connected`
- `ping`/`pong`
- `material_update`
- `notebook_update`
- `podcast_*`

WS manager supports fan-out to all user connections and prunes dead sockets.

## 17) Operational Notes

- Worker concurrency is bounded and includes stuck-job recovery.
- Upload flow enqueues quickly and offloads heavy extraction/embedding.
- Retrieval emits performance traces and supports hybrid/rerank tuning.
- Route-level ownership checks are pervasive for tenant safety.
- Search and research are designed with graceful degradation when external systems fail.

## 18) Backend Search Flow Summary (One-Line)

Search in KeplerLab is not a single endpoint: it is a layered system where `/search/web` handles source discovery, chat `WEB_SEARCH` handles iterative answer-oriented web retrieval with streaming updates, and `WEB_RESEARCH` handles deeper multi-round research and report generation, all guarded by URL/network safety rules and integrated back into notebook materials and chat persistence.