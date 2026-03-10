# KeplerLab Frontend — Complete Architecture & Feature Documentation

---

## Table of Contents

1. [Overview](#overview)
2. [Technology Stack](#technology-stack)
3. [Project Structure](#project-structure)
4. [Routing Architecture](#routing-architecture)
5. [Authentication System](#authentication-system)
6. [State Management (Zustand)](#state-management-zustand)
7. [API Client Layer](#api-client-layer)
8. [Real-Time Layer (SSE + WebSocket)](#real-time-layer-sse--websocket)
9. [Page-by-Page Breakdown](#page-by-page-breakdown)
10. [Component Architecture](#component-architecture)
    - [Layout Components](#layout-components)
    - [Sidebar (Sources Panel)](#sidebar-sources-panel)
    - [Chat Panel](#chat-panel)
    - [Studio Panel](#studio-panel)
    - [Notebook Header](#notebook-header)
11. [Feature Deep Dives](#feature-deep-dives)
    - [Upload Flow](#upload-flow)
    - [Chat & Streaming Flow](#chat--streaming-flow)
    - [Flashcard Feature](#flashcard-feature)
    - [Quiz Feature](#quiz-feature)
    - [Presentation (PPT) Feature](#presentation-ppt-feature)
    - [Mind Map Feature](#mind-map-feature)
    - [Podcast Studio](#podcast-studio)
    - [Explainer Video Feature](#explainer-video-feature)
    - [Code Execution (Chat)](#code-execution-chat)
    - [Web Search (Chat)](#web-search-chat)
    - [Deep Research (Chat)](#deep-research-chat)
12. [Hooks Reference](#hooks-reference)
13. [Stores Reference](#stores-reference)
14. [Theming](#theming)
15. [Mobile Responsiveness](#mobile-responsiveness)
16. [Configuration & Build](#configuration--build)
17. [Environment Variables](#environment-variables)

---

## Overview

The KeplerLab frontend is a **Next.js 16** (App Router) single-page-ish application with real-time streaming, multi-panel workspace layout, and deep integration with the backend API. It supports:

- Authentication (login/signup) with JWT access token + HttpOnly refresh cookie
- Workspace per Notebook: 3-panel layout (Sidebar / Chat / Studio)
- Streaming AI chat with RAG, web search, code execution, and deep research
- Study tools: Flashcards, Quiz, Presentations, Mind Maps, Podcast, Explainer Videos
- Real-time material processing updates via WebSocket
- Dark/light modes, syntax highlighting, LaTeX math rendering

---

## Technology Stack

| Category | Technology |
|----------|-----------|
| Framework | Next.js 16.1.6 (App Router) |
| UI Library | React 19 |
| State Management | Zustand 5.0.11 |
| Styling | Tailwind CSS 3.4.17 |
| Icons | lucide-react 0.474.0 |
| Theming | next-themes 0.4.6 |
| Notifications | react-toastify |
| Mind Map Canvas | @xyflow/react 12.10.1 |
| Markdown | react-markdown + remark-gfm + rehype-katex |
| Math Rendering | KaTeX (via rehype-katex) |
| Code Highlighting | react-syntax-highlighter (Dracula theme) |
| PDF/Image Export | jsPDF + html-to-image |
| HTTP Client | native `fetch` via custom `apiFetch()` wrapper |
| SSE Client | custom `streamSSE()` implementation |
| Build Tool | Next.js SWC compiler |
| Package Manager | npm |

---

## Project Structure

```
frontend/
├── src/
│   ├── middleware.js           # Route protection (Next.js Edge Middleware)
│   ├── app/
│   │   ├── layout.jsx          # Root layout (fonts, metadata, Providers)
│   │   ├── page.jsx            # Home: notebook list
│   │   ├── providers.jsx       # ThemeProvider, AuthInitializer, Toasts
│   │   ├── auth/
│   │   │   └── page.jsx        # Login / Signup page
│   │   └── notebook/
│   │       └── [id]/
│   │           ├── layout.jsx  # Notebook route layout
│   │           └── page.jsx    # Notebook workspace (3-panel)
│   ├── components/
│   │   ├── chat/
│   │   │   ├── ChatPanel.jsx           # Full chat panel
│   │   │   ├── ChatHistorySidebar.jsx  # Session list sidebar
│   │   │   ├── ChatInput.jsx           # Message input
│   │   │   ├── MessageList.jsx         # Message rendering
│   │   │   ├── MessageBubble.jsx       # Individual message
│   │   │   ├── MarkdownMessage.jsx     # Markdown + KaTeX + syntax highlight
│   │   │   ├── BlockActions.jsx        # Per-paragraph inline actions
│   │   │   ├── ArtifactCard.jsx        # Code execution output display
│   │   │   ├── CodeBlock.jsx           # Code block with run button
│   │   │   ├── SourceCitations.jsx     # RAG source citations
│   │   │   ├── ResearchPanel.jsx       # Deep research progress
│   │   │   └── WebSearchSources.jsx    # Web search results display
│   │   ├── layout/
│   │   │   ├── Sidebar.jsx         # Left panel: sources manager
│   │   │   ├── Header.jsx          # Notebook workspace header
│   │   │   └── NotebookHeader.jsx
│   │   ├── studio/
│   │   │   ├── StudioPanel.jsx         # Right panel: generation tools
│   │   │   ├── FlashcardView.jsx       # Flashcard stack UI
│   │   │   ├── QuizView.jsx            # Interactive quiz UI
│   │   │   ├── PresentationView.jsx    # Slide viewer
│   │   │   ├── MindMapCanvas.jsx       # React Flow canvas
│   │   │   ├── PodcastStudio.jsx       # Full podcast player UI
│   │   │   └── ExplainerView.jsx
│   │   ├── ui/
│   │   │   ├── Button.jsx
│   │   │   ├── Modal.jsx
│   │   │   ├── Spinner.jsx
│   │   │   ├── ConfirmDialog.jsx
│   │   │   ├── ProgressBar.jsx
│   │   │   └── ...
│   │   └── mindmap/
│   │       └── MindMapCanvas.jsx
│   ├── hooks/
│   │   ├── useChat.js          # Chat + SSE streaming hook
│   │   ├── useMaterialUpdates.js  # WebSocket material/notebook events
│   │   └── useResizable.js     # Panel drag resize logic
│   ├── stores/
│   │   ├── useAuthStore.js     # Auth state + token management
│   │   ├── useAppStore.js      # Master app state (unified)
│   │   ├── useChatStore.js     # Chat messages state
│   │   ├── useMaterialStore.js # Materials state
│   │   └── useNotebookStore.js # Notebook state
│   ├── lib/
│   │   ├── api/
│   │   │   ├── config.js       # apiFetch, auto token refresh
│   │   │   ├── auth.js         # Auth API wrappers
│   │   │   ├── generation.js   # Flashcard, quiz, PPT API
│   │   │   ├── materials.js    # Upload, listing, delete
│   │   │   ├── notebooks.js    # CRUD for notebooks
│   │   │   ├── podcast.js      # Podcast API
│   │   │   └── chat.js         # Chat/session API
│   │   └── stream/
│   │       └── streamClient.js # SSE parser
│   └── styles/
│       └── globals.css         # Tailwind base, custom scrollbar, themes
├── public/
│   ├── favicon.ico
│   └── ...static assets
├── next.config.mjs             # Next.js config + API proxy
├── tailwind.config.js          # Tailwind theme extension
├── jsconfig.json               # Path aliases
└── package.json
```

---

## Routing Architecture

### Route Map

| Path | Page | SSR / CSR |
|------|------|-----------|
| `/` | Notebook list (home) | CSR (uses auth) |
| `/auth` | Login / Signup | CSR |
| `/notebook/[id]` | Workspace | CSR (dynamic import) |
| `/notebook/draft` | Pre-notebook chat (no materials) | CSR |
| `/view/*` | Public view (no auth required) | SSR-friendly |

### Middleware (`src/middleware.js`)

Next.js Edge Middleware runs on every request:

1. If path starts with: `/auth`, `/view`, `/api`, `/_next`, `/favicon.ico`, static files → **allow through**
2. Check for `refresh_token` cookie:
   - Present: allow through
   - Missing: redirect to `/auth?redirect=<original-path>`

This middleware only checks for the cookie presence — actual validation happens on the backend.

### API Proxy (`next.config.mjs`)

Two rewrites configured:
- `/api/presentation/slides/:path*` → `{NEXT_PUBLIC_API_HOST}/api/presentation/slides/:path*`
- `/api/:path*` → `{NEXT_PUBLIC_API_HOST}/api/:path*`

This means all frontend API calls use relative `/api/*` paths — no CORS issues, no hardcoded URLs in components.

---

## Authentication System

### Token Architecture
| Token | Where Stored | Notes |
|-------|-------------|-------|
| Access Token | `_accessTokenRef` (JS module var) + Zustand `authStore` | Never stored in localStorage |
| Refresh Token | HttpOnly cookie (`refresh_token`) | Set by backend, inaccessible to JS |

### Auth Store (`useAuthStore.js`)

Core state: `user`, `isAuthenticated`, `isLoading`, `_accessTokenRef` (module-level, not reactive)

#### `initAuth()` — Application Bootstrap
```
1. Guard: _initPromise singleton (only runs once per page load)
2. Call GET /auth/me (with current access token if any)
   - If 200: set user, authenticated=true
   - If 401: call refreshAccessToken()
     - If refresh succeeds: set user, schedule next refresh
     - If refresh fails: clear state, redirect to /auth?reason=expired
3. Set loading=false
```

Called from `AuthInitializer` component in `providers.jsx` on mount.

#### `scheduleRefresh()`
- Sets a `setTimeout` for `TIMERS.TOKEN_REFRESH_INTERVAL` (typically 14 minutes = ACCESS_TOKEN_EXPIRE_MINUTES - 1)
- On trigger: `POST /auth/refresh` → update `_accessTokenRef`
- Retry policy: exponential backoff (2s → 4s → 8s), max 3 attempts
- On 3rd failure: trigger session expiry handler

#### `login(email, password)`
```
1. POST /auth/login → {access_token, user, token_type}
2. setAccessToken(access_token) to module ref
3. Set user in store, isAuthenticated=true
4. scheduleRefresh()
```

#### `logout()`
```
1. POST /auth/logout (gives backend chance to revoke tokens)
2. Clear _accessTokenRef
3. Clear user from store
4. Cancel scheduled refresh
5. Redirect to /auth
```

#### `_syncToken(token)`
- Syncs token to both `_accessTokenRef` and `apiConfig.setAccessToken(token)` to keep all API calls updated

---

## State Management (Zustand)

### Store Overview

| Store | Responsibility |
|-------|---------------|
| `useAuthStore` | Auth tokens, user info, refresh scheduling |
| `useAppStore` | Master orchestration: active notebook, panel state, podcast events, pending messages |
| `useChatStore` | Chat messages array, streaming state, session ID |
| `useMaterialStore` | Materials list, upload state, selected sources |
| `useNotebookStore` | Notebooks list, current notebook |

---

### `useAppStore` (Master Store)

The central coordination store. Key state:

| State Key | Type | Description |
|-----------|------|-------------|
| `currentNotebook` | Notebook | Active notebook object |
| `activeStudioFeature` | string | Which studio panel is open |
| `studioContent` | object | Content for the active studio feature |
| `generatedContentHistory` | GeneratedContent[] | All saved content for notebook |
| `podcastWsHandlerRef` | RefObject | Shared ref for podcast WS events |
| `pendingChatMessage` | string | Cross-component chat trigger |
| `isSidebarOpen` | bool | Mobile sidebar state |
| `isChatHistoryOpen` | bool | Chat history panel toggle |

Key actions:
- `resetForNotebookSwitch()` — clears materials, sources, messages, session, content
- `setActiveStudioFeature(feature)` — switches studio panel (flashcards, quiz, ppt, mindmap, podcast, explainer)
- `addGeneratedContent(content)` — saves to local history + triggers DB save
- `setPendingChatMessage(msg)` — used by Sidebar to trigger chat with "send message to chat" action

---

### `useChatStore`

| State | Description |
|-------|-------------|
| `messages` | Array of ChatMessage objects |
| `sessionId` | Current chat session UUID |
| `isStreaming` | Whether SSE stream is active |
| `error` | Last error string |

Message structure:
```js
{
  id: string,                // local or DB UUID
  role: 'user' | 'assistant',
  content: string,           // full text (appended during streaming)
  isStreaming?: boolean,
  intent?: string,           // 'rag' | 'web_search' | 'code_execution' | 'chat'
  chunks_used?: number,
  artifacts?: Artifact[],
  codeBlocks?: CodeBlock[],
  webSources?: Source[],
  researchState?: ResearchState,
  agentMeta?: object,
  blocks?: ResponseBlock[],
}
```

`updateLastMessage(updater)` — uses functional updater for atomic streaming appends.

---

### `useMaterialStore`

| State | Description |
|-------|-------------|
| `materials` | Material[] for current notebook |
| `selectedSources` | string[] of selected material IDs |
| `isUploading` | Upload in progress flag |
| `uploadProgress` | Number 0-100 |

Actions:
- `toggleSourceSelection(id)` — toggle one material in/out of selection
- `selectAllSources()` — select all `completed` materials
- `deselectAllSources()` — clear all selections
- `updateMaterialStatus(id, update)` — update status from WebSocket message

---

### `useNotebookStore`

| State | Description |
|-------|-------------|
| `notebooks` | Notebook[] (home page list) |
| `isLoading` | Fetch in-progress |

Actions: `fetchNotebooks`, `createNotebook`, `renameNotebook`, `deleteNotebook`

---

## API Client Layer

**File**: `src/lib/api/config.js`

### Core Wrapper: `apiFetch(path, options)`
```
1. Inject Authorization header: `Bearer ${getAccessToken()}`
2. Inject default Content-Type: application/json
3. On 401 response:
   a. Check _refreshPromise (dedup: another refresh in flight?)
   b. If not: set _refreshPromise = refreshAccessToken() → await
   c. Retry original request once with new token
   d. If retry also 401: call onSessionExpired callback (→ redirect to /auth?reason=expired)
4. Return Response object
```

### `apiFetchFormData(path, formData, options)`
- Same as `apiFetch` but omits `Content-Type` (let browser set multipart boundary)
- Same 401 retry logic

### `apiJson(path, options)` = `apiFetch()` + `res.json()`

### `fetchAudioObjectUrl(path)` 
- Authenticated fetch for audio files
- Returns `URL.createObjectURL(blob)` for use in `<audio>`

### Token Management
```js
let _token = null;
export const setAccessToken = (t) => (_token = t);
export const getAccessToken = () => _token;
```

Module-level storage — never touches localStorage.

### Session Expiry
```js
let _onExpired = null;
export const onSessionExpired = (cb) => (_onExpired = cb);
// Called when refresh token also fails → triggers logout + redirect
```

### API Modules

#### `auth.js`
- `login(email, password)` → `POST /auth/login`
- `signup(email, username, password)` → `POST /auth/signup`
- `logout()` → `POST /auth/logout`
- `getMe()` → `GET /auth/me`
- `refreshToken()` → `POST /auth/refresh`

#### `notebooks.js`
- `fetchNotebooks()` / `createNotebook()` / `updateNotebook()` / `deleteNotebook()`
- `fetchNotebookContent(id)` → get all generated content for notebook
- `saveGeneratedContent(id, data)` → save flashcards/quiz/etc.

#### `materials.js`
- `fetchMaterials(notebookId)` → list all materials
- `deleteMaterial(id)` → delete material + embeddings
- `uploadFile(notebookId, file, onProgress)` → multipart POST with progress tracking
- `addUrl(notebookId, url, title?)` → add URL/YouTube
- `addText(notebookId, text, title)` → paste text

#### `generation.js`
- `generateFlashcards(params)` → `POST /flashcard`
- `generateQuiz(params)` → `POST /quiz`
- `generatePresentation(params)` → `POST /presentation/async` + poll job
  - Creates async job
  - Polls `GET /jobs/{jobId}` every 3 seconds
  - Resolves when `status === 'completed'`
  - Timeout after 10 minutes
- `generateMindMap(params)` → `POST /mindmap`

#### `podcast.js`
- `createPodcastSession(params)` → `POST /podcast/session`
- `startPodcast(sessionId)` → `POST /podcast/session/{id}/start`
- `getPodcastSession(sessionId)` → `GET /podcast/session/{id}`
- `listPodcastSessions(notebookId)` → list sessions
- `askPodcastQuestion(sessionId, question)` → `POST /podcast/session/{id}/question`

#### `chat.js`
- `createChatSession(notebookId)` → `POST /chat/create-session/{notebookId}`
- `getChatSessions(notebookId)` → `POST /chat/sessions/{notebookId}`
- `deleteChatSession(sessionId)` → `DELETE /chat/sessions/{sessionId}`
- `getChatHistory(notebookId, sessionId)` → `GET /chat/history/{notebookId}?session_id=`
- `streamChat(params)` → `POST /chat` — returns `Response` object for SSE processing

---

## Real-Time Layer (SSE + WebSocket)

### SSE Client (`src/lib/stream/streamClient.js`)

`streamSSE(response, handlers, signal)`:
```
1. Get reader: response.body.getReader(), TextDecoder
2. Buffer incoming chunks
3. Split on double-newline to extract complete SSE events
4. Parse each event:
   a. Extract "event: <type>" line
   b. Extract "data: <json>" line
   c. If event line present → handlers[eventType]?.(parsedData)
   d. If no event line → use data.type field for routing (fallback)
5. Handles AbortSignal for cancellation
```

Supported handler names:
`token`, `done`, `error`, `step`, `artifact`, `code_block`, `web_search_update`, `web_sources`, `research_start`, `research_phase`, `tool_start`, `tool_result`, `repair_suggestion`, `install_progress`, `execution_done`, `execution_blocked`, `blocks`, `meta`

### WebSocket (`useMaterialUpdates.js`)

```
1. Connect: new WebSocket(`/api/ws/jobs/${user_id}?token=${accessToken}`)
2. Listen for messages:
   - material_update → update material in useMaterialStore
   - notebook_update → dispatch custom DOM event "notebookNameUpdate"
   - podcast_* → call podcastWsHandlerRef.current(msg) (registered by PodcastStudio)
   - pong → acknowledge keepalive
3. Auto-reconnect on close with 3s delay (max 5 attempts)
4. Cleanup on notebook switch / component unmount
```

---

## Page-by-Page Breakdown

### Home Page (`/app/page.jsx`)

- Calls `initAuth()` on mount (authentication guard)
- Fetches notebooks via `useNotebookStore.fetchNotebooks()`
- Renders a grid of notebook cards
- Create notebook: inline input or modal
- Rename notebook: inline edit (click name → input)
- Delete notebook: confirm dialog → `deleteNotebook(id)`
- Listens for `notebookNameUpdate` DOM event → updates notebook card name in real-time (triggered by AI auto-rename via WebSocket)
- Redirects to `/auth` if not authenticated

### Auth Page (`/app/auth/page.jsx`)

**URL params**:
- `?mode=signup` — start in signup mode
- `?reason=expired` — show "Session expired" banner
- `?redirect=<path>` — redirect to this path after login

**Layout**: Two-column (desktop)
- Left: animated feature showcase with bullet points of KeplerLab capabilities
- Right: login/signup form

**Form behavior**:
- Toggle between Login / Sign Up tabs
- Client-side validation (email format, password strength: min 8 chars, uppercase, lowercase, digit)
- Calls `useAuthStore.login()` or `useAuthStore.signup()`
- On success: redirects to `?redirect` param destination or `/`
- Error display: inline below inputs

### Notebook Workspace (`/app/notebook/[id]/page.jsx`)

**Layout**: Full-screen 3-panel:
```
[Header/Navbar]
[Sidebar | ChatPanel | StudioPanel]
```

On mount:
1. Validate auth via `initAuth()`
2. Fetch notebook details: `GET /notebooks/{id}`
3. Fetch materials: `GET /notebooks/{id}/materials`
4. Fetch generated content history: `GET /notebooks/{id}/content`
5. Connect WebSocket: `useMaterialUpdates(user_id)` hook
6. Load saved chat session if `?session=<id>` URL param present

**Draft mode** (`/notebook/draft`):
- No notebook ID
- Chat works but material context is empty
- On first message: auto-creates notebook and redirects to `/notebook/{id}`

**Panel layout**:
- All three panels use `dynamic()` import (no SSR) to avoid hydration issues
- Each wrapped in `PanelErrorBoundary`
- Mobile: sidebar shown as overlay with toggle button
- `useResizable` hook controls sidebar and studio panel widths

---

## Component Architecture

### Layout Components

#### `Header.jsx` / `NotebookHeader.jsx`
- Notebook title (editable inline)
- LLM model selector (shows active model)
- Theme toggle (dark/light)
- User menu (logout)

---

### Sidebar (Sources Panel)

**File**: `src/components/layout/Sidebar.jsx`

The sidebar is the left panel managing all source materials.

#### Panel Sections
1. **Add Sources** — upload/URL/text/web search tabs
2. **Sources List** — all materials for the notebook
3. **Selection Controls** — select all, deselect all

#### Upload UI
```
Tab 1: File Upload
  - Drag-and-drop zone or click to browse
  - Multiple file selection
  - Shows per-file progress bar
  - Calls materials.uploadFile() with XMLHttpRequest for progress events

Tab 2: Add URL
  - Input for https:// URLs
  - Auto-detects YouTube URLs → shows YouTube badge
  - Calls materials.addUrl()

Tab 3: Paste Text
  - Textarea + optional title
  - Calls materials.addText()

Tab 4: Web Search
  - Search query input
  - Result list with checkboxes
  - "Add as source" on selected results
```

#### Material Status Indicators
Each material in the list shows status:
| Status | Display |
|--------|---------|
| `pending` | Gray dot, "Queued" |
| `processing` | Spinning blue dot |
| `ocr_running` | Spinning orange dot, "OCR" |
| `transcribing` | Spinning purple dot |
| `embedding` | Spinning cyan dot |
| `completed` | Green checkmark |
| `failed` | Red X with error tooltip |

#### WebSocket Integration
- `useMaterialUpdates` hook wires WebSocket messages to `updateMaterialStatus()`
- Transitions between status states in real-time without polling
- **Polling fallback**: if any materials are still `processing`, polls every 8 seconds

#### Auto-select
After upload completes (status becomes `completed`), the sidebar auto-selects the new material.

#### Source Selection
Clicking a completed material toggles its selection. The selected material IDs are passed to the Chat hook as `effectiveIds` (filtered to `completed` only).

---

### Chat Panel

**File**: `src/components/chat/ChatPanel.jsx`

#### Panel Structure
```
[ChatHistorySidebar -- collapsible left side]
[MessageList]
[ChatInput]
```

#### Session Management
- On mount: loads sessions from `getChatSessions(notebookId)`
- URL param `?session=<id>`: loads that specific session
- Create new: `createChatSession(notebookId)` → clears messages → sets sessionId
- Switch session: clear messages → fetch history for new session
- Delete session: confirm → remove from list → reset to latest

#### Draft Mode
If `notebookId === 'draft'`:
- No materials shown
- On first message sent: auto-create notebook (`POST /notebooks`) → redirect to `/notebook/{id}`

#### `effectiveIds`
Computed from `selectedSources` filtered to only `status === 'completed'` materials. Sent with every chat request.

#### Message Input Features
- Multi-line textarea (auto-grows)
- `Enter` to send, `Shift+Enter` for newline
- Abort button shown while streaming
- Disabled during stream

---

### Chat Messages (`MessageList.jsx`, `MessageBubble.jsx`)

#### User Messages
- Simple text bubble (right-aligned)

#### Assistant Messages
- `MarkdownMessage` — full markdown rendering:
  - GFM (tables, strikethrough, task lists)
  - KaTeX math (inline `$...$` and block `$$...$$`)
  - Syntax-highlighted code blocks (react-syntax-highlighter, Dracula theme)
  - Copy button on code blocks
- `BlockActions` — shown when message has `blocks[]`:
  - Per-paragraph hover tooltip: Ask, Simplify, Translate, Explain
  - Click → streams block follow-up response in place
- `SourceCitations` — shown when intent=rag:
  - Lists which sources were used
  - Shows similarity context
- `ArtifactCard` — shown when code execution produces files:
  - Charts: inline image render
  - CSV: paginated table view
  - PDF: embedded viewer
  - Audio: inline player
  - Code: syntax highlight + download
- `CodeBlock` — code blocks with "Run" button:
  - Click "Run" → opens code execution panel with the code
- `WebSearchSources` — shown for web search responses:
  - Card grid of source URLs (title + snippet)
- `ResearchPanel` — shown for deep research:
  - Progress phases: Searching → Scraping → Synthesizing
  - Source count, iteration count
  - Expandable source list

#### Streaming Behavior
During streaming, the last message (`isStreaming=true`) appends tokens as they arrive. The message bubble shows a blinking cursor until `done` event fires.

---

### Studio Panel

**File**: `src/components/studio/StudioPanel.jsx`

The right panel houses all generation tools.

#### Tab Navigation
Tabs: Flashcards | Quiz | Presentation | Mind Map | Podcast | Explainer

Each tab has:
1. **Config section**: inputs for customization
2. **Generate button**: triggers API call
3. **Content view**: renders the generated artifact
4. **History**: past generated items for this notebook (loaded from `generatedContentHistory`)

#### Panel Resize
- A drag handle on the left edge
- `useResizable` hook: `mousedown` → track `mousemove` → compute delta → clamp between `minWidth=320` and `window.width * 0.6`
- Width stored in component `useState`, resets on mobile

#### Abort Control
Each feature type gets its own `AbortController`. Cancel button mid-generation calls `controller.abort()`.

---

### Flashcard View (`FlashcardView.jsx`)

```
State: currentIndex, isFlipped, savedSet

- Deck of cards (swipe or click to flip)
- Front: term/question
- Back: answer/explanation
- Previous / Next navigation
- Flip animation (CSS 3D transform)
- Export: JSON download or PDF
- Save to notebook: POST /notebooks/{id}/content
- Category filter: if cards have category field
```

---

### Quiz View (`QuizView.jsx`)

```
State: currentQuestion, answers, submitted, score

- One question at a time (pagination)
- MCQ: 4 radio options
- Submit: reveals answer + explanation
- Score display at end
- Retry: reset answers
- Export: JSON or PDF
- Save to notebook
```

---

### Presentation View (`PresentationView.jsx`)

```
State: currentSlide, isFullscreen, isLoading

- HTML iframe embedding the full presentation HTML
- Navigation: arrow buttons, keyboard arrows
- Fullscreen mode
- Slide thumbnails panel (sidebar)
- Download: serves HTML file directly
- Explainer trigger: "Make Video" button → opens explainer config
```

---

### Mind Map Canvas (`MindMapCanvas.jsx`)

```
Uses @xyflow/react.

Layout: dagre tree layout (auto-computed)
Nodes: labeled boxes with type colors
Edges: animated bezier curves
Controls: pan, zoom, fit-to-view

Interaction:
  - Drag nodes to reposition
  - Click node: highlight connected edges
  - Export: html-to-image → PNG download
```

---

### Podcast Studio (`PodcastStudio.jsx`)

Complex multi-state component.

```
States: idle → configuring → generating → ready

Config phase:
  - Mode selector (overview, deep-dive, debate, q-and-a, topic)
  - Topic input (required for 'topic' mode)
  - Language selector
  - Voice customization (host + guest)

Generation phase:
  - WebSocket event listener registered via podcastWsHandlerRef
  - Progress phases: "Generating Script..." → "Synthesizing Audio..." → "Ready"
  - Progress bar animated with percentage from server

Playback phase (when status=ready):
  - Custom audio player (not native <audio>)
  - Plays segments sequentially: src = fetchAudioObjectUrl(segment.audioUrl)
  - Shows current speaker name (host/guest)
  - Chapter navigation: jump to chapter start
  - Timeline: shows segment markers
  - Transcript panel: synchronized text highlight
  - Playback speed controls: 0.5x, 1x, 1.25x, 1.5x, 2x

Q&A panel:
  - Pause button to stop at current segment
  - Question input: text or voice record
  - Streams answer text + plays answer audio
  - Q&A exchange shown below player

Bookmarks panel:
  - List of bookmarks with jump-to
  - Add/delete bookmarks at current timestamp

Export panel:
  - PDF export: POST /podcast/session/{id}/export
  - JSON export
```

---

### Explainer Video Feature

```
Config:
  - Source: use existing presentation OR generate new
  - Narration language
  - Voice gender (male/female)
  
Generation:
  - POST /explainer/generate → starts background task
  - Poll GET /explainer/{id} every 5 seconds
  - Progress stages shown: Capturing → Scripting → Audio → Composing
  
Playback:
  - <video> element pointing to /api/explainer/{id}/video
  - Chapter markers overlaid on progress bar
  - Download full video
```

---

## Feature Deep Dives

### Upload Flow

```
User selects file → Sidebar.handleFileUpload()
  ↓
apiFetchFormData('/api/upload', formData):
  - XMLHttpRequest for progress events
  - onProgress callback → uploadProgress state
  ↓
Backend returns {material_id, job_id, status: 'pending'}
  ↓
Material added to list with status 'pending'
  ↓
WebSocket material_update events arrive:
  status: pending → processing → (ocr_running?) → embedding → completed
  Each update: useMaterialStore.updateMaterialStatus()
  UI re-renders with new status badge
  ↓
On 'completed': auto-select the new material
```

---

### Chat & Streaming Flow

```
User types in ChatInput → presses Enter → sendMessage()
  ↓
useChat.sendMessage(text):
  1. If no sessionId: createChatSession() first
  2. Optimistic UI: add user message to messages array
  3. Add empty assistant message (isStreaming=true)
  4. Create AbortController
  5. Call api/chat.streamChat({
       notebook_id, session_id, message,
       material_ids: effectiveIds,
       stream: true
     })
  ↓
streamChat() returns Response object (do NOT await body)
  ↓
streamSSE(response, handlers, abortSignal):
  - token:        updateLastMessage → append content
  - meta:         updateLastMessage → set intent, chunks_used
  - tool_start:   updateLastMessage → add toolCallState
  - tool_result:  updateLastMessage → update toolCallState
  - artifact:     updateLastMessage → push to artifacts[]
  - code_block:   updateLastMessage → push to codeBlocks[]
  - web_sources:  updateLastMessage → set webSources[]
  - web_search_update: updateLastMessage → set webSearchState
  - research_start: updateLastMessage → set researchState.phase
  - research_phase: updateLastMessage → update researchState
  - blocks:       updateLastMessage → set blocks[] for BlockActions
  - done:         set isStreaming=false, update elapsed
  - error:        set error state, isStreaming=false
  ↓
Message rendering updates on each token (React state update)
```

---

### Flashcard Feature

```
User opens Studio → Flashcards tab
Config:
  - Select sources (or uses selectedSources from sidebar)
  - Card count (1-150, default 20)
  - Difficulty (easy/medium/hard)
  - Topic (optional)
  - Additional instructions (optional)
  ↓
Click "Generate":
  api/generation.generateFlashcards(params)
  POST /flashcard {material_ids, card_count, difficulty, topic, ...}
  Await JSON response (synchronous, ~5-30s)
  ↓
On success:
  Set flashcards[] in studio state
  Render FlashcardView component
  ↓
User interactions:
  - Click card → flip animation (front/back)
  - Arrow buttons → navigate deck
  - Category filter pills
  - Save: POST /notebooks/{id}/content → stored in generatedContentHistory
  ↓
History panel: loads saved flashcard sets from generatedContentHistory
```

---

### Quiz Feature

```
Config:
  - Select sources
  - Question count (1-150, default 15)
  - Difficulty
  - Topic (optional)
  ↓
Generate: POST /quiz → wait JSON
  ↓
QuizView renders:
  - One question per screen
  - 4 MCQ options (radio)
  - Submit → shows correct answer + explanation
  - Next question
  - Final score screen
  - Retry button
```

---

### Presentation (PPT) Feature

```
Config:
  - Select sources
  - Slide count (default 10)
  - Theme (light/dark/corporate/minimal/vibrant)
  - Additional instructions
  ↓
Generate (async):
  1. POST /presentation/async → {job_id}
  2. Start polling: GET /jobs/{job_id} every 3s
  3. Show progress spinner with job status
  4. On completed: extract result from job.result
  5. On timeout (10min): show error
  ↓
PresentationView renders:
  - HTML slides in iframe
  - Navigation controls
  - Slide list sidebar
  - Fullscreen toggle
  ↓
Make Video button:
  - Opens explainer config overlay
  - Pre-fills presentation_id
```

---

### Mind Map Feature

```
Config:
  - Select sources (uses app-level notebook sources, not just selected)
  - Additional context (optional)
  ↓
Generate: POST /mindmap
  Returns {nodes: [{id, label, type}], edges: [{from, to}]}
  ↓
MindMapCanvas renders:
  - dagre layout applied to nodes/edges
  - ReactFlow canvas
  - Drag, pan, zoom
  - Export PNG
```

---

### Podcast Studio

Detailed flow in [Podcast Studio component section](#podcast-studio).

---

### Explainer Video Feature

```
Config:
  - Source: existing presentation from history OR generate new PPT
  - Narration language
  - Voice: male/female
  ↓
Generate: POST /explainer/generate
  Returns {explainer_id, status: 'pending'}
  ↓
Polling: GET /explainer/{id} every 5s
  Status transitions → update progress UI:
  'capturing_slides' → 'generating_script' → 'generating_audio' → 'composing_video' → 'completed'
  ↓
ExplainerView renders:
  - HTML5 video player
  - Chapter TOC
  - Download button
```

---

### Code Execution (Chat)

When chat intent is `CODE_EXECUTION`:
```
Backend generates code → SSE code_block event:
  {code, language, session_id}
  ↓
Frontend renders CodeBlock component with "Run" button
User clicks "Run":
  POST /code-execution/execute-code (SSE stream)
    ↓
  Events:
    install_progress: "Installing seaborn..."
    repair_suggestion: "Fixing error..."
    artifact: {filename, mime, display_type, download_token}
    execution_done: {stdout, stderr, elapsed}
    ↓
  Artifacts rendered as ArtifactCard components
  Download links generated from /api/artifacts/download/{token}
```

---

### Web Search (Chat)

```
User message: "find latest AI news"
  ↓
Backend detects WEB_SEARCH capability
  ↓
SSE events:
  tool_start: {tool: "web_search"}
  web_search_update: {status: "searching", queries: [...]}
  web_sources: {sources: [{title, url, snippet}]}
  token: response chunks
  done:
  ↓
Frontend:
  WebSearchSources component shows source cards
  Response includes inline citations
```

---

### Deep Research (Chat)

```
User triggers research intent (explicit or via menu)
  ↓
SSE events:
  research_start: {query, max_iterations, target_sources}
  research_phase: {phase: "searching", iteration: 1, queries: [...]}
  research_phase: {phase: "scraping", iteration: 1, sources_count: 15}
  research_phase: {phase: "synthesizing", iteration: 2, ...}
  token: synthesis content tokens
  done:
  ↓
Frontend:
  ResearchPanel shows:
    - Phase indicator (spinning) 
    - Iteration counter
    - Sources found count
    - Expandable URL list
  Synthesis rendered as streaming markdown
```

---

## Hooks Reference

### `useChat(notebookId, draftMode)` — `src/hooks/useChat.js`

Primary purpose: manage the lifecycle of a chat conversation.

```js
const {
  messages,           // ChatMessage[]
  sessionId,          // current session UUID
  isStreaming,        // bool
  sessions,           // ChatSession[]
  sendMessage,        // async (text, materialIds) => void
  abortStream,        // () => void
  loadHistory,        // (sessionId) => void
  createSession,      // () => Promise<session>
  switchSession,      // (sessionId) => void
  deleteSession,      // (sessionId) => void
  loadSessions,       // () => void
} = useChat(notebookId, draftMode)
```

State management:
- All messages in `useChatStore.messages`
- `abortRef` stores current `AbortController`
- On new session: `useChatStore.reset()` clears messages

### `useMaterialUpdates(userId)` — WebSocket hook

```js
useMaterialUpdates(userId) {
  // establishes WebSocket connection
  // routes messages to stores
  // reconnects on failure
  // cleans up on unmount
}
```

### `useResizable(initialWidth, minWidth, maxWidth)` — `src/hooks/useResizable.js`

```js
const { width, handleMouseDown } = useResizable(380, 240, 600);
// Attach handleMouseDown to drag handle element
// Returns current pixel width that updates on drag
```

---

## Stores Reference

### Store Initialization Chain

```
_app bootstrap:
  providers.jsx → AuthInitializer.mount()
    ↓
  useAuthStore.initAuth()
    → GET /auth/me
    → scheduleRefresh()
    ↓
  Renders app with isAuthenticated=true/false
    ↓
  Home Page:
    → useNotebookStore.fetchNotebooks()
    ↓
  Notebook workspace:
    → useAppStore.setCurrentNotebook()
    → useMaterialStore (populated from fetch)
    → useChatStore (session from URL param or latest)
    → WebSocket connected
```

---

## Theming

**Provider**: `next-themes` ThemeProvider  
**Storage key**: `kepler-theme`  
**Default**: `dark`  
**Class strategy**: adds `.dark` class to `<html>`

Tailwind config extends with:
- Custom color palette (primary, secondary, surface, on-surface, etc.)
- Typography plugin configuration
- Dark mode: `class` strategy

CSS Variables pattern in `globals.css`:
```css
:root {
  --background: #ffffff;
  --foreground: #171717;
}
.dark {
  --background: #0a0a0a;
  --foreground: #ededed;
}
```

Theme toggle: `Header.jsx` uses `useTheme()` from next-themes.

---

## Mobile Responsiveness

### Breakpoint Strategy
- `lg` (1024px): full 3-panel layout
- `md` (768px): hide sidebar by default, show studio as bottom sheet
- `sm` (640px): single column

### Mobile Sidebar
- Hidden by default on mobile (`isSidebarOpen = false` in `useAppStore`)
- Mobile navbar shows hamburger button
- Sidebar appears as overlay with backdrop
- Add Sources: full-page modal on mobile

### Studio Panel
- On mobile: Studio shown as bottom drawer or full-page
- Feature switching via bottom tab bar

---

## Configuration & Build

### `next.config.mjs`

```js
{
  output: 'standalone',        // Docker-optimized production build
  rewrites: [                  // API proxy
    '/api/presentation/slides/:path*' → backend,
    '/api/:path*' → backend
  ],
  images: {
    remotePatterns: [{
      protocol: 'https',
      hostname: process.env.NEXT_PUBLIC_API_HOST
    }]
  }
}
```

### `jsconfig.json` Path Aliases
```json
{
  "@/*": ["./src/*"]
}
```

### `tailwind.config.js`
- Content paths: `./src/**/*.{js,jsx,ts,tsx}`
- Typography plugin for markdown
- Custom animations: `fade-in`, `slide-up`, `pulse-soft`

---

## Environment Variables

| Variable | Where Used | Description |
|----------|-----------|-------------|
| `NEXT_PUBLIC_API_HOST` | `next.config.mjs` proxy rewrites | Backend API base URL |
| `NEXT_PUBLIC_WS_HOST` | `useMaterialUpdates.js` | WebSocket URL (if different from API host) |

> `NEXT_PUBLIC_*` variables are inlined at build time and exposed to the browser. Never store secrets here.

---

*End of frontend.md*
