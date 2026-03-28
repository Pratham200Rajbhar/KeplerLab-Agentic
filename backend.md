# Backend Architecture (KeplerLab Agentic)

## 1. Overview
The backend is a FastAPI application with Prisma (PostgreSQL), asynchronous workers, streaming chat/agent execution, and multi-modal generation pipelines.

Primary responsibilities:
- authentication and session management
- notebook and material lifecycle
- retrieval-augmented chat and autonomous agent execution
- code generation/execution in a sandbox with artifact persistence
- generation pipelines (flashcards, quiz, mindmap, presentation, explainer, podcast)
- websocket updates for long-running operations

Core technologies:
- FastAPI (HTTP + websocket)
- Prisma Python client (async)
- PostgreSQL
- Chroma vector retrieval stack (RAG)
- LangChain-compatible LLM service wrappers
- edge-tts and media toolchain for podcast/explainer

## 2. Runtime Topology

### 2.1 Main App Boot Sequence
`backend/app/main.py` orchestrates startup via a FastAPI lifespan:
1. connect Prisma DB
2. warm embedding model
3. preload reranker
4. start background `job_processor` task
5. ensure sandbox packages
6. clean stale temp sandbox dirs
7. ensure output/artifact directories
8. cleanup expired refresh tokens

Shutdown sequence:
1. signal worker graceful shutdown
2. wait with timeout for in-flight jobs
3. disconnect Prisma

### 2.2 Middleware Stack
Middleware configured in `main.py`:
- performance middleware (`performance_monitoring_middleware`)
- rate-limit middleware (`rate_limit_middleware`, currently pass-through)
- request logging middleware (request ID and latency)
- CORS middleware
- TrustedHost middleware in production

Error handlers:
- `HTTPException` pass-through with CORS headers
- global exception handler returns 500 + request ID

### 2.3 Router Registration
Routers are mounted without a global `/api` prefix; route modules define their own prefixes.
Registered domains:
- health/auth/models
- notebooks/upload/materials
- flashcard/quiz/mindmap
- chat (from `services/chat_v2/router.py`)
- jobs/presentation (legacy + v2)/search/proxy
- explainer/podcast/code-execution/artifacts/ai-resource
- websocket (`/ws/jobs/{user_id}`)

## 3. Configuration and Environment Model
Defined in `backend/app/core/config.py` via `BaseSettings`:
- environment toggles (`ENVIRONMENT`, `DEBUG`)
- DB connection (`DATABASE_URL`)
- auth/JWT/cookie settings
- LLM provider/model selection and generation parameters
- RAG retrieval tuning (K values, reranker usage, thresholds)
- upload and sandbox resource limits
- storage/output directories

Important behavior:
- relative paths are normalized to project-root absolute paths
- in production, `COOKIE_SECURE` is forced `True`
- provider key warnings emitted for missing cloud LLM credentials

## 4. Authentication and Session Security

### 4.1 Token Model
Auth flow uses short-lived access tokens + rotating refresh tokens:
- access token: JWT (`type=access`)
- refresh token: JWT (`type=refresh`, family + jti)
- refresh token hash stored in DB (`refresh_tokens`)

### 4.2 Endpoints
`/auth` routes:
- `POST /signup`
- `POST /login`
- `POST /refresh`
- `GET /me`
- `POST /logout`

### 4.3 Rotation/Re-use Protection
`validate_and_rotate_refresh_token`:
- checks token exists and not expired
- blocks already-used token
- revokes whole family on reuse detection
- marks token used atomically before issuing next token

### 4.4 Auth Enforcement Pattern
Most routes depend on `get_current_user`.
Token can be provided via:
- `Authorization: Bearer <token>`
- `token` query param (used by websocket/file-viewer flows)

## 5. API Surface by Domain

## 5.1 Notebook and Content APIs
Prefix: `/notebooks`
- CRUD notebooks
- ensure/generate thumbnail (`POST /{id}/thumbnail`)
- generated content CRUD under `/content`
- content rating endpoint (`PATCH .../rating`)

## 5.2 Material and Upload APIs
Upload prefix: `/upload`
- file upload (`POST /upload`)
- batch upload (`POST /upload/batch`)
- URL ingestion (`POST /upload/url`)
- text ingestion (`POST /upload/text`)
- supported formats (`GET /upload/supported-formats`)

Material prefix: `/materials`
- list materials (optional notebook filter)
- rename/update filename/title
- delete material
- fetch full extracted text

## 5.3 Chat v2 APIs
Prefix: `/chat`
- `POST /chat` (SSE streaming)
- block follow-up actions (`POST /block-followup`)
- prompt optimization/suggestions
- source selection persistence (`GET/PUT /source-selection`)
- session management (`GET/POST/DELETE /sessions`)
- history management (`GET/DELETE /history/{notebook_id}`)
- message edit/delete endpoints

