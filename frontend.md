# KeplerLab Frontend - Complete Architecture and End-to-End Flow

## 1. Scope of This Document

This document maps the frontend implementation under `frontend/` with emphasis on:
- Next.js app architecture and runtime boot flow
- Route-level behavior
- State management and data flow
- API client contracts and backend integration
- Streaming, WebSocket, and feature execution flows
- Notebook workspace behavior from source ingestion to generated outputs

Primary roots:
- `frontend/src/app/**`
- `frontend/src/components/**`
- `frontend/src/stores/**`
- `frontend/src/hooks/**`
- `frontend/src/lib/api/**`
- `frontend/src/lib/stream/streamClient.js`
- `frontend/src/middleware.js`
- `frontend/next.config.mjs`
- `frontend/package.json`

## 2. Technology Stack

- Framework: Next.js App Router (v16)
- Runtime UI: React 19
- Global state: Zustand
- Styling: Tailwind + CSS variables + custom styles
- Theme handling: `next-themes`
- Icons: `lucide-react`
- Markdown/render helpers: `react-markdown`, `remark`, `rehype`, `katex`
- Presentations/diagrams/document tooling: `jspdf`, `@xyflow/react`, doc viewer libraries

## 3. App Boot and Navigation Architecture

## 3.1 Root Layout and Providers

Files:
- `src/app/layout.jsx`
- `src/app/providers.jsx`

Boot sequence:
1. Global fonts and CSS are loaded.
2. `ThemeProvider` initializes light/dark preference.
3. `AuthInitializer` calls `useAuthStore.initAuth()` on mount.
4. Shared UI overlays are mounted globally:
   - `ToastContainer`
   - `ConfirmDialog`

## 3.2 Middleware-Based Access Control

File: `src/middleware.js`

Behavior:
- Public prefixes bypass auth check: `/auth`, `/view`, `/api`
- Static asset paths bypass auth check
- For protected routes, if `refresh_token` cookie missing:
  - redirect to `/auth`
  - attach `redirect` query for non-root paths

This means unauthenticated users are pushed to auth before notebook workspace access.

## 3.3 App Routes

Observed pages:
- `/` -> notebook list/home (`src/app/page.jsx`)
- `/auth` -> sign-in/sign-up (`src/app/auth/page.jsx`)
- `/notebook/[id]` -> workspace (`src/app/notebook/[id]/page.jsx`)
- `/view` -> file viewer route (`src/app/view/page.jsx`)

Error/loading surfaces:
- `src/app/loading.jsx`
- `src/app/error.jsx`
- `src/app/global-error.jsx`
- `src/app/not-found.jsx`

## 4. API Integration Layer

## 4.1 Base Client and Token Lifecycle

File: `src/lib/api/config.js`

Core responsibilities:
- Stores in-memory access token (`_accessToken`)
- Central `apiFetch`, `apiFetchFormData`, `apiJson`
- Always sends cookies (`credentials: include`)
- Auto-refresh on 401 with single-flight dedupe (`_refreshPromise`)
- Retries failed request once after refresh
- Session-expiry callback support (`onSessionExpired`)

Failure behavior:
- If refresh fails, token cleared and app redirects to `/auth?reason=expired` (or custom callback path)

## 4.2 Next.js Rewrite Proxying

File: `next.config.mjs`

Development rewrites:
- `/api/:path*` -> `${NEXT_PUBLIC_API_BASE_URL}/:path*`
- `/api/presentation/slides/:path*` -> backend slide path

Frontend also calls backend directly using configured base URL in API client.

## 4.3 API Module Inventory

- `api/auth.js`
- `api/notebooks.js`
- `api/materials.js`
- `api/chat.js`
- `api/generation.js`
- `api/explainer.js`
- `api/podcast.js`
- `api/agent.js` (artifact URL helpers)

## 5. State Management Architecture (Zustand)

## 5.1 Auth Store (`useAuthStore.js`)

State:
- `user`, `isLoading`, `isAuthenticated`, `error`

Actions:
- `initAuth`:
  - tries refresh token
  - fetches `/auth/me`
  - schedules periodic refresh
- `login`, `signup`, `logout`
- session-expiry handling integrated with API config callback

Refresh strategy:
- timer every 13 minutes (`TIMERS.TOKEN_REFRESH_INTERVAL`)
- retries refresh with exponential backoff

## 5.2 App Workspace Store (`useAppStore.js`)

Combines cross-panel workspace data:
- current notebook and draft mode
- materials and source selections
- chat session/messages mirror state
- generated outputs and notes
- loading/error flags

Important reset actions:
- `resetForNotebookSwitch`: clears notebook-scoped runtime state
- `resetWorkspace`: full workspace clear

