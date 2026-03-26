# KeplerLab Frontend: Complete Architecture and Feature Flows

This document captures the frontend system in `/disk1/KeplerLab_Agentic/frontend` end-to-end: app structure, auth/session flow, API integration, state stores, streaming behavior, and feature-level user journeys.

## 1) Scope and Coverage

Documented from source-level inspection of:
- `frontend/src/app/**/*`
- `frontend/src/components/**/*`
- `frontend/src/hooks/**/*`
- `frontend/src/stores/**/*`
- `frontend/src/lib/**/*`
- `frontend/src/styles/**/*`
- top-level config (`package.json`, `next.config.mjs`, `tailwind.config.js`, `eslint.config.mjs`)

Notes:
- Frontend workspace includes large generated/dependency folders (for example `.next`, `node_modules`), which are not business logic.
- Focus here is runtime app code and behavior.

## 2) High-Level Frontend Architecture

### 2.1 Platform
- Framework: Next.js App Router
- UI engine: React client components
- State: Zustand stores
- Theme: `next-themes`
- Styling: Tailwind + custom CSS in `src/styles/globals.css`
- Network: custom API clients under `src/lib/api/*`
- Streaming: SSE parser `src/lib/stream/streamClient.js`

### 2.2 Core composition
- Route layer under `src/app`.
- Shared shell/components under `src/components`.
- Domain hooks under `src/hooks`.
- Centralized stores under `src/stores`.
- API abstraction and token handling under `src/lib/api`.

## 3) Routing and Access Control

### 3.1 Global middleware (`src/middleware.js`)
Behavior:
- Public routes: `/auth`, `/api`, static assets.
- Protected routes: everything else.
- If no auth token cookie, redirect protected requests to `/auth`.
- If token exists and path is `/auth`, redirect to `/`.

Auth cookie checked by middleware: `kepler_token`.

### 3.2 App routes (`src/app`)
Primary pages:
- `/` -> home dashboard with notebooks list and actions.
- `/auth` -> login/signup experience.
- `/notebook/[id]` -> main workspace (sidebar + chat + studio).
- `/view` -> file/document viewer mode.

Global wrappers:
- `layout.jsx`: app HTML shell.
- `providers.jsx`: theme provider and global app providers.

## 4) Authentication and Session Lifecycle

## 4.1 Auth store (`src/stores/useAuthStore.js`)
State:
- `token`
- `user`
- `isAuthenticated`
- loading/error states

Actions:
- `login`, `signup`, `logout`
- `refreshToken` with retry and schedule refresh before expiry
- bootstrap state from existing session

