# KeplerLab Backend - Complete Architecture and Feature Flow

## 1. Scope and What Was Read

This document is built from a full backend workspace scan and direct reads of key runtime files.

- Workspace root: `/disk1/KeplerLab_Agentic`
- Backend folder: `backend/`
- Total files under backend folder (including generated/cache/data): `1626`
- Source-focused backend files (excluding `__pycache__`): `189`
- Core runtime files read directly: `app/main.py`, `app/core/config.py`, `prisma/schema.prisma`, major route files, chat router, worker/auth/orchestrator services, websocket manager.

Notes:
- Generated/cache/runtime directories exist (`__pycache__`, logs, output artifacts, uploaded/generated data).
- This doc focuses on implementation source of truth and runtime architecture.

## 2. High-Level Backend Architecture

The backend is a FastAPI monolith organized by layered domains.

- API layer: `app/routes/`
- Business logic layer: `app/services/`
- Data models/contracts: `app/models/` and Pydantic request/response schemas inside route/service modules
- Persistence:
- PostgreSQL via Prisma async client (`app/db/prisma_client.py` + `prisma/schema.prisma`)
- Chroma vector store (`app/db/chroma.py`) for embeddings
- Prompt system: `app/prompts/` (chat, code, generation, system, shared)
- Async background processing: `app/services/worker.py` and `app/services/job_service.py`
- Realtime channel: websocket connection manager + route (`app/services/ws_manager.py`, `app/routes/websocket_router.py`)

## 3. App Startup and Runtime Lifecycle

Source: `backend/app/main.py`.

### 3.1 Startup Sequence

On app lifespan startup:

1. Connect Prisma DB (`connect_db`).
2. Warm embedding model in thread pool (`services/rag/embedder.py`).
3. Preload reranker in thread pool (`services/rag/reranker.py`).
4. Start background job processor task (`services/worker.py:job_processor`).
5. Ensure sandbox/on-demand code execution packages (`services/code_execution/sandbox_env.py`).
6. Cleanup stale temp sandbox directories (`/tmp/kepler_sandbox_*`, `/tmp/kepler_analysis_*`).
7. Ensure output directories exist (`output/generated`, `output/presentations`, `output/explainers`, `output/podcast`, `data/artifacts`).
8. Cleanup expired refresh tokens at startup.

### 3.2 Middleware and Error Handling

Applied middleware stack:

1. Performance monitoring middleware (`services/performance_logger.py`).
2. Rate limiter middleware (`services/rate_limiter.py`).
3. Request logger middleware with generated request ID and timing.
4. CORS middleware (`settings.CORS_ORIGINS`).
5. Trusted host middleware in production.

Error handling:

- `HTTPException` => JSON with explicit detail and CORS headers.
- Unhandled exceptions => HTTP 500 with `request_id` for traceability.

### 3.3 Shutdown Sequence

1. Graceful worker shutdown signal.
2. Cancel/wait for background job task with timeout.
3. Disconnect Prisma DB.

## 4. Configuration Model

Source: `backend/app/core/config.py`.

Major config domains:

- Environment: `ENVIRONMENT`, `DEBUG`
- Persistence: `DATABASE_URL`, `CHROMA_DIR`
- Storage paths: `UPLOAD_DIR`, `WORKSPACE_BASE_DIR`, `ARTIFACTS_DIR`, output dirs
- Upload and processing limits:
- `MAX_UPLOAD_SIZE_MB=10240`
- `OCR_TIMEOUT_SECONDS=300`
- `WHISPER_TIMEOUT_SECONDS=600`
- `LIBREOFFICE_TIMEOUT_SECONDS=120`
- Code execution controls:
- `CODE_EXECUTION_TIMEOUT=15`
- `MAX_CODE_REPAIR_ATTEMPTS=3`
- Auth/JWT:
- `JWT_SECRET_KEY`, `JWT_ALGORITHM=HS256`
- Access token expiry (minutes), refresh token expiry (days)
- Secure refresh cookie settings
- LLM/provider controls:
- `LLM_PROVIDER` in `{MYOPENLM, GOOGLE, NVIDIA, OLLAMA}`
- provider-specific model names and keys
- temperature/top-p/token controls
- RAG controls:
- embedding/reranker model IDs
- retrieval K values, MMR lambda
- chunk overlap/length/similarity thresholds
- External endpoints:
- image/web search/web scraping endpoint hooks