## 5.3 Specialized Stores

- `useChatStore`: chat message/session/stream/error state
- `useMaterialStore`: material list + source selection controls
- `useNotebookStore`: lightweight current notebook info
- `usePodcastStore`: podcast session, phase, websocket updates
- `useToastStore`, `useConfirmStore`, `useUIStore`: global UI utilities

## 6. Notebook Workspace Composition

File: `src/app/notebook/[id]/page.jsx`

Panel layout:
- Header (top)
- Sidebar (left, sources)
- Chat panel (center)
- Studio panel (right)

Page flow:
1. Resolve notebook id from route.
2. Handle draft mode and newly-created notebook transitions.
3. Fetch notebook details if needed.
4. Set `currentNotebook` in store and clear prior notebook state when switching.
5. Render dynamic panels with panel-specific error boundaries.

## 7. Sidebar Flow (Sources and Ingestion)

File: `src/components/layout/Sidebar.jsx`

Responsibilities:
- list and manage materials for current notebook
- upload files / web sources / text sources
- search web and import selected results
- open material preview text modal
- track source selection and statuses

Key flows:

### 7.1 Material Load
1. On notebook change, call `getMaterials(notebookId)`.
2. Normalize and set list in store.
3. Auto-select completed sources if configured.

### 7.2 Upload Files
1. Open `UploadDialog`.
2. Call `uploadBatch` or `uploadBatchWithAutoNotebook` for draft notebooks.
3. Add pending material rows immediately.
4. Receive async status updates via websocket and refresh list.

### 7.3 Web Search Import
1. User enters query + optional filetype.
2. Calls `/search/web` via `webSearch()`.
3. User selects results in `WebSearchDialog`.
4. Each selected URL sent through `uploadUrl()`.

### 7.4 Live Material Status Updates
Hook: `useMaterialUpdates.js`
- opens websocket `/ws/jobs/{userId}`
- authenticates with access token
- handles ping/pong
- reconnects with exponential backoff
- forwards `material_update`, `notebook_update`, and podcast-related events

## 8. Chat System Frontend Flow

## 8.1 Chat Panel Composition

File: `src/components/chat/ChatPanel.jsx`

Responsibilities:
- manage current chat session in URL query (`session`)
- load session list and history
- create/delete/select chat sessions
- render messages, empty state, input, selection menu
- start new notebook automatically from draft when first chat is sent

## 8.2 Chat Hook (`useChat.js`)

Core flow for `sendMessage`:
1. Ensure not already streaming.
2. Ensure chat session exists (create if needed).
3. Append local optimistic user message.
4. Append placeholder assistant message.
5. Call `streamChat(...)` to backend `/chat`.
6. Parse streamed SSE events through `streamSSE`.
7. Update assistant message progressively by event type.

Handled event categories include:
- token stream
- done/error
- blocks/meta
- code blocks
- artifact attachments
- web search updates/sources
- research phase/source/citations
- agent status/plan/step/tool/result/reflection/done

Also supports:
- abort current stream
- retry previous user message
- load history and reconstruct partial agent state from metadata
- delete/edit messages (edit triggers re-send)

## 8.3 SSE Parser

File: `src/lib/stream/streamClient.js`

Behavior:
- Reads `ReadableStream` chunks
- Parses `event:` and `data:` lines
- Falls back to `data.type` when event name is generic
- Dispatches to per-event handlers
- Supports abort signal cancellation

## 9. Studio Panel Flow (Generated Learning Artifacts)

File: `src/components/studio/StudioPanel.jsx`

Functional groups:
- Flashcards
- Quiz
- Presentation
- Explainer
- Podcast
- History of generated outputs

## 9.1 Shared generation pattern

For flashcards/quiz/presentation:
1. Ensure source selection exists.
2. Open config dialog.
3. Submit API request with selected material ids.
4. Show loading state and allow cancellation via AbortController.
5. Persist generated output to notebook content via `saveGeneratedContent`.
6. Add to local `contentHistory`.

## 9.2 History Management

`contentHistory` supports:
- open previous item
- rename (calls notebook content update)
- delete (calls notebook content delete or podcast session delete)
- copy/export

## 9.3 Explainer Flow

Using `api/explainer.js`:
1. Check reusable presentations for selected materials.
2. Trigger generation with language and voice options.
3. Poll status endpoint.
4. Retrieve final video blob/url.

## 9.4 Podcast Flow

Using `api/podcast.js` + `usePodcastStore`:
- create/list/update/delete podcast sessions
- start generation
- fetch segment/session audio
- submit questions and retrieve doubts
- bookmarks and annotations
- trigger/export retrieval
- summary generation
- voices/languages discovery

