# KeplerLab — Full Codebase Audit & Problem Report

> **Generated:** March 4, 2026  
> **Scope:** Complete backend + frontend + database + CLI analysis  
> **Codebase:** ~25,000+ lines Python (backend) + ~14,000 lines JS/JSX (frontend)

---

## Table of Contents

1. [Critical / Blocking Issues](#1-critical--blocking-issues)
2. [Security Vulnerabilities](#2-security-vulnerabilities)
3. [Dead Code & Unused Imports](#3-dead-code--unused-imports)
4. [Bad Flow / Unnecessary Steps](#4-bad-flow--unnecessary-steps)
5. [Production Readiness Gaps](#5-production-readiness-gaps)
6. [Database Schema Issues](#6-database-schema-issues)
7. [Code Architecture Problems](#7-code-architecture-problems)
8. [Frontend-Specific Issues](#8-frontend-specific-issues)
9. [Inconsistencies & Code Smells](#9-inconsistencies--code-smells)
10. [Prompt System Issues](#10-prompt-system-issues)
11. [Dependency & Config Issues](#11-dependency--config-issues)
12. [Performance Issues](#12-performance-issues)
13. [What Works Well](#13-what-works-well)

---

## 1. Critical / Blocking Issues

These will crash, break, or silently fail in production.

### 1.1 Missing Prompt Template Files — Runtime Crash

**Files:** `backend/app/prompts/__init__.py`

The prompt loader exposes `get_presentation_intent_prompt()`, `get_presentation_strategy_prompt()`, and `get_slide_content_prompt()` — all referencing `.txt` files that **do not exist** on disk:
- `presentation_intent_prompt.txt` — missing
- `presentation_strategy_prompt.txt` — missing  
- `slide_content_prompt.txt` — missing

Calling any of these functions will crash with `FileNotFoundError`.

### 1.2 Missing Prompt Loader Functions — Orphaned Prompts

5 out of 12 prompt files have **no loader function** in `__init__.py`:
- `podcast_script_prompt.txt` — no loader
- `podcast_qa_prompt.txt` — no loader
- `code_generation_prompt.txt` — no loader
- `code_repair_prompt.txt` — no loader
- `data_analysis_prompt.txt` — no loader

These prompts are loaded by their respective services using direct file reads, bypassing the centralized loader entirely. The loader pattern is inconsistently applied.

### 1.3 GPU Manager Concurrency Bug

**File:** `backend/app/services/gpu_manager.py`

`GPUManager` uses **two independent locks**: `threading.Lock` for sync callers and `asyncio.Lock` for async callers. These locks **do not cross-protect** — a sync GPU session and an async GPU session can execute simultaneously, causing CUDA race conditions, OOM errors, or corrupted tensors.

### 1.4 Async PPT Only Supports Single Material

**File:** `backend/app/routes/ppt.py` → `generate_ppt_async`

The sync `generate_ppt` endpoint handles both `material_id` (single) and `material_ids` (multiple), but the async version `generate_ppt_async` only processes a single `material_id`. Multi-material async PPT generation silently drops all extra materials.

---

## 2. Security Vulnerabilities

### 2.1 HIGH — Path Traversal in Podcast Routes

**File:** `backend/app/routes/podcast_live.py`

- `get_audio_file` accepts raw `filename` from URL path — not sanitized with `os.path.basename()` or `safe_path()`.
- `download_export` accepts raw `filename` from URL — same issue.

An attacker could request `/podcast/session/{id}/audio/../../etc/passwd` depending on how `get_audio_file_path()` handles it.

### 2.2 HIGH — `dangerouslySetInnerHTML` Without Sanitization

**File:** `frontend/src/components/presentation/PresentationView.jsx`

Slide HTML content from the LLM is rendered with `dangerouslySetInnerHTML` with **no DOMPurify or sanitization**. If a user uploads materials containing XSS payloads, the LLM could reproduce them in slide content.

### 2.3 HIGH — No Rate Limiting on Auth Endpoints

**File:** `backend/app/routes/auth.py`

`/auth/login` and `/auth/signup` have no rate limiting at the route level. While the middleware has some IP-based auth rate limiting, it's **in-memory only** and lost on restart. Brute-force attacks go unimpeded across restarts.

### 2.4 MEDIUM — Auto-Install Pip Packages from LLM Code

**File:** `backend/app/services/code_execution/sandbox_env.py`

The sandbox auto-installs missing pip packages when LLM-generated code references them. A malicious or manipulated LLM response could trigger installation of arbitrary packages containing malware.

### 2.5 MEDIUM — `delete_uploaded_file()` Accepts Arbitrary Paths

**File:** `backend/app/services/storage_service.py`

`delete_uploaded_file(path)` accepts any file path and deletes it — no validation that the path is within the uploads directory. A bug in any caller could delete system files.

### 2.6 MEDIUM — Unauthenticated TTS Generation

**File:** `backend/app/routes/podcast_live.py`

`/podcast/voice/preview` requires no authentication. An attacker can submit unlimited TTS requests, consuming GPU/CPU resources. Should have at minimum IP-based rate limiting.

### 2.7 MEDIUM — Error Messages Leak Internal Details

**Files:** `backend/app/routes/ppt.py`, `backend/app/routes/chat.py`

Exception details are returned to the client in error responses:
```python
f"Failed to generate presentation: {str(e)}"  # ppt.py L112
```
Stack traces and internal error messages should never reach the client.

### 2.8 MEDIUM — PII Logging

**File:** `backend/app/routes/auth.py`

Email addresses are logged at INFO level:
```python
logger.info(f"Signup attempt for email: {request.email}")
```
PII (email) in application logs violates GDPR and creates compliance risk.

### 2.9 MEDIUM — No CSRF on Cookie-Based Refresh

**File:** `backend/app/routes/auth.py`

The `/auth/refresh` endpoint uses HttpOnly cookies with `credentials: 'include'` but has **no CSRF token**. `SameSite=lax` helps but is not a complete defense.

### 2.10 MEDIUM — Missing Export Ownership Validation

**File:** `backend/app/routes/podcast_live.py`

`get_export_status` at line ~353 doesn't verify the export belongs to the requesting user. Any authenticated user could poll another user's export status by guessing the export ID (UUID).

### 2.11 LOW — HTTP Allowed for URL Uploads

**File:** `backend/app/routes/upload.py`

URL uploads accept both `http://` and `https://`, while the proxy endpoint enforces `https://` only. This inconsistency may expose users to MITM attacks when uploading from HTTP sources.

### 2.12 LOW — Wide CORS on File Viewer Proxy

**File:** `backend/app/routes/proxy.py`

The file-viewer proxy sets `Access-Control-Allow-Origin: *`, opening CORS for any origin to access proxied file content.

### 2.13 LOW — No WebSocket Connection Limits

**File:** `backend/app/routes/websocket_router.py`

No cap on concurrent WebSocket connections per user. A single user could open hundreds of connections, exhausting server resources.

### 2.14 LOW — SQL Injection Risk (Theoretical)

**File:** `backend/app/services/audit_logger.py`

`get_usage_statistics()` builds SQL via f-string interpolation. Currently safe because only trusted values are interpolated, but fragile to future changes.

---

## 3. Dead Code & Unused Imports

### 3.1 Backend Dead Code

| Location | What's Dead | Why |
|----------|------------|-----|
| `routes/chat.py` | `ClearChatRequest` model | Defined but never referenced by any endpoint |
| `routes/upload.py` | `ALLOWED_MIME_TYPES` set (line ~43) | Defined but validation uses `FileTypeDetector` instead |
| `routes/upload.py` | `process_url_material`, `process_text_material` imports | Imported but never called (replaced by background worker) |
| `routes/mindmap.py` | `import asyncio`, `import MindMapResponse` | Imported but never used |
| `routes/proxy.py` | `import HTMLResponse` | Imported but never used |
| `services/worker.py` | Top-level `from storage_service import load_material_text` | Re-imported inside function body; top-level import is dead |
| `services/gpu_manager.py` | `gpu_session()` sync method | No current caller uses the sync context manager |
| `services/material_service.py` | `process_material()`, `process_url_material()`, `process_text_material()` | Legacy wrappers replaced by the background job pattern |
| `services/tts_provider/` | **Entire directory** | Contains only `__pycache__/` — source files deleted without cleanup |
| `services/yt_translation/` | **Entire directory** | Contains only `__pycache__/` — source files deleted without cleanup |
| `cli/backup_chroma.py` | `import shutil` | Imported but never used |

### 3.2 Frontend Dead Code

| Location | What's Dead | Why |
|----------|------------|-----|
| `lib/utils/constants.js` | `QUICK_ACTIONS` constant | Defined but never imported anywhere |
| `lib/utils/constants.js` | `API_FALLBACK_URL` constant | Defined but never imported |
| `lib/api/explainer.js` | `getExplainerStatus` function | Exported but import removed from `InlineExplainerView` |
| `components/auth/` | **Entire directory** | Empty directory — no files |
| `lib/chakra/provider.jsx` | Chakra UI token definitions (colors, radii, fonts) | Tokens defined but no Chakra components consume them |
| `lib/utils/helpers.js` | `parseSlashCommand` | Duplicated in `slashCommands.js` with different signature; ChatPanel imports from `slashCommands.js` |

---

## 4. Bad Flow / Unnecessary Steps

### 4.1 Duplicate Embedding Models — Redundant Overhead

The system loads **two separate embedding models**:
1. `sentence-transformers/all-MiniLM-L6-v2` (384-dim) — used solely by ChromaDB collection
2. `BAAI/bge-m3` (1024-dim) — used by the RAG retrieval pipeline

The RAG system queries ChromaDB which internally uses MiniLM, then re-embeds with BGE-M3 for reranking. This means:
- **Double memory usage** (~1.5GB extra for the second model)
- **Semantic mismatch** — ChromaDB stores MiniLM embeddings but the RAG pipeline thinks in BGE-M3 space

This should be unified to a single embedding model.

### 4.2 Sequential Material Text Loading

**File:** `backend/app/routes/utils.py` → `require_materials_text()`

When multiple material IDs are provided, text is loaded **sequentially** in a loop:
```python
for mid in material_ids:
    text = await require_material_text(mid, user_id)
```
Should use `asyncio.gather()` for parallel loading.

### 4.3 Monthly Token Usage Summed in Python

**File:** `backend/app/services/token_counter.py` → `get_user_monthly_usage()`

Loads all daily records for the month from DB and sums in Python:
```python
records = await prisma.usertokenusage.find_many(...)
total = sum(r.tokensUsed for r in records)
```
Should use SQL `SUM()` aggregation instead.

### 4.4 Mixed Material + Upload Routes

**File:** `backend/app/routes/upload.py` (680 lines)

Material CRUD endpoints (`/materials`, `/materials/{id}`, etc.) are crammed into the upload route file. These are separate concerns and should live in a `materials.py` route module.

### 4.5 Duplicate DifficultyLevel Enum

**Files:** `backend/app/routes/flashcard.py` and `backend/app/routes/quiz.py`

Both define identical `DifficultyLevel` enums. Should be defined once in a shared location (e.g., `models/`).

### 4.6 Duplicate PPT Route Registration

**File:** `backend/app/routes/ppt.py`

The slide image endpoint is registered twice:
```python
@router.get("/presentation/slides/{user_id}/{presentation_id}/{filename}")
@router.get("/api/presentation/slides/...", include_in_schema=False)
```
This `/api/` prefix workaround suggests a frontend routing issue that should be fixed at the proxy layer, not duplicated on the backend.

### 4.7 Chakra UI Loaded But Not Used

**File:** `frontend/src/lib/chakra/provider.jsx`, `frontend/src/app/providers.jsx`

The entire Chakra UI library (~50-100KB gzipped) is loaded, wrapped around the app, and has custom tokens defined — but **zero Chakra UI components are used anywhere**. The entire app uses Tailwind CSS. This is pure dead weight.

### 4.8 Redundant FOUC Prevention

**File:** `frontend/src/app/layout.jsx`

A manual `<script dangerouslySetInnerHTML>` injects theme-detection JS to prevent flash of unstyled content. But `next-themes` (already installed and used) handles this automatically. The manual script is redundant.

### 4.9 No Prompt Loader Consistency

Half the prompts go through the centralized `_load()` + `_render()` system in `prompts/__init__.py`, while the other half are loaded directly by services using `open()`. This dual-loading pattern means:
- No single place to see all prompts
- No consistent caching behavior
- Some prompts are `@lru_cache`'d, others are re-read from disk every call

---

## 5. Production Readiness Gaps

### 5.1 In-Memory Rate Limiter — Breaks with Multiple Workers

**File:** `backend/app/services/rate_limiter.py`

Rate limits use a Python `defaultdict(list)` in memory. This means:
- Limits reset on every server restart
- In multi-worker setups (uvicorn with `--workers N`), each worker has its own counter
- Effectively no rate limiting in production

**Fix:** Use Redis-based sliding window (e.g., `redis` + Lua scripts).

### 5.2 In-Memory WebSocket Manager — Single Process Only

**File:** `backend/app/services/ws_manager.py`

`ConnectionManager` stores connections in a process-local `defaultdict`. With multiple workers:
- A user connected to Worker A won't get notifications from Worker B
- No pub/sub backbone (Redis Pub/Sub, etc.)

### 5.3 No Test Suite

- **Backend:** `pytest` is in `requirements.txt` but there are **zero test files** anywhere in the project.
- **Frontend:** No test framework installed. No `jest`, `vitest`, `@testing-library`, `playwright`, or `cypress` in `package.json`. No `test` script.

### 5.4 No TypeScript

The entire frontend (~14,000 lines) is plain JavaScript with no type checking. No `tsconfig.json`, no `// @ts-check` annotations.

### 5.5 `reactStrictMode: false`

**File:** `frontend/next.config.mjs`

Strict Mode is disabled with comment "for SSE/WS". This masks bugs (stale closures, missing cleanups) instead of fixing them.

### 5.6 No Error Tracking / Monitoring

No Sentry, DataDog, LogRocket, or any error tracking service integrated in frontend or backend.

### 5.7 No Bundle Analysis

No `@next/bundle-analyzer` or similar tool. Bundle size is unmonitored.

### 5.8 No Database Migration Strategy

The Prisma schema exists but there's no visible migration history (`prisma/migrations/` directory). Schema changes are likely applied with `prisma db push` (destructive in production).

### 5.9 No Job Cleanup / TTL

**File:** `backend/app/services/job_service.py`

Completed and failed jobs accumulate in `BackgroundJob` table forever. No cleanup cron, no TTL, no archival strategy.

### 5.10 No Graceful Request Draining

While the worker has graceful shutdown, the FastAPI app itself doesn't implement connection draining. In-flight HTTP requests are killed on deploy.

### 5.11 `images.remotePatterns` Only Allows localhost

**File:** `frontend/next.config.mjs`

```js
remotePatterns: [{ protocol: 'https', hostname: 'localhost', port: '8000' }]
```
This will fail in production — `localhost` over `https` on port `8000` doesn't make sense and no production domain is configured.

---

## 6. Database Schema Issues

### 6.1 Missing Foreign Keys (Referential Integrity Holes)

Four models store `notebookId` as a plain UUID string **without a FK relation**:

| Model | Field | Missing Relation |
|-------|-------|-----------------|
| `AgentExecutionLog` | `notebookId` | No FK to `Notebook` |
| `CodeExecutionSession` | `notebookId` | No FK to `Notebook` |
| `ResearchSession` | `notebookId` | No FK to `Notebook` |
| `PodcastSession` | `notebookId` | No FK to `Notebook` |

If a notebook is deleted, these records reference a non-existent notebook with no cascade.

### 6.2 `materialIds` as String Arrays Instead of Join Tables

**Models:** `GeneratedContent`, `PodcastSession`

`materialIds String[]` breaks referential integrity. If materials are deleted, stale IDs remain in the array with no FK enforcement. Should be a many-to-many join table.

### 6.3 Duplicate Enums

`MaterialStatus` and `JobStatus` have **identical values** (`pending`, `processing`, `ocr_running`, `transcribing`, `embedding`, `completed`, `failed`). Should share one enum or be intentionally differentiated.

### 6.4 Missing Indexes on Hot Tables

| Table | Missing Index | Impact |
|-------|---------------|--------|
| `ChatMessage` | `notebookId` | Chat history queries scan full table |
| `ChatMessage` | Composite `(notebookId, createdAt)` | Sort-by-time queries unoptimized |
| `GeneratedContent` | `notebookId`, `userId`, `contentType` | Content listing queries unoptimized |

### 6.5 String Fields Where Enums Should Be

| Model | Field | Current Type | Should Be |
|-------|-------|-------------|-----------|
| `User` | `role` | `VarChar(50)` | Enum (`USER`, `ADMIN`) |
| `ExplainerVideo` | `status` | `VarChar(30)` | Enum |
| `PodcastExport` | `status` | `VarChar(20)` | Enum |

### 6.6 `metadata` as String Instead of JSON

**Model:** Multiple models store metadata as `String @db.Text` when it should be `Json?` for queryability and type safety. The schema itself has a comment: `// consider migrating to Json type`.

### 6.7 No Soft Delete on Users

`User` deletions cascade, destroying **all** user data (notebooks, materials, chat history, API logs). In production, this should be a soft-delete pattern with `deletedAt` timestamp.

### 6.8 Notebook Deletion Doesn't Clean Up Chat Data

**File:** `backend/app/services/notebook_service.py` → `delete_notebook()`

Deletes materials and generated content but **does not delete** `ChatSession`, `ChatMessage`, or `ResponseBlock` records for the notebook — leaving orphaned chat data.

### 6.9 No Transaction Isolation on Cascading Deletes

Material deletion involves: ChromaDB cleanup → file deletion → DB record deletion. If any step fails midway, data is left in an inconsistent state. No database transaction wraps the operation.

---

## 7. Code Architecture Problems

### 7.1 God Files / Monoliths

| File | Lines | Problem |
|------|-------|---------|
| `frontend/src/components/chat/ChatPanel.jsx` | 1,212 | Handles input, streaming, slash commands, research mode, sessions, agent thinking, code review, mind map bridge, suggestions — all in one component with 30+ state variables |
| `frontend/src/components/studio/StudioPanel.jsx` | 907 | Manages flashcards, quiz, PPT, explainer, mindmap, podcast, and content history in one component |
| `backend/app/services/agent/tools_registry.py` | 1,070 | All agent tool implementations in one file (RAG, code exec, quiz, flashcard, PPT, podcast, data analysis) |
| `backend/app/services/rag/secure_retriever.py` | 896 | Retrieval + MMR + reranking + balancing + cross-doc detection all in one file |
| `backend/app/services/material_service.py` | 849 | File processing + URL processing + text processing + CRUD + cleanup |
| `backend/app/routes/upload.py` | 680 | Upload endpoints + material CRUD endpoints mixed together |
| `backend/app/services/chat/service.py` | 621 | RAG generation + citation validation + block splitting + DB persistence + sessions + followup + suggestions |
| `frontend/src/app/page.jsx` | 489 | Dashboard page mixed with notebook grid rendering logic |
| `frontend/src/components/layout/Sidebar.jsx` | 501 | Upload, web search, resize, WS updates, material management |

### 7.2 `useAppStore` Is a Catch-All

**File:** `frontend/src/stores/useAppStore.js` (164 lines)

Mixes unrelated state domains: notebooks, materials, sources, chat messages, generated content, UI flags. Any state change triggers re-renders in **all** consuming components. Should be split into:
- `useChatStore` — messages, sessions
- `useMaterialStore` — materials, sources
- `useNotebookStore` — notebook CRUD
- `useUIStore` — loading states, panels

### 7.3 Inconsistent Prisma Client Access

Some files use the module-level singleton:
```python
from app.db.prisma_client import prisma  # direct singleton
```
Other files use the getter function:
```python
from app.db.prisma_client import get_prisma  # factory function
prisma = get_prisma()
```
This makes it unclear which pattern is canonical and could cause issues if `get_prisma()` ever adds lazy initialization logic.

### 7.4 Excessive Lazy Imports

Backend routes have pervasive lazy imports inside function bodies:
```python
async def endpoint():
    from app.services.agent import AgentState  # lazy
    from app.db.prisma_client import prisma    # lazy
```

While this avoids circular imports, it:
- Hides dependencies (imports not visible at module top)
- Adds per-request import overhead (Python caches, but still)
- Indicates a circular dependency problem that should be architecturally fixed

### 7.5 No Router Prefixes

Most route files create `APIRouter()` without prefix:
```python
router = APIRouter()  # no prefix="/chat" etc.
```
Prefixes are applied only in `main.py` via `app.include_router(router, prefix="/chat")`. This means:
- Route files don't self-document their URL prefix
- Easy to accidentally create path collisions

---

## 8. Frontend-Specific Issues

### 8.1 Duplicate API_BASE Declarations

| File | How It Gets Base URL |
|------|---------------------|
| `lib/api/config.js` | `apiConfig.baseUrl` (canonical) |
| `lib/api/podcast.js` | `const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL \|\| 'http://localhost:8000'` |
| `lib/api/agent.js` | `const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL \|\| 'http://localhost:8000'` |
| `components/viewer/FileViewerContent.jsx` | `const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL \|\| 'http://localhost:8000'` |

Three files duplicate the base URL logic instead of importing from `config.js`.

### 8.2 Auth API Bypasses `apiFetch`

**File:** `frontend/src/lib/api/auth.js`

Login, signup, logout, and refresh use raw `fetch()` instead of the centralized `apiFetch` wrapper. This means auth API calls miss:
- Automatic retry logic
- Consistent error handling
- Request/response interceptors

### 8.3 Non-Serializable Values in Zustand State

| Store | Value | Issue |
|-------|-------|-------|
| `useAppStore` | `selectedSources: new Set()` | `Set` is not JSON-serializable; breaks devtools and persistence |
| `usePodcastStore` | `_audioEl: new Audio()` | DOM element in state; prevents SSR hydration |
| `usePodcastStore` | `_audioCache: new Map()` | `Map` is not serializable |
| `useConfirmStore` | `state.resolve` (Promise resolve function) | Function in state |

### 8.4 No Request Cancellation

Most API functions lack `AbortSignal` support. If a user navigates away mid-request, the request continues in the background. Only `streamChat`, `generateMindMap`, and a few generation functions accept signals.

### 8.5 No Virtualization for Long Lists

Chat messages, notebook cards, and material lists render **all items** with no virtualization. Long chat histories will cause significant lag.

### 8.6 Missing `React.memo` on List Items

No list item components (`ChatMessage`, `SourceItem`, notebook cards) use `React.memo()`. Parent re-renders trigger re-renders of every list item.

### 8.7 Index-Based React Keys

11+ files use array index as key (`key={index}`), which causes incorrect rendering when lists reorder, filter, or items are inserted/removed.

### 8.8 Missing Accessibility

- Icon-only buttons missing `aria-label` (widespread)
- No skip-to-main-content link
- Color-only status indicators (no text/icon for screen readers)
- No keyboard navigation with roving tabindex for menus
- Focus trap only in Modal component

### 8.9 No `metadata` Exports in Sub-Pages

Only the root `layout.jsx` has metadata. Auth page and notebook page have no title/description — bad for SEO and tab identification.

### 8.10 Memory Leak Risks

- **Blob URLs:** `usePodcastStore._audioCache` stores blob URLs and only revokes them in `resetPodcast()`. Navigation without reset leaks memory.
- **WebSocket reconnection:** Timer stacking if user rapidly navigates between notebooks.
- **Audio element:** Created at module load time, persists forever.

---

## 9. Inconsistencies & Code Smells

### 9.1 Backend Inconsistencies

| Pattern | Used In | Alternative Used In |
|---------|---------|-------------------|
| `from app.db.prisma_client import prisma` | explainer, health, chat | — |
| `from app.db.prisma_client import get_prisma` (then call) | mindmap, podcast, WS | — |
| f-string logging `f"msg {var}"` | auth, chat, proxy, search, upload | % formatting (nowhere consistently) |
| Module-level `import time` | Most files | Inside function body: `mindmap.py` |
| `safe_path()` for path security | ppt.py ✓ | Missing in podcast_live.py ✗ |
| Router prefix in `APIRouter()` | None | All applied in `main.py` only |
| Response models on endpoints | models.py, search.py ✓ | flashcard, quiz, mindmap, chat ✗ |

### 9.2 Frontend Inconsistencies

| Pattern | Where | Alternative |
|---------|-------|-------------|
| `apiConfig.baseUrl` | Most API files | Raw `API_BASE` in podcast.js, agent.js |
| Error display via `toast.error()` | Some components | Local `error` state in others |
| `useTheme()` from next-themes | Some components | Direct CSS variable reads in others |
| `useResizablePanel` hook | Exists in hooks/ | Sidebar reimplements resize manually |
| Named exports | Most files | `export default {}` object in ConfigDialogs.jsx |

### 9.3 Private Attribute Access

| Location | Access | Issue |
|----------|--------|-------|
| `routes/models.py` | `model_manager._is_model_cached(name)` | Breaks encapsulation |
| `routes/websocket_router.py` | `ws_manager._user_connections.setdefault(...)` | Direct internal state manipulation |

### 9.4 `token_data` Type Confusion

**File:** `backend/app/routes/agent.py` (download endpoint)

The handler defensively handles `token_data` as potentially a string, an object with `.user_id`, or a dict — indicating unclear contract for `require_file_token`'s return type.

### 9.5 Inconsistent Placeholder Syntax in Prompts

- Most prompts: `{{DOUBLE_BRACES}}`
- `mindmap_prompt.txt`: `{single_braces}`
- `podcast_script_prompt.txt`: `{python_format_style}`

Three different placeholder conventions across 12 prompt files.

---

## 10. Prompt System Issues

### 10.1 No Prompt Injection Protection

User-supplied strings (uploaded material text, chat messages, topic names) are injected directly into prompts via string replacement. If material content contains `{{CONTENT_TEXT}}` literally, it could cause unexpected substitutions.

### 10.2 JSON Output Parsing Fragility

Quiz, flashcard, and mindmap prompts demand raw JSON output from LLMs. LLMs frequently wrap output in markdown fences (`` ```json ... ``` ``) despite instructions. The `structured_invoker.py` has a 5-level repair pipeline to handle this — which is excellent — but the prompt instructions could be improved to reduce repair frequency.

### 10.3 No Prompt Versioning

No mechanism to track which prompt version generated which content. When prompts change, there's no way to correlate output quality changes with specific prompt revisions.

---

## 11. Dependency & Config Issues

### 11.1 Heavyweight Dependencies

| Package | Size Impact | Current Use | Recommendation |
|---------|------------|-------------|----------------|
| `@chakra-ui/react` + `@emotion/react` | ~100KB gzipped | Zero components used | **Remove entirely** |
| `framer-motion` | ~30KB gzipped | Only loaded by Chakra internally | **Remove with Chakra** |
| `selenium` + `webdriver-manager` | Heavy | Unclear if used (playwright also present) | Audit usage; likely remove |
| `SQLAlchemy[asyncio]` + `asyncpg` | Moderate | Not referenced in any service code | **Dead dependency** — Prisma is used exclusively |
| `redis` | Small | No Redis usage in code | **Dead dependency** |
| `easyocr` | ~200MB+ (with models) | OCR service | Verify if both `pytesseract` AND `easyocr` are needed |
| `TTS` | Very heavy (Coqui TTS) | Unclear if used alongside `edge-tts` | Audit usage |

### 11.2 Pinning Issues

- `torch` is installed from CUDA 12.1 index but no `torch` version pin — could break on updates.
- `chromadb >=0.5.11,<0.6.0` — good range pin.
- `react: ^19.2.3` — caret range on a bleeding-edge major version; could pull breaking pre-release.

### 11.3 Config Smells

- `ACCESS_TOKEN_EXPIRE_MINUTES=15` — very short; causes frequent refresh cycles.
- `MAX_UPLOAD_SIZE_MB=25` but `limit_request_body` middleware allows 100MB — inconsistent limits.
- `CODE_EXECUTION_TIMEOUT=15` seconds — may be too short for data analysis scripts.
- No `CORS_ORIGINS` configuration for production — defaults to `localhost:5173,localhost:3000`.

### 11.4 Hardcoded Token Limits

**File:** `backend/app/services/token_counter.py`

`TOKEN_LIMITS` dictionary hardcodes model-to-token-limit mappings. New models require code changes. Should come from config or the model registry.

---

## 12. Performance Issues

### 12.1 Backend

| Issue | Location | Impact |
|-------|----------|--------|
| Two embedding models loaded simultaneously | RAG pipeline + ChromaDB | ~1.5GB extra memory |
| Sequential material text loading | `routes/utils.py:require_materials_text` | N sequential disk reads instead of parallel |
| Monthly usage summed in Python | `token_counter.py:get_user_monthly_usage` | Unnecessary data transfer from DB |
| Sync ChromaDB calls in async context | `cli/reindex.py:_delete_material_chunks` | Blocks the event loop |
| No bulk ChromaDB delete on notebook deletion | `notebook_service.py:delete_notebook` | N thread pool calls instead of 1 |
| Full model load for verification at startup | `model_manager.py` | OOM risk on low-memory machines |
| `settings` imported inside middleware per-request | `performance_logger.py` | Minor per-request overhead |
| No pagination on `get_user_api_usage` beyond limit | `audit_logger.py` | Default OK but no cursor-based paging |

### 12.2 Frontend

| Issue | Location | Impact |
|-------|----------|--------|
| Chakra UI loaded but unused | `providers.jsx` | +100KB bundle |
| 2,529-line monolithic CSS | `globals.css` | No tree-shaking possible |
| No `React.memo` on list items | Chat, materials, notebooks | Cascading re-renders |
| `Set` in Zustand state | `useAppStore.selectedSources` | New reference on every read |
| No virtualization | ChatPanel, notebook cards | Lag on long lists |
| `useSearchParams()` in ChatPanel | `ChatPanel.jsx` | Re-render on any URL change |
| Blob URL leaks | `usePodcastStore._audioCache` | Memory accumulation |

---

## 13. What Works Well

Not everything is problematic. These patterns are well-implemented:

### Backend Strengths
- **Structured LLM invoker** (`structured_invoker.py`) — 5-level JSON repair pipeline with delta correction is excellent
- **Job queue** with `SKIP LOCKED` — proper concurrent job processing with stuck job recovery
- **File storage architecture** — full text on disk, summary in DB, UUID-based filenames
- **SSRF protection** — comprehensive private IP/DNS checking on proxy and URL upload
- **Auth token rotation** — family-based refresh token rotation with replay attack detection
- **Sandbox code execution** — AST-based validation, blocklists, subprocess isolation
- **Graceful worker shutdown** — proper signal handling with in-flight job completion

### Frontend Strengths
- **Token refresh deduplication** — `_refreshPromise` prevents concurrent refresh calls
- **SSE stream parser** — clean, handles partial buffers correctly
- **Lazy loading** — heavy components (`MindMapCanvas`, `PodcastStudio`) use `dynamic()` with `ssr: false`
- **Design system** — comprehensive CSS custom properties with light/dark theme support
- **Auth middleware** — clean Next.js Edge middleware for route protection
- **Confirm dialog as promise** — `useConfirmStore.show()` returns a Promise for clean async flow
- **Exponential backoff** — WebSocket reconnection with proper backoff

### Architecture Strengths
- **Multi-provider LLM support** — clean factory pattern for Ollama/Google/NVIDIA/Custom
- **Tenant-isolated RAG** — ChromaDB queries scoped to user_id, preventing cross-tenant data access
- **Background job pipeline** — clean separation of upload → queue → process → notify
- **CLI tooling** — well-documented backup, export, import, reindex tools

---

## Summary by Priority

### Fix Now (Before Any Production Deployment)
1. Add missing prompt template files (will crash at runtime)
2. Fix GPU manager dual-lock concurrency bug
3. Add path traversal protection to podcast audio/export routes
4. Sanitize HTML in PresentationView before `dangerouslySetInnerHTML`
5. Add rate limiting on auth endpoints (use Redis)
6. Restrict `delete_uploaded_file()` to upload directory
7. Add even basic tests

### Fix Soon (High Impact)
8. Remove Chakra UI (save ~100KB bundle)
9. Split god components (ChatPanel, StudioPanel, tools_registry)
10. Split `useAppStore` into focused stores
11. Add missing DB indexes on ChatMessage and GeneratedContent
12. Add FK relations on 4 orphaned `notebookId` fields
13. Fix async PPT to support multiple materials
14. Move to Redis-backed rate limiter and WS manager
15. Remove dead dependencies (SQLAlchemy, redis, selenium)
16. Clean up dead code (tts_provider/, yt_translation/, unused imports)

### Fix Later (Tech Debt)
17. Unify embedding models
18. Add TypeScript to frontend
19. Enable `reactStrictMode: true`
20. Add prompt versioning
21. Implement database migration strategy
22. Implement soft-delete on users
23. Add job cleanup/TTL
24. Implement proper transaction isolation on cascading deletes
25. Parallelize `require_materials_text()`
26. Fix inconsistent patterns (Prisma access, API_BASE, placeholders)