Validators in config enforce:

- `JWT_SECRET_KEY` must exist
- `DATABASE_URL` must exist
- `LLM_PROVIDER` must be one of supported providers
- Relative paths are normalized to project-root absolute paths
- In production: `COOKIE_SECURE=True`

## 5. Data Architecture (Prisma Schema)

Source: `backend/prisma/schema.prisma`.

### 5.1 Core Entities

- `User`
- `Notebook`
- `Material`
- `ChatSession`
- `ChatMessage`
- `ResponseBlock`
- `GeneratedContent`
- `GeneratedContentMaterial` (join table)
- `Artifact`
- `BackgroundJob`
- `RefreshToken`
- `ExplainerVideo`
- `CodeExecutionSession`
- `ResearchSession`
- Podcast suite:
- `PodcastSession`
- `PodcastSegment`
- `PodcastDoubt`
- `PodcastExport`
- `PodcastBookmark`
- `PodcastAnnotation`
- `PodcastSessionMaterial` (join table)
- Observability/audit:
- `UserTokenUsage`
- `ApiUsageLog`
- `AgentExecutionLog`

### 5.2 Key State Enums

- Material/job lifecycle: `pending`, `processing`, `ocr_running`, `transcribing`, `embedding`, `completed`, `failed`
- Explainer video status lifecycle
- Podcast session status lifecycle

### 5.3 Important Relations

- User owns notebooks/materials/chats/generated content/jobs/artifacts.
- Notebook links materials/chats/generated content/research/code-exec/podcast/artifacts.
- ChatMessage can have many ResponseBlocks and Artifacts.
- GeneratedContent can have many materials via join table.
- PodcastSession can have many materials via join table and many segments/doubts/exports/bookmarks/annotations.

## 6. API Surface - Complete Route Map

Route files under `app/routes/` + `app/services/presentation/router.py`.

### 6.1 Health and System

- `GET /health`
- `GET /health/simple`
- `GET /models/status`
- `POST /models/reload`

### 6.2 Auth

- `POST /auth/signup`
- `POST /auth/login`
- `POST /auth/refresh`
- `GET /auth/me`
- `POST /auth/logout`

### 6.3 Notebook

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

### 6.4 Materials and Upload

- `GET /materials`
- `PATCH /materials/{material_id}`
- `DELETE /materials/{material_id}`
- `GET /materials/{material_id}/text`
- `POST /upload`
- `POST /upload/batch`
- `POST /upload/url`
- `POST /upload/text`
- `GET /upload/supported-formats`

### 6.5 Chat (chat_v2 router)

- `POST /chat`
- `POST /chat/block-followup`
- `POST /chat/optimize-prompts`
- `POST /chat/suggestions`
- `POST /chat/empty-suggestions`
- `GET /chat/history/{notebook_id}`
- `DELETE /chat/history/{notebook_id}`
- `GET /chat/sessions/{notebook_id}`
- `POST /chat/sessions`
- `DELETE /chat/sessions/{session_id}`
- `DELETE /chat/message/{message_id}`
- `PATCH /chat/message/{message_id}`

### 6.6 Generation Features

- Flashcard:
- `POST /flashcard`
- `POST /flashcard/suggest`
- Quiz:
- `POST /quiz`
- `POST /quiz/suggest`
- Mindmap:
- `POST /mindmap`
- AI resource builder:
- `POST /ai-resource-builder`

### 6.7 Presentation and Explainer

Two presentation routers coexist under prefix `/presentation`:

- Legacy PPT route file: `app/routes/ppt.py`
- Structured presentation service router: `app/services/presentation/router.py`

Presentation endpoints combined:

- `POST /presentation`
- `POST /presentation/suggest`
- `POST /presentation/async`
- `GET /presentation/slides/{user_id}/{presentation_id}/{filename}`
- `POST /presentation/generate`
- `GET /presentation/{presentation_id}`
- `GET /presentation/{presentation_id}/html`
- `GET /presentation/{presentation_id}/ppt`
- `GET /presentation/{presentation_id}/download`
- `POST /presentation/update`

Explainer:

- `POST /explainer/check-presentations`
- `POST /explainer/generate`
- `GET /explainer/{explainer_id}/status`
- `GET /explainer/{explainer_id}/video`

### 6.8 Podcast Live

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