## 5.4 Generation APIs
- flashcards: `/flashcard`
- quiz: `/quiz`
- mindmap: `/mindmap`
- presentation (legacy): `/presentation` and `/presentation/suggest`, plus `/presentation/async`
- presentation (v2): `/presentation/generate`, `/presentation/update`, `/presentation/{id}`, `/presentation/{id}/download`
- explainer: `/explainer/*`
- podcast: `/podcast/*`

Note: both legacy and v2 presentation routers are mounted under `/presentation`; route overlap requires careful maintenance.

## 5.5 Search, Proxy, Viewer, Models, Jobs
- web search: `POST /search/web`
- proxy/viewer utilities: `/api/v1/proxy`, `/api/v1/file-viewer/info`, `/api/v1/file-viewer/proxy`
- model status/reload: `/models/status`, `/models/reload`
- background job status: `/jobs/{job_id}`

## 5.6 Code Execution and Artifacts
- `POST /code-execution/execute-code` (SSE)
- `POST /code-execution/run-generated`
- `GET /artifacts/{artifact_id}`

## 5.7 Realtime
- websocket channel: `/ws/jobs/{user_id}`
- receives material, notebook, podcast, presentation progress events

## 6. Material Ingestion and Processing Pipeline

## 6.1 Ingestion Path
1. upload endpoint validates and persists source metadata
2. material row created with `pending`
3. background job row created (`material_processing`)
4. in-process queue notified (`job_queue.notify()`)

## 6.2 Worker Execution Path
`services/worker.py` loop:
- polls pending jobs with bounded concurrency (`MAX_CONCURRENT_JOBS=5`)
- recovers stuck processing jobs older than threshold
- processes by source type:
  - file -> `process_material_by_id`
  - url/web/youtube -> `process_url_material_by_id`
  - text -> `process_text_material_by_id`
- marks status completed/failed and updates DB
- optionally auto-renames notebook for default names

## 6.3 Material Service Internals
`services/material_service.py` handles:
- extraction output validation
- full-text persistence in storage
- chunking (special structured-data fast path)
- embedding and vector-store write
- integrity checks (`stored_chunks == expected_chunks`)
- material status transitions (`processing -> embedding -> completed/failed`)
- websocket `material_update` events
- background AI title generation and notebook naming

## 7. Chat v2 Orchestration Architecture

## 7.1 Capability Routing
`route_capability` selects between:
- `NORMAL_CHAT`
- `RAG`
- `WEB_SEARCH`
- `WEB_RESEARCH`
- `CODE_EXECUTION`
- `AGENT`
- `IMAGE_GENERATION`

Inputs:
- explicit slash/intents (`/agent`, `/image`, intent override)
- material selection presence
- keyword/task-type inference

Notable policy:
- with selected materials, default path is retrieval-first (`RAG`) unless request is computational/generative, which routes to `AGENT`

## 7.2 Streaming and Persistence
`orchestrator.run`:
- executes selected tool path
- streams token/tool/progress SSE events
- builds LLM prompts with optional history and retrieval context
- persists user + assistant messages
- stores block-level assistant content in `response_blocks`

## 7.3 Source Selection Persistence
Per notebook/user source selection is saved in `notebook_source_selections` and used when request omits material IDs.

## 8. Agent Subsystem (Autonomous Workflow)

## 8.1 Control Loop
`services/agent/agent_orchestrator.py` pipeline:
1. analyze
2. plan
3. execute step + reflect loop
4. synthesize/direct response
5. persist and emit completion metadata

Execution limits:
- max steps: 12
- max tool calls: 15
- max retries per step: 2
- timeout: 600s

## 8.2 Analyze and Planning
- resource profile classification (dataset/document/mixed)
- file-generation intent detection
- intent classification and plan generation via LLM prompts
- fallback plans injected if planner output is empty
- file generation output steps force `python_auto`

## 8.3 Tool Selection and Execution
Tool registry:
- `rag`
- `web_search`
- `research`
- `python_auto` (generate + execute + artifact registration)

Selection policy:
- prioritize planner hint
- enforce retrieval-first for document-only selections
- force `python_auto` for file-output steps

## 8.4 Reflection
On failed step, orchestrator asks reflection prompt for next action:
- continue
- retry with fix
- replan
- complete

## 8.5 Synthesis and Persistence
Final response strategy:
- file generation + artifacts: concise artifact response
- otherwise synthesized narrative from observations/sources/history

Persistence:
- save user goal + assistant message
- link produced artifacts to assistant message
- save response blocks

## 9. Code Execution and Sandbox Architecture

