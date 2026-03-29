# KeplerLab Frontend Documentation

## 1) Frontend At A Glance

KeplerLab frontend is a Next.js App Router application that provides:
- Authenticated notebook workspace UI
- Source ingestion and web search import workflows
- Streaming AI chat with slash-command capabilities
- Studio generation actions (flashcards, quiz, mindmap, code execution, AI resources)
- Podcast session controls
- Material/file viewing via secured backend proxy

Primary root:
- `frontend/src/app/`
- `frontend/src/components/`
- `frontend/src/stores/`
- `frontend/src/hooks/`
- `frontend/src/lib/api/`
- `frontend/src/lib/stream/`

## 2) Runtime Stack

Core:
- Next.js 16 App Router
- React 19
- Zustand for client state
- Tailwind CSS + custom CSS variables/theme tokens
- axios for HTTP wrappers
- EventSource for streaming chat
- native WebSocket for material/podcast updates

Security/runtime behavior:
- Frontend relies on backend auth token + refresh cookie model
- Middleware redirects unauthenticated users to auth page
- Next rewrites route `/api/:path*` to backend `/api/v1/:path*`

## 3) Route Structure

Main pages under `src/app`:
- `/` -> landing or dashboard based on auth
- `/auth` -> login/signup
- `/notebook/[id]` -> main workspace
- `/view?url=...` -> file/document viewer experience

Supporting files:
- `src/app/layout.jsx` global app shell
- `src/app/providers.jsx` theme/toast providers
- `src/middleware.js` route guard and auth redirects

Notebook route composition:
- `src/app/notebook/[id]/layout.jsx` loads shared notebook context
- `src/app/notebook/[id]/page.jsx` renders interactive workspace layout

## 4) Global Architecture Pattern

The frontend follows a layered client pattern:
1. API modules (`lib/api`) define backend calls
2. Zustand stores (`stores`) hold normalized session/UI data
3. Hooks (`hooks/useChat.js`, etc.) orchestrate flows
4. Components consume store state and dispatch actions
5. Realtime pipelines (SSE + WS) update stores incrementally

This pattern avoids deeply nested prop chains and keeps route pages thin.

## 5) State Management (Zustand Stores)

### `useAuthStore`
Responsibilities:
- User identity, login state, auth bootstrap
- Calls auth API endpoints and handles token lifecycle
- Exposes `checkAuth`, `login`, `signup`, `logout`

### `useAppStore`
Responsibilities:
- Notebook-scoped app state (current notebook, UI flags)
- Source panel dialogs, selected source references
- Shared UI toggles across notebook workspace

### `useChatStore`
Responsibilities:
- Chat sessions, active session, message list
- Streaming flags and partial assistant state
- Source selection association with notebook
- Follow-up prompts and response block metadata

### `useMaterialStore`
Responsibilities:
- Material list, statuses, selection
- Upload job progress and polling/refresh triggers
- Source management actions

### `usePodcastStore`
Responsibilities:
- Podcast session metadata and segment progress
- Playback-related state and actions
- Doubts, bookmarks, annotations data sync

### `useSkillStore`
Responsibilities:
- Skill definitions and run histories
- Skill execution streaming state

## 6) API Client Layer (`src/lib/api`)

Representative modules:
- `authApi.js`
- `notebookApi.js`
- `chatApi.js`
- `materialApi.js`
- `podcastApi.js`
- `skillsApi.js`
- `codeExecutionApi.js`
- `searchApi.js`
- `modelApi.js`

Shared behavior:
- Consistent base URL and headers
- Refresh-retry strategy on auth expiration paths
- Typed/normalized response handling where needed

Notable integration:
- Frontend references backend `/api/v1` endpoints directly
- Also supports Next rewrite through `/api/*` for proxy-style calls

## 7) Notebook Workspace UI Composition

Primary workspace components:
- `components/layout/Sidebar.jsx`
- `components/chat/ChatPanel.jsx`
- `components/studio/StudioPanel.jsx`
- `components/notebook/UploadDialog.jsx`
- `components/notebook/WebSearchDialog.jsx`
- `components/viewer/FileViewerContent.jsx`

Layout behavior in notebook page:
- Sidebar for sources and navigation
- Main center panel for chat and generated outputs
- Studio panel for generation/automation tasks

## 8) Authentication And Navigation Flow

`middleware.js` enforces route access:
- Auth routes are accessible without active session
- Protected routes redirect to `/auth` if token/session missing
- Logged-in users are redirected away from `/auth` to app pages

Auth page flow (`src/app/auth/page.jsx`):
1. User chooses login/signup mode
2. Submits credentials to auth API
3. Stores user + token state
4. Redirects to dashboard/root

## 9) Chat UI And Streaming Flow

Key components:
- `ChatPanel.jsx`
- `ChatInput.jsx`
- `MessageList.jsx`
- hook: `useChat.js`
- stream parser: `lib/stream/streamClient.js`

Detailed flow:
1. User submits prompt (optionally slash command).
2. `useChat` builds payload including:
   - notebook ID
   - session ID (existing or create)
   - selected materials/source IDs
   - requested capabilities/intents
3. Request sent to backend `/chat` endpoint expecting SSE.
4. Stream parser consumes event lines and emits typed events.
5. UI updates incrementally by event type:
   - `token` appends assistant text
   - `tool_start` shows active tool status
   - `web_search_update` updates search progress rows
   - `web_sources` attaches citations/source list
   - `artifact` appends downloadable outputs
   - `done` finalizes message state
6. Completed message persisted in chat store and linked to session.

Slash command intent routing (frontend side):
- Prefixes like `/web`, `/research`, `/agent`, `/python` (as supported in UI) set intent hints in outbound payload.
- Backend may override based on material selection rules.