### 6.9 Other Runtime Endpoints

- Code execution:
- `POST /code-execution/execute-code`
- `POST /code-execution/run-generated`
- Search:
- `POST /search/web`
- Jobs:
- `GET /jobs/{job_id}`
- Artifacts:
- `GET /artifacts/{artifact_id}`
- Proxy:
- `GET /api/v1/file-viewer/info`
- Websocket channel prefix:
- `/ws` (route file provides ws job channel)

## 7. End-to-End Feature Flows

## 7.1 Upload -> Processing -> Embedding -> Availability

1. Request enters `/upload*`.
2. Input validated (`file_validator`, route-level checks).
3. Material DB row created in pending status.
4. Background job created (`job_service`).
5. Worker polls every 2s, pulls pending jobs with locking pattern.
6. Worker dispatches by source type:
- file -> `process_material_by_id`
- url/web/youtube -> `process_url_material_by_id`
- text -> `process_text_material_by_id`
7. Text extraction/chunking/embedding pipelines run.
8. Material status updated through lifecycle states.
9. Completion updates visible to client (via websocket polling/updates).

Operational details:

- Concurrency cap: `MAX_CONCURRENT_JOBS=5`.
- Stuck job recovery: processing jobs older than timeout reset to pending on startup.
- Old job cleanup: periodic deletion of old completed/failed jobs.

## 7.2 Chat Request Orchestration

Source roots:

- `app/services/chat_v2/router.py`
- `app/services/chat_v2/orchestrator.py`

Flow:

1. Validate selected materials belong to notebook/user.
2. Filter only completed materials.
3. Ensure/create chat session.
4. Route capability by intent and context (`router_logic.py`):
- `RAG`
- `WEB_SEARCH`
- `WEB_RESEARCH`
- `CODE_EXECUTION`
- `AGENT`
- `IMAGE_GENERATION`
5. Execute capability path:
- RAG tool / web tool / research tool / python tool / agent pipeline / image generation
6. Stream SSE chunks/events to client.
7. Persist message, response blocks, metadata, and artifacts.

## 7.3 Agentic Pipeline

Source roots: `app/services/agent/*`.

Pipeline stages:

1. Plan generation (`planner.py`).
2. Step-wise execution (`executor.py`, `tool_selector.py`, `tools_registry.py`).
3. Reflection/continuation logic.
4. Synthesis response generation.
5. Artifact registration + persistence.

Safety controls are implemented in orchestration and code-exec path (max steps/tool-call windows, retries, execution time limits).

## 7.4 Code Execution Path

Source roots:

- Route: `app/routes/code_execution.py`
- Engine: `app/services/code_execution/sandbox.py`
- Security: `app/services/code_execution/security.py`
- Environment provisioning: `sandbox_env.py`

Flow:

1. Accept code execution request with language/timeout/stdin.
2. Run security checks and sanitization.
3. Execute in isolated workspace/sandbox context.
4. Capture stdout/stderr/plots/files.
5. Return stream and/or artifact references.

## 7.5 RAG and Retrieval

Source roots: `app/services/rag/*`.

Flow:

1. Material chunks embedded and stored in Chroma.
2. Query retrieval via secure retriever with user/material notebook constraints.
3. Optional MMR and reranking.
4. Context formatting + LLM synthesis.
5. Citation validation pass.

## 7.6 Presentation / Explainer / Podcast

Presentation:

- Generation and update via `services/presentation/*` plus legacy PPT generator path.
- Export paths for HTML/PPT/PDF.

Explainer:

- Presentation-to-video pipeline (script + TTS + composition).

Podcast:

- Session creation + script/audio generation + interactive Q&A/bookmarks/annotations/export.

## 8. Authentication and Session Security Flow

Source roots:

- `app/services/auth/security.py`
- `app/services/auth/service.py`
- `app/routes/auth.py`

Flow:

1. Signup hashes password and stores user.
2. Login verifies password and issues:
- short-lived access token (bearer)
- refresh token (cookie)
3. Refresh endpoint rotates refresh token with family/reuse detection.
4. Token reuse triggers family revocation.
5. Startup and periodic cleanup remove expired tokens.

## 9. Realtime and Async Infrastructure

### 9.1 Websocket Manager

Source: `app/services/ws_manager.py`.

- Per-user connection registry.
- Max 10 concurrent websocket connections per user.
- Supports user-targeted send and broadcast.
- Dead connections are pruned on send failures.