## 9.1 Entry Flow
`/code-execution/execute-code`:
- validates and sanitizes code
- runs in sandbox
- can auto-install approved packages for missing module errors
- may attempt LLM code repair up to configured attempts
- emits SSE progress and result events

## 9.2 Security Layer
`services/code_execution/security.py` enforces:
- blocked imports (OS/process/network/dangerous modules)
- blocked dangerous call patterns (`eval`, `exec`, shell exec)
- path and open-mode checks
- matplotlib/plotly output capture rewriting

## 9.3 Sandbox Runner
`sandbox_runner.py` supports:
- docker-isolated execution (preferred)
- local RLIMIT-based fallback
- network-disabled execution
- output file harvesting from sandbox workdir

## 9.4 Artifact Registration
Generated files are:
1. copied into persistent artifacts directory
2. recorded in `artifacts` table
3. emitted back as artifact SSE events and attached to messages

## 10. Presentation, Explainer, Podcast Pipelines

## 10.1 Presentation
`services/presentation/generator.py`:
- RAG-based context collection from selected materials
- strict JSON payload generation via structured LLM
- render HTML + export PPTX
- store as `generated_content`

`editor_service.py`:
- full deck or single-slide updates
- websocket progress notifications (`presentation_update_progress`)
- regeneration of HTML/PPT outputs

## 10.2 Explainer Video
`routes/explainer.py` + `services/explainer/processor.py`:
- checks/reuses presentation context
- creates explainer DB row with status lifecycle
- captures slide screenshots
- generates per-slide narration scripts
- TTS generation
- composes per-slide videos and concatenates final MP4
- stores final metadata + generated content row

## 10.3 Podcast
`routes/podcast_live.py` + `services/podcast/session_manager.py`:
- create/list/update/delete sessions
- async generation pipeline:
  - script generation (RAG + LLM)
  - segment TTS synthesis with concurrency
  - progressive websocket updates
- Q&A over ongoing session with TTS responses
- bookmarks/annotations
- export and summary endpoints

## 11. Realtime Event Contracts

### 11.1 SSE (Chat + Tools + Agent)
Common chat/tool events include:
- `token`, `done`, `error`
- `tool_start`, `tool_result`
- `meta`, `blocks`
- `web_search_update`, `web_sources`
- `code_block`, `artifact`, `image`
- research stream events (`research_start`, `research_phase`, `research_source`, `citations`, `research_pdf`)
- agent events (`agent_status`, `agent_plan`, `agent_step`, `agent_tool`, `agent_result`, `agent_reflection`, `agent_artifact`, `agent_done`)

### 11.2 Websocket
`/ws/jobs/{user_id}` supports authenticated per-user channels:
- connection/auth handshake with ping/pong keepalive
- material status events
- notebook rename events
- podcast progress/segment/ready events
- presentation update progress events

## 12. Persistence Model (Prisma)
Main tables and relationships:
- `users`
- `notebooks`
- `materials`
- `chat_sessions`, `chat_messages`, `response_blocks`
- `generated_content` (+ join tables)
- `background_jobs`
- `refresh_tokens`
- `code_execution_sessions`
- `research_sessions`
- `podcast_*` entities
- `explainer_videos`
- `artifacts`

Important linkage patterns:
- chat messages belong to notebook + user + optional session
- assistant messages can own many response blocks and artifacts
- notebooks aggregate materials, chats, generated outputs, podcasts

## 13. Security and Risk Posture

Implemented controls:
- JWT auth + refresh rotation and family revocation
- ownership checks on most notebook/material/chat/generation routes
- URL safety checks for URL upload/proxy (private IP blocking)
- path traversal defense via `safe_path`
- sandboxed execution with network restrictions and resource caps

Notable caveats from current code:
- `GET /artifacts/{artifact_id}` serves by artifact ID without explicit `get_current_user` check in route layer
- some file-serving podcast endpoints rely on path/session IDs and do not re-check owner in the route handler itself

## 14. Operational Behavior
- structured logging in app, worker, and agent stages
- request-level performance headers in development
- worker includes stuck-job recovery + old-job cleanup
- graceful shutdown handling for background processor
- model warmup at startup to reduce first-request latency

## 15. End-to-End Sequence Examples

### 15.1 Upload -> Process -> Chat with RAG
1. frontend uploads file to `/upload` or `/upload/batch`
2. backend creates material + background job
3. worker extracts/chunks/embeds material
4. websocket emits `material_update`
5. user sends chat request with selected materials
6. chat orchestrator runs RAG tool and streams response
7. messages and blocks persist to DB

### 15.2 Agent File Generation
1. user sends `/agent` request with file-generation goal
2. agent classifies as file generation and plans steps
3. `python_auto` generates and executes code in sandbox
4. artifacts are detected, registered, linked to message
5. frontend receives agent and artifact SSE events for display/download