## 10) Search Feature Flow In Frontend

Search appears in two major surfaces:
1. Source discovery dialog (`WebSearchDialog`) to add links as notebook sources
2. Chat slash-mode web and research requests

### 10.1 Source Discovery Flow (Dialog)

Detailed sequence:
1. User opens `WebSearchDialog` from source controls.
2. Enters search query and optional file-type filter.
3. `searchApi` posts to `/search/web`.
4. UI renders normalized result cards (`title`, `link`, `snippet`).
5. User selects one or many results.
6. For each selected URL, frontend submits `/upload/url` payload.
7. Material rows appear in source list as `pending/processing`.
8. WebSocket updates transition statuses until `completed`.
9. User can select these new materials for RAG chat.

### 10.2 Chat Web Search Flow

Detailed sequence:
1. User enters `/web ...` prompt in chat input.
2. Chat payload sets web-search intent.
3. SSE events provide live search progress and sources.
4. UI displays progress timeline and then final synthesized response.

### 10.3 Chat Deep Research Flow

Detailed sequence:
1. User enters `/research ...` prompt.
2. SSE streams research phase events, source additions, report tokens.
3. If PDF artifact event arrives, UI renders download/open action.

## 11) Upload And Material Lifecycle In UI

Entry points:
- `UploadDialog` (file upload)
- `WebSearchDialog` (URL imports)
- text-based creation surfaces where available

Lifecycle visuals:
- Source item cards show processing states
- Failures are surfaced with retry/delete paths
- Completed items expose preview/open actions

`SourceItem.jsx` responsibilities:
- Render status badges
- Trigger selection toggle
- Open viewer for supported resources

## 12) Studio Panel Feature Flows

`StudioPanel.jsx` centralizes non-chat generation actions.

Typical actions:
- Flashcard generation
- Quiz generation
- Mindmap generation
- Code execution run path
- AI resource builder path

General workflow:
1. User selects source constraints/material context
2. User picks generation mode and parameters
3. Frontend calls feature endpoint
4. Result block is added to notebook generated content area
5. Optional rating/edit/update flows call notebook content endpoints

## 13) Viewer And Proxy Integration

Viewer route: `/view` with URL query parameter.

`FileViewerContent.jsx` flow:
1. Calls `/api/v1/file-viewer/info` for content classification.
2. If office document, uses backend-provided embed URL.
3. If pdf/text, uses `/api/v1/file-viewer/proxy` stream.
4. Handles unsupported/private/inaccessible target errors gracefully.

This ensures browser can preview remote content without direct unsafe cross-origin requests.

## 14) Real-Time Updates Beyond Chat

WebSocket channel:
- Connected using user-scoped path `/ws/jobs/{user_id}`
- Handles reconnect and keepalive behavior

Update types used in UI:
- `material_update`: progress states and completion
- `notebook_update`: notebook-level metadata refresh
- podcast related updates for generation/playback progress

Realtime design benefit:
- Upload and generation operations can run server-side while UI stays synchronized without polling-heavy loops.

## 15) Dashboard And Entry Experience

`Dashboard.jsx` and `LandingPage.jsx` separate authenticated and unauthenticated entry states:
- Unauthenticated users see marketing/onboarding style landing
- Authenticated users see notebook list and action controls

Notebook creation and navigation actions are wired into notebook APIs and app store updates.

## 16) Error Handling And UX Guardrails

Patterns used:
- Toast notifications for operation success/failure
- Loading placeholders in route-level `loading.jsx`
- `error.jsx` boundary pages for route failures
- Request-level catches with human-readable fallback messages

Chat-specific guardrails:
- Prevent duplicate sends while streaming
- Session fallback if no active chat session exists
- Incremental token rendering with resilient stream parser

## 17) Frontend To Backend Endpoint Mapping (Core)

High-frequency mappings:
- Auth UI -> `/auth/*`
- Notebook list/detail/content -> `/notebooks*`
- Chat streaming/history/session -> `/chat*`
- Source upload/manage -> `/upload*`, `/materials*`, `/jobs*`
- Search discovery -> `/search/web`
- Studio generate -> `/flashcard`, `/quiz`, `/mindmap`, `/code-execution/*`, `/ai-resource-builder`
- Podcast UI -> `/podcast/*`
- Skill UI -> `/skills*`
- Viewer -> `/api/v1/file-viewer/*` and `/api/v1/proxy`

## 18) End-To-End User Journey (Frontend Perspective)

Typical end-to-end usage:
1. User logs in via `/auth`.
2. Opens or creates notebook.
3. Adds materials via file upload, URL, or web search discovery.
4. Watches processing updates through WebSocket.
5. Selects sources and starts chat.
6. Uses slash commands for web/research/agent/code modes.
7. Receives streaming responses, artifacts, and citations.
8. Uses Studio panel for structured outputs (quiz/flashcards/mindmap/code/resources).
9. Stores and revisits generated outputs in notebook history.
10. Optionally creates podcast session and interacts with playback artifacts.

## 19) Implementation Notes

- The frontend is intentionally store-driven; avoid putting business logic directly in page components.
- SSE event contracts are central; adding new backend event types requires parser/store/UI updates.
- Source selection strongly influences backend routing behavior, so selection UX must remain clear.
- Viewer relies on backend safety checks; frontend should keep using backend proxy/info endpoints rather than direct fetch for remote docs.

## 20) Frontend Search Summary (One-Line)

Frontend search is a dual-path UX: one path imports discovered links as first-class notebook materials via `/search/web` plus `/upload/url`, and the second path drives live in-chat web/research capabilities through `/chat` SSE streaming.