### 9.2 Worker Queue

Source: `app/services/worker.py` + `app/services/job_service.py`.

- Poll loop with event-notify optimization.
- Concurrent processing with backoff on loop errors.
- Graceful shutdown with timeout.

## 10. Prompt and LLM Instruction Assets

Prompt packs under `app/prompts/`:

- `chat/`: chat behavior, block actions, synthesis
- `code/`: code generation/execution prompting
- `generation/`: quiz/flashcard/mindmap/presentation/podcast/etc.
- `system/`: planner/reflection/tool/router/system prompts
- `shared/`: style/reasoning/formatting/safety

This structure allows centralized prompt governance while feature services call into consistent prompt assets.

## 11. CLI and Operational Utilities

`backend/cli/` includes maintenance workflows:

- `download_models.py`
- `reindex.py`
- `backup_chroma.py`
- `export_embeddings.py`
- `import_embeddings.py`
- `migrate_material_joins.py`

Used for indexing/model bootstrap/data migration/backup operations.

## 12. Backend Source Inventory (Complete, Source-Focused)

All source-focused backend files discovered:

```text
app/core/config.py
app/core/__init__.py
app/core/utils.py
app/core/web_search.py
app/db/chroma.py
app/db/__init__.py
app/db/prisma_client.py
app/__init__.py
app/main.py
app/models/__init__.py
app/models/model_schemas.py
app/models/shared_enums.py
app/prompts/chat/agent_synthesis.md
app/prompts/chat/block_ask.md
app/prompts/chat/block_explain.md
app/prompts/chat/block_simplify.md
app/prompts/chat/block_translate.md
app/prompts/chat/chat_agent.md
app/prompts/chat/chat_base.md
app/prompts/chat/chat_rag.md
app/prompts/chat/direct_response.md
app/prompts/chat/web_search_synthesis.md
app/prompts/code/code_execution.md
app/prompts/code/code_generation.md
app/prompts/generation/explainer.md
app/prompts/generation/flashcard.md
app/prompts/generation/flashcard_suggest.md
app/prompts/generation/mindmap.md
app/prompts/generation/notes.md
app/prompts/generation/optimize.md
app/prompts/generation/podcast.md
app/prompts/generation/podcast_qa.md
app/prompts/generation/presentation.md
app/prompts/generation/presentation_suggest.md
app/prompts/generation/quiz.md
app/prompts/generation/quiz_suggest.md
app/prompts/generation/study_guide.md
app/prompts/generation/summary.md
app/prompts/generation/web_completeness_check.md
app/prompts/__init__.py
app/prompts/shared/formatting.md
app/prompts/shared/reasoning.md
app/prompts/shared/safety.md
app/prompts/shared/style.md
app/prompts/system/agent_intent_classifier.md
app/prompts/system/agent_planner.md
app/prompts/system/agent_reflection.md
app/prompts/system/agent_system.md
app/prompts/system/agent_tool_selector.md
app/prompts/system/base_system.md
app/prompts/system/json_repair.md
app/prompts/system/rag_system.md
app/prompts/system/tool_system.md
app/routes/ai_resource.py
app/routes/artifacts.py
app/routes/auth.py
app/routes/chat.py
app/routes/code_execution.py
app/routes/explainer.py
app/routes/flashcard.py
app/routes/health.py
app/routes/__init__.py
app/routes/jobs.py
app/routes/materials.py
app/routes/mindmap.py
app/routes/models.py
app/routes/notebook.py
app/routes/podcast_live.py
app/routes/ppt.py
app/routes/proxy.py
app/routes/quiz.py
app/routes/search.py
app/routes/upload.py
app/routes/utils.py
app/routes/websocket_router.py
app/services/agent/agent_orchestrator.py
app/services/agent/artifact_executor.py
app/services/agent/executor.py
app/services/agent/__init__.py
app/services/agent/kepler_fpdf.py
app/services/agent/log_utils.py
app/services/agent/material_files.py
app/services/agent/memory.py
app/services/agent/planner.py
app/services/agent/prompts.py
app/services/agent/resource_router.py
app/services/agent/state.py
app/services/agent/tool_selector.py
app/services/agent/tools_registry.py
app/services/ai_resource_builder.py
app/services/auth/__init__.py
app/services/auth/security.py
app/services/auth/service.py
app/services/chat_v2/context_builder.py
app/services/chat_v2/__init__.py
app/services/chat_v2/message_store.py
app/services/chat_v2/orchestrator.py
app/services/chat_v2/prompt_optimizer.py
app/services/chat_v2/router_logic.py
app/services/chat_v2/router.py
app/services/chat_v2/schemas.py
app/services/chat_v2/service.py
app/services/chat_v2/streaming.py
app/services/code_execution/__init__.py
app/services/code_execution/sandbox_env.py
app/services/code_execution/sandbox.py
app/services/code_execution/security.py
app/services/explainer/__init__.py
app/services/explainer/processor.py
app/services/explainer/script_generator.py
app/services/explainer/tts.py
app/services/explainer/video_composer.py
app/services/file_validator.py
app/services/flashcard/generator.py
app/services/flashcard/__init__.py
app/services/image_generation/gemini_service.py
app/services/__init__.py
app/services/job_service.py
app/services/llm_service/__init__.py
app/services/llm_service/llm.py
app/services/llm_service/llm_schemas.py
app/services/llm_service/structured_invoker.py
app/services/material_service.py
app/services/mindmap/generator.py
app/services/model_manager.py
app/services/notebook_name_generator.py
app/services/notebook_service.py
app/services/notebook_thumbnail_service.py
app/services/performance_logger.py
app/services/podcast/export_service.py
app/services/podcast/__init__.py
app/services/podcast/qa_service.py
app/services/podcast/satisfaction_detector.py
app/services/podcast/script_generator.py
app/services/podcast/session_manager.py
app/services/podcast/tts_service.py
app/services/podcast/voice_map.py
app/services/ppt/generator.py
app/services/ppt/__init__.py
app/services/ppt/screenshot_service.py
app/services/ppt/slide_extractor.py
app/services/presentation/editor_service.py
app/services/presentation/generator.py
app/services/presentation/html_renderer.py
app/services/presentation/__init__.py
app/services/presentation/pdf_exporter.py
app/services/presentation/ppt_exporter.py
app/services/presentation/router.py
app/services/presentation/schemas.py
app/services/quiz/generator.py
app/services/quiz/__init__.py
app/services/rag/citation_validator.py
app/services/rag/context_builder.py
app/services/rag/context_formatter.py
app/services/rag/embedder.py
app/services/rag/__init__.py
app/services/rag/pipeline.py
app/services/rag/reranker.py
app/services/rag/secure_retriever.py
app/services/rate_limiter.py
app/services/research/__init__.py
app/services/research/pdf_exporter.py
app/services/research/pipeline.py
app/services/storage_service.py
app/services/text_processing/chunker.py
app/services/text_processing/extractor.py
app/services/text_processing/file_detector.py
app/services/text_processing/__init__.py
app/services/text_processing/ocr_service.py
app/services/text_processing/pdf_extractor.py
app/services/text_processing/resilient_runner.py
app/services/text_processing/transcription_service.py
app/services/text_processing/web_scraping.py
app/services/text_processing/youtube_service.py
app/services/tools/__init__.py
app/services/tools/python_tool.py
app/services/tools/rag_tool.py
app/services/tools/research_tool.py
app/services/tools/web_search_tool.py
app/services/worker.py
app/services/ws_manager.py
cli/backup_chroma.py
cli/download_models.py
cli/export_embeddings.py
cli/import_embeddings.py
cli/__init__.py
cli/migrate_material_joins.py
cli/reindex.py
prisma/schema.prisma
```

## 13. Backend Dependencies Snapshot

Primary backend dependencies from `backend/requirements.txt` include:

- FastAPI/Uvicorn ecosystem
- LangChain/LangGraph + multiple model providers
- Sentence-transformers + Torch + Transformers
- Chroma vector DB
- Prisma client
- OCR/transcription stack (pytesseract/easyocr/whisper)
- Document/media processing stack (pypdf/pymupdf/pdf2image/python-pptx/ffmpeg)
- Web scraping/search support (`ddgs`, `trafilatura`, `youtube-transcript-api`, `yt-dlp`)
- Security/auth (`python-jose`, `passlib`, `bcrypt`)
- Testing (`pytest`, `pytest-asyncio`)

---

If you want, a second pass can add function-level call graphs for each route handler (per endpoint -> exact service functions -> exact DB table mutations).