WebSocket integration:
- Sidebar forwards podcast websocket messages into `usePodcastStore.handleWsEvent`.

## 10. Auth and Home Experience

## 10.1 Auth Page

File: `src/app/auth/page.jsx`

Features:
- split layout marketing + form
- login/signup mode switch
- submit to auth store actions
- redirect logic based on auth state and query params

## 10.2 Home Page

File: `src/app/page.jsx`

Responsibilities:
- require authentication
- list notebooks (`getNotebooks`)
- create/rename/delete notebooks
- theme toggle
- user menu/logout
- respond to notebook name update events emitted from workspace websocket updates

## 11. File Viewer Path

Route: `/view` (`src/app/view/page.jsx`)

Loads `FileViewerContent` dynamically and supports backend proxy/file-viewer endpoints for document rendering workflows.

## 12. Cross-Cutting UX and Infrastructure Patterns

- Dynamic imports to reduce heavy initial bundle for workspace panels
- Resizable panels with min/max bounds (`useResizablePanel`, constants)
- Global toasts and confirm dialogs for user feedback
- Per-panel error boundaries (`PanelErrorBoundary`)
- Keyboard and modal accessibility patterns
- Optimistic UI for many actions with backend reconciliation

## 13. End-to-End User Journeys

## 13.1 Journey A: New User -> Notebook -> Upload -> Chat

1. User lands on `/auth` and logs in.
2. Auth store gets access token and schedules refresh.
3. User navigates to `/` and creates/selects notebook.
4. In notebook workspace, Sidebar uploads material.
5. Backend enqueues job; websocket pushes processing/completed statuses.
6. User selects completed source and sends chat question.
7. Chat panel streams assistant response via SSE.
8. History/session state is persisted and restorable.

## 13.2 Journey B: Generate Learning Assets

1. User selects one or more sources.
2. In Studio, choose flashcards/quiz/presentation.
3. Backend generates and returns structured output.
4. Frontend saves result into notebook content history.
5. User revisits, renames, deletes, or exports later.

## 13.3 Journey C: Agent/Research/Code in Chat

1. User sends slash-command-style or intent-routed query.
2. SSE includes rich event stream (plan/steps/tool output/artifacts).
3. Message renderer updates progress UI incrementally.
4. Artifacts become downloadable/viewable in chat cards.

## 14. Backend Endpoint Usage Map by Frontend Module

Auth:
- `/auth/login`, `/auth/signup`, `/auth/me`, `/auth/refresh`, `/auth/logout`

Notebook/content:
- `/notebooks`, `/notebooks/{id}`, `/notebooks/{id}/content...`

Materials/upload/search:
- `/upload`, `/upload/batch`, `/upload/url`, `/upload/text`, `/upload/supported-formats`
- `/materials...`
- `/search/web`

Chat/code:
- `/chat`, `/chat/history/...`, `/chat/sessions...`, `/chat/message/...`
- `/chat/block-followup`, `/chat/suggestions`, `/chat/empty-suggestions`, `/chat/optimize-prompts`
- `/code-execution/execute-code`

Generation:
- `/flashcard`, `/quiz`, `/presentation/async`, `/jobs/{id}`
- `/explainer/*`
- `/podcast/*`

Realtime:
- websocket `/ws/jobs/{user_id}`

Artifacts/viewers:
- `/artifacts/{id}`
- file-viewer/proxy paths under `/api/v1/*`

## 15. Frontend Component Domain Inventory

Major component domains under `src/components/`:
- `chat/` (message rendering, artifacts, progress strips, input/history)
- `layout/` (header/sidebar)
- `studio/` (content generation and history)
- `podcast/` (player/studio/config/transcript/export)
- `presentation/` (slides and config)
- `viewer/` (doc/file viewer)
- `ui/` (modal, toasts, confirmation, error boundaries)
- `notebook/` (source item, upload/search dialogs)

## 16. Reliability and Session Semantics

- Token refresh is centralized and deduplicated to avoid concurrent refresh races.
- Session-expiry callback enforces consistent logout behavior.
- WebSocket reconnect uses exponential backoff.
- Chat stream abort path prevents stale in-flight writes.
- Notebook switch reset avoids cross-notebook state bleed.

## 17. Practical Mental Model

The frontend is a notebook-centric workspace shell with three synchronized control planes:
- Sources plane (Sidebar): ingestion + readiness state
- Conversation plane (Chat): SSE-driven intelligent interactions
- Generation plane (Studio): asynchronous asset creation and lifecycle

All three share notebook context via Zustand stores and converge on backend APIs that persist state into notebook/material/session entities.

This captures end-to-end frontend architecture and all major feature flows present in this workspace.