### 4.2 API auth client (`src/lib/api/auth.js`)
Endpoints used:
- `POST /auth/login`
- `POST /auth/signup`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /auth/me`

Token behavior:
- Access token stored in app state and sent as bearer.
- Refresh token stored as HttpOnly cookie; frontend triggers refresh call when needed.

### 4.3 API request wrapper (`src/lib/api/config.js`)
- Base URL from env (`NEXT_PUBLIC_API_URL` style config path).
- Injects bearer access token if present.
- On 401, attempts refresh and retries once.
- Normalizes errors for UI consumers.

## 5) Global State Architecture (Zustand)

Stores under `src/stores`:
- `useAppStore.js`: app-level UI state and notebook/workspace orchestration metadata.
- `useChatStore.js`: chat sessions/messages, streaming states, selected mode/capability metadata.
- `useMaterialStore.js`: notebook materials list, selected materials, upload/progress state.
- `usePodcastStore.js`: podcast session playback/generation state, doubts/bookmarks/annotations.
- `useMindMapStore.js`: mindmap content and rendering state.
- `useAuthStore.js`: auth/session state.

Store design pattern:
- Async actions call API modules.
- Local optimistic state updates for responsive UI.
- Error captured per feature for panel-level rendering.

## 6) API Integration Matrix

API clients in `src/lib/api`:
- `chat.js`: chat message streaming/history/session APIs.
- `materials.js`: list, upload, rename, delete, text retrieval.
- `notebooks.js`: notebook CRUD and generated-content operations.
- `generation.js`: flashcard/quiz and related generation calls.
- `mindmap.js`: mindmap generate/load.
- `presentation.js`: presentation generation/export/update.
- `podcast.js`: podcast session/generation/playback and side features.
- `explainer.js`: explainer generation and status/video retrieval.
- `agent.js`: agent-oriented APIs and stream handling support.

Consistency traits:
- Shared request helper, shared auth token path.
- Standardized error handling and response mapping.

## 7) Notebook Workspace Page Architecture

Main page: `src/app/notebook/[id]/page.jsx`

Primary layout components:
- `components/layout/Sidebar.jsx`
- `components/chat/ChatPanel.jsx`
- `components/studio/StudioPanel.jsx`

### 7.1 Sidebar responsibilities
- Notebook metadata display and actions.
- Materials list rendering with status indicators.
- Upload entrypoints:
  - file upload
  - URL upload
  - text upload
- Material selection controls used by chat/studio generation.
- Live update integration from websocket events for material processing progress.

### 7.2 Chat panel responsibilities
- Message composer and message list rendering.
- Trigger chat send via `useChat` hook.
- Stream rendering for incremental token updates.
- Display of structured events: sources, citations, tool progress, artifacts.
- Chat history and session switching/delete/edit controls.

### 7.3 Studio panel responsibilities
- Feature tabs/panels: flashcard, quiz, mindmap, presentation, podcast, explainer, other generated outputs.
- Opens config dialogs for generation parameters.
- Triggers feature-specific API calls.
- Saves and displays generated content history linked to notebook.

## 8) Chat Streaming and Event Handling

### 8.1 Hook (`src/hooks/useChat.js`)
Responsibilities:
- Encapsulate chat send and SSE stream lifecycle.
- Prepare payload with notebook/material/session/mode context.
- Subscribe to stream events and update `useChatStore` incrementally.
- Handle abort/cancel, error, completion transitions.

### 8.2 Stream parser (`src/lib/stream/streamClient.js`)
- Parses SSE event frames.
- Distinguishes event types (token chunks, metadata, source lists, tool/phase progress, completion/error).
- Sends normalized events to hooks/stores.

### 8.3 UI-visible event categories
- message chunk deltas
- intent/capability metadata
- source/citation updates
- code execution and artifact events
- research/agent phase messages
- final completion payload

## 9) Feature Flows (End-to-End)

## 9.1 Auth flow
1. User opens app.
2. Middleware checks token cookie.
3. If missing token and protected route, redirect to `/auth`.
4. Login/signup submits credentials to backend.
5. On success, auth store sets user/token and navigates to home.
6. Refresh scheduler keeps access token alive.

### 9.2 Notebook and materials
1. User creates/selects notebook from home.
2. Notebook page loads notebook details + material list.
3. User uploads file/url/text from sidebar.
4. Sidebar/store receive background progress updates.
5. On completion, material appears as selectable source.
6. Material text preview and metadata actions available.

### 9.3 Chat with capability routing
1. User enters prompt in chat panel.
2. `useChat` sends SSE request through chat API client.
3. Backend selects capability (normal/rag/agent/research/code/web).
4. Stream events update partial assistant message and progress UI.
5. Final response and metadata committed to store.
6. Session and message history remain available for revisit/edit/delete.

### 9.4 Flashcards and quiz
1. User opens studio tab for flashcard/quiz.
2. Selects source materials and optional topic settings.
3. Frontend calls generation API.
4. Result is rendered in studio and stored in generated-history list.

### 9.5 Mindmap
1. User triggers mindmap generation from selected materials.
2. API response parsed to graph-like data structure.
3. Mindmap store updates and visualization component renders nodes/edges.
4. Generated content entry appears in notebook history.

### 9.6 Presentation
1. User configures presentation options.
2. Frontend triggers generation endpoint.
3. Progress/result reflected in studio list.
4. User opens HTML view or downloads PPT/PDF via presentation endpoints.
5. Instruction-based edit flow can modify existing presentation.

### 9.7 Explainer
1. User opens explainer section.
2. Frontend checks existing presentation availability.
3. Sends generate request with language/voice options.
4. Polls status endpoint until completion.
5. Plays/downloads resulting video file.

### 9.8 Podcast
1. User creates podcast session with mode/language/voice settings.
2. Starts generation and receives progress updates.
3. Audio player consumes segment or full-audio endpoints.
4. User can submit doubt questions, add bookmarks, and annotations.
5. Exports and summaries retrieved from API.

### 9.9 Artifact and file viewing
1. Chat/agent/code flows may return artifact references.
2. UI renders artifact cards with links.
3. `/view` route + file-viewer components use proxy/info endpoints for safe rendering strategy.
4. Binary and textual assets handled with mode-aware viewer components.

## 10) Component-Level Structure Highlights

Representative UI components:
- Layout:
  - `components/layout/Sidebar.jsx`
- Chat:
  - `components/chat/ChatPanel.jsx`
  - message renderer, markdown/code rendering, source/citation blocks
- Studio:
  - `components/studio/StudioPanel.jsx`
  - `components/studio/ConfigDialogs.jsx`
- Podcast:
  - `components/podcast/PodcastStudio.jsx`
- Viewer:
  - file/document rendering components for artifact and source previews

Design behavior:
- Heavy use of dynamic imports where needed to avoid SSR/client mismatch for browser-only modules.
- Progressive rendering for stream-driven interactions.

## 11) Home Dashboard Flow (`src/app/page.jsx`)

Capabilities:
- Notebook listing and creation.
- Notebook rename/delete actions.
- Navigation into `/notebook/[id]` workspace.
- Recent/generated content surfacing depending on app store behavior.

## 12) File Viewer and Proxy Integration

Routes/components around `/view` coordinate with backend proxy APIs:
- Determine content type and viewer mode.
- For PDFs/text/web docs, load through backend file proxy to avoid CORS/direct SSRF issues.
- Render with dedicated viewer components.

## 13) Error Handling and UX Resilience

Patterns used:
- Centralized API error normalization.
- Store-level `loading` and `error` flags for each domain.
- Retry logic on auth expiration.
- Stream error handling in `useChat` with graceful message state transitions.

## 14) Frontend Configuration

Key files:
- `next.config.mjs`: app build/runtime config.
- `tailwind.config.js`: utility class scanning/theme setup.
- `eslint.config.mjs`: linting rules.
- `postcss.config.mjs`: CSS pipeline.
- `jsconfig.json`: path alias/resolution behavior.

## 15) Frontend to Backend Contract Summary

Main backend domains consumed by frontend:
- auth
- notebook
- materials/upload
- chat (SSE)
- generation (flashcard/quiz/mindmap)
- presentation
- explainer
- podcast
- jobs/ws updates
- artifacts and file-view proxy

Contract style:
- REST for CRUD and polling.
- SSE for token/progress streams.
- WebSocket for asynchronous processing updates.

## 16) End-to-End User Journey Summary

### 16.1 Study workflow
1. Authenticate.
2. Create/select notebook.
3. Upload learning materials.
4. Wait for processing completion.
5. Chat with materials using RAG/agent/research/code tools.
6. Generate derivative outputs (flashcards/quiz/mindmap/presentation/podcast/explainer).
7. View/download artifacts and exports.

### 16.2 Real-time behavior map
- Material processing progress: websocket-driven updates.
- Conversational output: SSE streaming.
- Long-running generation jobs: status polling + event updates.

This frontend is designed as a notebook-centric orchestration UI that coordinates multiple AI workflows while keeping state synchronized across sidebar, chat, and studio panels.
