# KeplerLab Frontend — Complete Documentation

> **Stack**: Next.js 16 (App Router) · React 19 · Zustand 5 · TailwindCSS 3 · SSE Streaming · WebSocket  
> **Root**: `/home/pratham/disk1/KeplerLab_Agentic/frontend/`

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Technology Stack](#2-technology-stack)
3. [Project Structure](#3-project-structure)
4. [Next.js App Router — Pages & Routes](#4-nextjs-app-router--pages--routes)
5. [Edge Middleware — Auth Guard](#5-edge-middleware--auth-guard)
6. [Providers & App Initialization](#6-providers--app-initialization)
7. [Authentication Flow](#7-authentication-flow)
8. [API Layer (`lib/api/`)](#8-api-layer-libapi)
9. [SSE Streaming (`lib/stream/`)](#9-sse-streaming-libstream)
10. [State Management — All 10 Zustand Stores](#10-state-management--all-10-zustand-stores)
11. [Dashboard / Home Page](#11-dashboard--home-page)
12. [Notebook Workspace Page](#12-notebook-workspace-page)
13. [Sidebar Component](#13-sidebar-component)
14. [Header Component](#14-header-component)
15. [ChatPanel Component](#15-chatpanel-component)
16. [ChatInputArea Component](#16-chatinputarea-component)
17. [StudioPanel Component](#17-studiopanel-component)
18. [Presentation Feature](#18-presentation-feature)
19. [Podcast Studio Feature](#19-podcast-studio-feature)
20. [Mind Map Feature](#20-mind-map-feature)
21. [Hooks Reference](#21-hooks-reference)
22. [Constants & Utilities](#22-constants--utilities)
23. [Complete Data Flow Diagrams](#23-complete-data-flow-diagrams)
24. [Component Tree Reference](#24-component-tree-reference)
25. [CSS & Theming System](#25-css--theming-system)

---

## 1. Architecture Overview

KeplerLab's frontend is a **three-panel AI study workspace** built on Next.js App Router with no traditional page-level data fetching (no `getServerSideProps`). All data flows through client-side Zustand stores, authenticated REST API calls, and real-time SSE/WebSocket connections.

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser (Client-only UI)                  │
│  ┌──────────────┬──────────────────────┬──────────────────┐ │
│  │   Sidebar    │     ChatPanel        │   StudioPanel    │ │
│  │ (Materials + │  (Streaming Chat +   │ (Flashcards,     │ │
│  │  Sources)    │   Agent/RAG/Code)    │  Quiz, Slides,   │ │
│  │              │                      │  Podcast, Map)   │ │
│  └──────┬───────┴──────────┬───────────┴──────────┬───────┘ │
│         │                  │                       │         │
│  ┌──────▼──────┐  ┌────────▼──────┐  ┌────────────▼──────┐ │
│  │ useMaterial │  │  useChatStore │  │  useUI/Podcast/   │ │
│  │   Store     │  │  useAuthStore │  │  Agent/Notebook   │ │
│  └──────┬──────┘  └────────┬──────┘  └────────────┬──────┘ │
│         │                  │                       │         │
│  ┌──────▼────────────────────────────────────────▼──────┐  │
│  │              lib/api/ (apiFetch + auto-refresh)        │  │
│  └──────────────────────────┬────────────────────────────┘  │
└─────────────────────────────│────────────────────────────────┘
                               │ HTTP / SSE / WebSocket
                    ┌──────────▼──────────┐
                    │  FastAPI Backend     │
                    │  localhost:8000      │
                    └─────────────────────┘
```

### Key Design Decisions

| Decision | Implementation |
|---|---|
| **No server components for auth** | All auth is client-side via Zustand + cookie HttpOnly refresh tokens |
| **Frontend drives intent** | Chat routing is frontend-controlled (`intentOverride` field) — no backend intent classification |
| **SSE over WebSocket for chat** | Streaming tokens via `EventSource`-compatible fetch (`StreamClient`), WS only for job status |
| **Dynamic imports for heavy panels** | `PodcastStudio`, `MindMapCanvas`, `PresentationView` are lazy-loaded via `next/dynamic` |
| **Centralized fetch** | Single `apiFetch()` function handles all token management and 401 recovery |

---

## 2. Technology Stack

| Package | Version | Purpose |
|---|---|---|
| `next` | 16.1.6 | App Router, server/edge middleware, file routing |
| `react` | 19.2.3 | UI framework |
| `react-dom` | 19.2.3 | DOM rendering |
| `zustand` | 5.0.11 | Client-side state management (10 stores) |
| `tailwindcss` | 3.4.17 | Utility-first CSS framework |
| `next-themes` | 0.4.6 | Dark/light mode with SSR hydration safety |
| `lucide-react` | 0.576.0 | Icon set |
| `@xyflow/react` | 12.10.1 | Mind map canvas (ReactFlow v12) |
| `dagre` | 0.8.5 | Auto-layout algorithm for mind map DAG |
| `react-markdown` | 10.1.0 | Markdown rendering in chat |
| `remark-gfm` | 4.0.1 | GitHub Flavored Markdown (tables, strikethrough) |
| `remark-math` | 6.0.0 | Math block syntax `$$...$$` |
| `rehype-katex` | 7.0.1 | KaTeX rendering for math |
| `rehype-raw` | 7.0.0 | Allow raw HTML in markdown |
| `react-syntax-highlighter` | 16.1.1 | Syntax-highlighted code blocks |
| `react-window` | 2.2.7 | Virtualized list rendering for flashcards |
| `html-to-image` | 1.11.13 | Export mind map as PNG |
| `jspdf` | 4.2.0 | Export mind map as PDF |
| `katex` | 0.16.33 | Direct KaTeX usage |
| `eslint` + `eslint-config-next` | 9 / 16.1.6 | Linting |
| `autoprefixer` | 10.4.20 | CSS vendor prefixes |
| `postcss` | 8.4.49 | CSS processing |

---

## 3. Project Structure

```
frontend/
├── src/
│   ├── middleware.js                 # Edge middleware (auth guard)
│   ├── app/
│   │   ├── layout.jsx                # Root layout (ThemeProvider, Providers)
│   │   ├── page.jsx                  # Dashboard — notebook grid
│   │   ├── providers.jsx             # Client providers + auth init
│   │   ├── error.jsx                 # Global error boundary
│   │   ├── not-found.jsx             # 404 page
│   │   ├── auth/
│   │   │   └── page.jsx              # Login / Signup
│   │   ├── notebook/
│   │   │   └── [id]/
│   │   │       └── page.jsx          # Notebook workspace (3-panel)
│   │   └── view/                     # Public view routes
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.jsx           # Left panel: materials + source selection
│   │   │   └── Header.jsx            # Top bar: nav, theme, user menu
│   │   ├── chat/
│   │   │   ├── ChatPanel.jsx         # Main chat panel (streaming, sessions)
│   │   │   ├── ChatInputArea.jsx     # Text input + slash commands
│   │   │   ├── ChatMessageList.jsx   # Virtualized message list
│   │   │   ├── SlashCommandPills.jsx # Active command badge row
│   │   │   ├── SlashCommandDropdown.jsx  # Slash command picker
│   │   │   ├── CommandBadge.jsx      # Individual command badge
│   │   │   ├── SuggestionDropdown.jsx    # AI question suggestions
│   │   │   └── slashCommands.js      # Command definitions + parseSlashCommand()
│   │   ├── studio/
│   │   │   ├── StudioPanel.jsx           # Right panel: all generation features
│   │   │   ├── InlineFlashcardsView.jsx  # Flashcard viewer
│   │   │   ├── InlineQuizView.jsx        # Quiz viewer
│   │   │   └── InlinePresentationView.jsx # Slide viewer (iframe-based)
│   │   ├── presentation/
│   │   │   └── PresentationView.jsx  # Full presentation renderer
│   │   ├── podcast/
│   │   │   └── PodcastStudio.jsx     # Podcast state-machine UI
│   │   ├── mindmap/
│   │   │   └── MindMapCanvas.jsx     # ReactFlow mind map canvas
│   │   └── ui/
│   │       ├── Toast.jsx             # Toast notification component
│   │       └── ConfirmDialog.jsx     # Modal confirmation dialog
│   ├── stores/
│   │   ├── useAuthStore.js           # Auth state + token lifecycle
│   │   ├── useAppStore.js            # Global hub + re-exports
│   │   ├── useChatStore.js           # Messages, streaming, session ID
│   │   ├── useMaterialStore.js       # Materials list + source selection
│   │   ├── useNotebookStore.js       # Notebooks list + current notebook
│   │   ├── useUIStore.js             # Panel visibility, layout state
│   │   ├── usePodcastStore.js        # Podcast generation state
│   │   ├── useAgentStore.js          # Agent execution state
│   │   ├── useToastStore.js          # Toast queue
│   │   └── useConfirmStore.js        # Confirm dialog state
│   ├── hooks/
│   │   ├── useChat.js                # Chat streaming hook (SSE events)
│   │   ├── useMaterialUpdates.js     # WebSocket material status hook
│   │   ├── usePodcast.js             # Podcast generation hook
│   │   ├── usePodcastPlayer.js       # Audio playback hook
│   │   ├── usePodcastWebSocket.js    # Podcast WS events
│   │   ├── useMindMap.js             # Mind map data hook
│   │   ├── useMicInput.js            # Microphone input hook
│   │   └── useResizablePanel.js      # Panel drag-resize hook
│   ├── lib/
│   │   ├── api/
│   │   │   ├── config.js             # apiFetch(), token management, auto-refresh
│   │   │   ├── auth.js               # login, signup, refresh, logout, getUser
│   │   │   ├── chat.js               # sendChat, getSuggestions, sessions API
│   │   │   ├── materials.js          # upload, list, delete, indexURL
│   │   │   ├── notebooks.js          # CRUD notebooks
│   │   │   ├── generation.js         # flashcards, quiz, presentation async
│   │   │   ├── mindmap.js            # generateMindMap, save, get
│   │   │   ├── podcast.js            # generateScript, generateAudio, sessions
│   │   │   ├── agent.js              # getAgentLog, rerun
│   │   │   └── jobs.js               # pollJob (async job status)
│   │   ├── stream/
│   │   │   ├── client.js             # StreamClient (SSE reader + event dispatcher)
│   │   │   └── state.js              # StreamState (event state accumulator)
│   │   └── utils/
│   │       ├── constants.js          # PANEL, SLIDE, TIMERS, QUICK_ACTIONS, etc.
│   │       └── helpers.js            # generateId(), formatFileSize(), etc.
│   └── styles/
│       └── globals.css               # CSS custom properties + Tailwind base
├── public/                           # Static assets
├── next.config.mjs                   # Next.js config (rewrites, image domains)
├── tailwind.config.js                # Tailwind config (custom colors, fonts)
├── postcss.config.mjs                # PostCSS config
├── eslint.config.mjs                 # ESLint config
├── jsconfig.json                     # Path aliases (@/ → src/)
└── package.json                      # Dependencies
```

---

## 4. Next.js App Router — Pages & Routes

### Route Map

| URL | File | Access | Description |
|---|---|---|---|
| `/` | `app/page.jsx` | Auth required | Dashboard: list, create, open notebooks |
| `/auth` | `app/auth/page.jsx` | Public | Login / Signup form |
| `/notebook/[id]` | `app/notebook/[id]/page.jsx` | Auth required | 3-panel AI workspace |
| `/view/*` | `app/view/...` | Public | Shared notebook views |
| `/_next/*` | Internal | Public | Next.js assets |
| `/api/*` | Internal | Public | Next.js API routes (if any) |

### `layout.jsx` — Root Layout

```jsx
// app/layout.jsx
export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <Providers>     {/* ThemeProvider wrapping */}
          {children}
          <Toast />
          <ConfirmDialog />
        </Providers>
      </body>
    </html>
  );
}
```

- `suppressHydrationWarning` prevents hydration mismatch from `next-themes` applying `data-theme` on the server.
- `<Toast />` and `<ConfirmDialog />` are portal-like global overlays, mounted once at root.
- Font: system sans-serif stack applied via CSS custom properties.

---

## 5. Edge Middleware — Auth Guard

**File**: `src/middleware.js`  
**Runs on**: Next.js Edge Runtime (before page render)

```js
// middleware.js
const PUBLIC_PREFIXES = ['/auth', '/view', '/api', '/_next', '/favicon'];

export function middleware(request) {
  const { pathname } = request.nextUrl;
  const isPublic = PUBLIC_PREFIXES.some(prefix => pathname.startsWith(prefix));

  if (!isPublic) {
    const refreshToken = request.cookies.get('refresh_token');
    if (!refreshToken) {
      const redirectUrl = new URL('/auth', request.url);
      redirectUrl.searchParams.set('redirect', pathname);
      return NextResponse.redirect(redirectUrl);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
```

**Logic**:
1. Check if path starts with any public prefix.
2. If protected, look for `refresh_token` HttpOnly cookie (set by backend `/auth/login`).
3. If missing → redirect to `/auth?redirect=<original_path>`.
4. The access token is NOT checked here (it lives in memory) — only the presence of the refresh cookie gates access.

> Note: The middleware does NOT validate the cookie's JWT signature — full validation happens on the first API call. This is intentional (Edge Runtime has no DB access).

---

## 6. Providers & App Initialization

**File**: `src/app/providers.jsx`

```jsx
'use client';
export default function Providers({ children }) {
  return (
    <ThemeProvider attribute="data-theme" defaultTheme="dark" enableSystem={false}>
      <AuthInitializer />
      {children}
    </ThemeProvider>
  );
}
```

### `AuthInitializer`

A headless component (renders `null`) that fires `initAuth()` exactly once on mount:

```jsx
function AuthInitializer() {
  const initAuth = useAuthStore(s => s.initAuth);
  useEffect(() => {
    initAuth();
  }, []);
  return null;
}
```

### What `initAuth()` Does (in sequence)

```
1. Guard: already initializing? → return same promise (dedup via _initPromise)
2. Call POST /auth/refresh (browser sends refresh_token cookie automatically)
   ├── Success → setAccessToken(token) → scheduleRefresh(expiresAt)
   │            → call GET /auth/me → setUser(user)
   └── Failure → clearAuth() → (middleware will redirect on next navigation)
3. Set isInitialized = true
```

### Theme System

- `ThemeProvider` from `next-themes` writes `data-theme="dark"` or `data-theme="light"` to `<html>`.
- All colors are CSS custom properties in `globals.css` scoped to `[data-theme="dark"]` and `[data-theme="light"]`.
- Example variables: `--surface-base`, `--surface-raised`, `--accent`, `--text-primary`, `--border`.

---

## 7. Authentication Flow

**File**: `src/stores/useAuthStore.js`

### State Shape

```js
{
  user: null | { id, username, email },
  isAuthenticated: false,
  isLoading: false,
  isInitialized: false,        // Has initAuth() completed?
  // NOTE: accessToken is stored in module-level _accessTokenRef, NOT in store state
  //       This avoids stale closures and Zustand serialization issues
}
```

### Key Functions

#### `login(email, password)`
```
POST /auth/login
  → HTTP-only cookie: refresh_token (7 days)
  → JSON body: { access_token, expires_at }
  → setAccessToken(token), setUser(user), scheduleRefresh(expiresAt)
```

#### `signup(username, email, password)`
```
POST /auth/register
  → HTTP-only cookie: refresh_token
  → JSON: { access_token, user, expires_at }
  → same as login flow
```

#### `logout()`
```
POST /auth/logout (sends refresh cookie for server-side invalidation)
  → clearAuth() → clearAccessToken()
  → router.push('/auth')
```

#### `scheduleRefresh(expiresAt)`
```
TOKEN_REFRESH_INTERVAL = 13 minutes (tokens expire at 15 min)
setTimeout fires 2 min before expiry:
  → calls _refreshToken()
  → on success: scheduleRefresh(newExpiresAt)   [recursive scheduling]
  → on failure: retry 3× with backoff (2s, 4s, 8s)
  → after 3 failures: _handleSessionExpiry() → redirect to /auth?reason=expired
```

#### Token Storage Strategy
```
_accessTokenRef (module-level variable, not in Zustand state)
   ↕ synchronized via setAccessToken() / clearAccessToken()
lib/api/config.js reads: getAccessToken() → _accessTokenRef.current
```

This module-level storage prevents React re-renders on every API call while still being accessible from anywhere.

---

## 8. API Layer (`lib/api/`)

### `config.js` — Core `apiFetch()`

The single entry point for all authenticated API calls:

```
apiFetch(path, options) flow:
1. getAccessToken() → attach as Authorization: Bearer <token>
2. fetch(`${API_BASE_URL}${path}`, options)
3. If response.status === 401:
   a. _refreshTokenOnce() — deduped via _refreshPromise (parallel 401s share one refresh)
   b. On success: retry original request with new token
   c. On failure: _handleSessionExpiry() → redirect /auth?reason=expired
4. Return response (JSON parsing left to caller)
```

**Constants:**
```js
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
```

### All API Modules

#### `auth.js`
```js
login(email, password)          → POST /auth/login
register(username, email, pass)  → POST /auth/register  
refresh()                        → POST /auth/refresh
logout()                         → POST /auth/logout
getCurrentUser()                 → GET  /auth/me
```

#### `chat.js`
```js
sendChat(notebookId, sessionId, message, sourceIds, intentOverride)
  → POST /chat/{notebookId}/stream   (returns raw Response for SSE reading)
  → Body: { session_id, message, source_ids, intent_override }

getSessions(notebookId)          → GET  /chat/{notebookId}/sessions
getHistory(notebookId, sessionId)→ GET  /chat/{notebookId}/{sessionId}/history
deleteSession(notebookId, sid)   → DELETE /chat/{notebookId}/{sessionId}
getSuggestions(notebookId, msg)  → GET  /chat/{notebookId}/suggestions?message=...
```

#### `materials.js`
```js
uploadFiles(notebookId, files, onProgress)   → POST /upload/{notebookId} (multipart)
uploadURL(notebookId, url)                   → POST /upload/{notebookId}/url
getMaterials(notebookId)                     → GET  /materials/{notebookId}
deleteMaterial(materialId)                   → DELETE /materials/{materialId}
renameMaterial(materialId, name)             → PATCH /materials/{materialId}
```

#### `notebooks.js`
```js
getNotebooks()                    → GET  /notebooks/
createNotebook(name)              → POST /notebooks/
renameNotebook(id, name)          → PATCH /notebooks/{id}
deleteNotebook(id)                → DELETE /notebooks/{id}
```

#### `generation.js`
```js
generateFlashcards(notebookId, sourceIds, options)  → POST /flashcards/generate
generateQuiz(notebookId, sourceIds, options)        → POST /quiz/generate
generatePresentation(notebookId, sourceIds, options)
  → POST /presentation/async          (returns { job_id })
  → pollJob(job_id, 3s interval)      → GET /jobs/{job_id}
  → max 10 min timeout
  → returns job.result (presentation HTML slides)
```

#### `mindmap.js`
```js
generateMindMap(notebookId, sourceIds, message)  → POST /mindmap/generate/{notebookId}
saveMindMap(notebookId, nodes, edges)            → POST /mindmap/save/{notebookId}
getMindMap(notebookId)                           → GET  /mindmap/{notebookId}
```

#### `podcast.js`
```js
generateScript(notebookId, sourceIds, mode, topic?)  → POST /podcast/generate-script
generateAudio(scriptId, voice1, voice2)               → POST /podcast/generate-audio
getSession(sessionId)              → GET  /podcast/sessions/{sessionId}
getSessions(notebookId)            → GET  /podcast/sessions?notebook_id=...
deleteSession(sessionId)           → DELETE /podcast/sessions/{sessionId}
```

#### `jobs.js`
```js
pollJob(jobId, intervalMs=3000, maxWaitMs=600000)
  → GET /jobs/{jobId} every intervalMs until status ∈ {completed, failed}
  → rejects on timeout or failure
  → returns complete job object on success
```

---

## 9. SSE Streaming (`lib/stream/`)

### `client.js` — `StreamClient`

The `StreamClient` reads a raw `fetch` Response's `ReadableStream` and dispatches typed events.

```
StreamClient {
  _handlers: Map<eventType, handler[]>

  on(eventType, handler)    → register handler for event type
  off(eventType, handler)   → remove handler
  connect(response)         → start reading the stream

  connect(response) logic:
    reader = response.body.getReader()
    decoder = new TextDecoder()
    buffer = ''
    currentEvent = null

    loop: read chunk from reader
      → decode bytes → append to buffer
      → split on '\n'
      → for each line:
          'event: <type>' → currentEvent = type
          'data: <json>'  → parse JSON → dispatch(currentEvent || 'message', data)
          ''  (blank line) → reset currentEvent (SSE spec: blank line = event boundary)
      → continue until done=true
}
```

**Event types dispatched:**
`token` · `meta` · `blocks` · `step` · `artifact` · `code_block` · `summary` · `agent_start` · `tool_start` · `tool_result` · `web_start` · `web_sources` · `research_start` · `research_phase` · `error` · `done`

### `state.js` — `StreamState`

Accumulates all streaming events into a single state object. Used by `useChat.js` hook to build React state from SSE events.

```js
class StreamState {
  // Core
  isStreaming: bool
  currentContent: string       // accumulated token text
  metadata: {}
  blocks: []                   // response blocks (code, text, etc.)

  // Progress
  steps: []
  currentStep: { tool, status }

  // Agent-specific
  agentPlan: null | { steps[], intent }
  agentSteps: []
  agentActiveStep: null
  agentSummary: null

  // Code execution
  codeBlock: null | { language, code, output?, error? }

  // Web search
  webSearchStatus: 'idle' | 'searching' | 'reading' | 'done'
  webSources: []

  // Research
  researchStatus: 'idle' | 'running' | 'done'
  researchIteration: number
  researchPhase: string
  researchSources: []

  handleEvent(eventType, data)  // dispatches to correct field updates
}
```

---

## 10. State Management — All 10 Zustand Stores

### Store Overview

| Store | File | Purpose |
|---|---|---|
| `useAuthStore` | `useAuthStore.js` | User, tokens, refresh scheduling |
| `useAppStore` | `useAppStore.js` | Global hub that re-exports all stores |
| `useChatStore` | `useChatStore.js` | Chat messages, sessions, streaming state |
| `useMaterialStore` | `useMaterialStore.js` | Materials list, source selection |
| `useNotebookStore` | `useNotebookStore.js` | Notebooks list, current notebook |
| `useUIStore` | `useUIStore.js` | Panel sizes, sidebar open, active panel |
| `usePodcastStore` | `usePodcastStore.js` | Podcast phase, script, audio state |
| `useAgentStore` | `useAgentStore.js` | Agent execution steps, artifacts |
| `useToastStore` | `useToastStore.js` | Toast notification queue |
| `useConfirmStore` | `useConfirmStore.js` | Confirm modal state |

---

### `useAuthStore`

```js
State:
  user: null | { id, username, email }
  isAuthenticated: boolean
  isLoading: boolean
  isInitialized: boolean  // initAuth completed?

Actions:
  initAuth()               // called once on app mount in AuthInitializer
  login(email, password)
  signup(username, email, password)
  logout()
  setUser(user)
  clearAuth()
  scheduleRefresh(expiresAt)

Module-level (NOT in state):
  _accessTokenRef = { current: null }
  _initPromise    = null   // prevents concurrent initAuth() calls
```

---

### `useChatStore`

```js
State:
  messages: Message[]       // { id, role, content, citations, slashCommand, timestamp }
  sessionId: string | null
  isStreaming: boolean
  abortController: AbortController | null
  pendingChatMessage: null | string  // message waiting for notebook creation

Actions:
  addMessage(role, content, extra?)      // returns new message
  updateLastMessage(updater)             // mutate last message in-place
  setMessages(messagesOrUpdater)
  clearMessages()
  setSessionId(id)
  setStreaming(bool)
  setAbortController(controller)
  setPendingChatMessage(msg)
```

---

### `useMaterialStore`

```js
State:
  materials: Material[]
  currentMaterial: Material | null
  selectedSources: string[]   // array of material IDs (not Set — for serializability)

Actions:
  setMaterials(arr | updater)
  addMaterial(material)
  updateMaterial(id, updates)     // status updates from WebSocket
  removeMaterial(id)
  setCurrentMaterial(material)
  toggleSourceSelection(id)       // add/remove from selectedSources
  selectAllSources()
  deselectAllSources()
  setSelectedSources(arr | updater)
  isSourceSelected(id)            // selector (not a subscription)
```

---

### `useNotebookStore`

```js
State:
  notebooks: Notebook[]
  currentNotebook: Notebook | null
  isDraftMode: boolean   // true when URL is /notebook/new or notebook not yet saved

Actions:
  setNotebooks(arr)
  setCurrentNotebook(notebook)
  addNotebook(notebook)
  updateNotebook(id, updates)
  removeNotebook(id)
  setDraftMode(bool)
```

---

### `useUIStore`

```js
State:
  sidebarOpen: boolean           // mobile overlay sidebar
  activePanel: 'chat' | 'studio' | 'both'
  sidebarWidth: number           // px (default: 320)
  studioWidth: number            // px (default: 360)

Actions:
  toggleSidebar()
  setActivePanel(panel)
  setSidebarWidth(px)
  setStudioWidth(px)
```

---

### `usePodcastStore`

```js
State:
  phase: 'idle' | 'library' | 'mode-select' | 'generating' | 'player'
  sessions: PodcastSession[]
  currentSession: null | PodcastSession
  script: null | { segments[], chapters, title }
  isGeneratingScript: boolean
  isGeneratingAudio: boolean
  audioUrl: null | string
  progress: number   // 0-100 for audio generation

Actions:
  setPhase(phase)
  setSessions(arr)
  setCurrentSession(session)
  setScript(script)
  setIsGeneratingScript(bool)
  setIsGeneratingAudio(bool)
  setAudioUrl(url)
  setProgress(n)
  reset()
```

---

### `useAgentStore`

```js
State:
  isRunning: boolean
  executionLog: AgentExecutionLog | null
  steps: AgentStep[]
  artifacts: Artifact[]
  activeStepIndex: number

Actions:
  setIsRunning(bool)
  setExecutionLog(log)
  setSteps(steps)
  addArtifact(artifact)
  setActiveStepIndex(n)
  reset()
```

---

### `useToastStore`

```js
State:
  toasts: Toast[]   // { id, type, message, duration }

Actions:
  addToast(type, message, duration?)
  removeToast(id)

// useToast() hook:
  toast.success(msg), toast.error(msg), toast.info(msg), toast.warning(msg)
  // Auto-removes after TIMERS.TOAST_DURATION (2500ms)
```

---

### `useConfirmStore`

```js
State:
  isOpen: boolean
  title: string
  message: string
  onConfirm: () => void
  onCancel: () => void

Actions:
  openConfirm({ title, message, onConfirm, onCancel? })
  closeConfirm()

// useConfirm() hook: returns a Promise-based confirm() function
```

---

### `useAppStore` — Global Hub

`useAppStore` re-exports from all specialized stores, acting as a single import point for components that need multiple stores:

```js
// Components can do:
const { currentNotebook, materials, messages, isStreaming } = useAppStore(s => ({
  currentNotebook: s.currentNotebook,
  materials: s.materials,
  messages: s.messages,
  isStreaming: s.isStreaming,
}));
// useAppStore internally delegates to the appropriate sub-store
```

---

## 11. Dashboard / Home Page

**File**: `src/app/page.jsx`

### State & Data Flow

```
On mount:
  1. useNotebookStore.setNotebooks(await getNotebooks())
  2. Display grid of notebook cards

User creates notebook:
  POST /notebooks/ → addNotebook(result) → router.push(`/notebook/${result.id}`)

User opens notebook:
  router.push(`/notebook/${id}`)

User renames notebook:
  PATCH /notebooks/{id} → updateNotebook(id, { name })

User deletes notebook:
  useConfirm() dialog → DELETE /notebooks/{id} → removeNotebook(id)
```

### UI Structure

```
/page.jsx
└── Dashboard
    ├── Header (nav: KeplerLab logo, theme toggle, user menu)
    ├── Hero section: "Your AI Study Notebooks"
    ├── Create Notebook button
    └── Notebook Grid
        └── NotebookCard × N
            ├── Name (editable on double-click)
            ├── Material count, Last updated
            ├── Open / Delete actions
            └── Hover: edit/delete icon buttons
```

---

## 12. Notebook Workspace Page

**File**: `src/app/notebook/[id]/page.jsx`

The main application workspace. Handles draft mode (new notebook) and loads the 3-panel layout.

### Lifecycle

```
1. params.id === 'new'? → set draft mode = true, skip notebook load
   params.id is UUID? → fetchNotebook(id) → setCurrentNotebook(result)
                       → fetchMaterials(id) → setMaterials(result)

2. Render:
   ┌──── Header ────────────────────────────────────────────┐
   │              KeplerLab | [Notebook Name]                │
   ├─ Sidebar ─┬─────── ChatPanel ────────┬─ StudioPanel ───┤
   │  Materials│  Chat / Agent / Research  │  Flashcards     │
   │  Sources  │  Streaming output         │  Quiz           │
   │           │  Code execution view      │  Presentation   │
   │           │                           │  Podcast        │
   │           │                           │  Mind Map       │
   └───────────┴───────────────────────────┴─────────────────┘

3. Panel widths managed by useUIStore:
   - Sidebar: 320px default, 260–600px range (drag-resize)
   - StudioPanel: 360px default, 260–600px range (drag-resize)
   - ChatPanel: fills remaining flex space

4. Mobile (<768px): Sidebar hidden by default, toggled via Header menu button
   → sidebarOpen controlled by useUIStore.toggleSidebar()
```

### Error Handling

```jsx
<PanelErrorBoundary panelName="Chat">
  <ChatPanel />
</PanelErrorBoundary>
```

Each panel is wrapped in an `ErrorBoundary` so a crash in one panel doesn't down the whole workspace.

### Draft Mode

When a user uploads a file or sends a chat with no notebook (draft mode):
1. `useMaterialStore.setPendingUpload(file)` or `useChatStore.setPendingChatMessage(msg)` stores the intended action.
2. `POST /notebooks/` creates a real notebook.
3. The pending action is replayed.
4. URL is updated to `/notebook/{newId}` via `window.history.replaceState`.

---

## 13. Sidebar Component

**File**: `src/components/layout/Sidebar.jsx`

The left panel manages all document ingestion and source selection.

### Features

| Feature | Mechanism |
|---|---|
| File upload (drag & drop) | `<input type="file">` + `onDragOver/onDrop` → `uploadFiles()` |
| Batch upload | Multiple files selected → sequential or parallel `uploadFiles()` |
| URL indexing | Input of web URL → `uploadURL()` → job queued |
| Source toggling | `toggleSourceSelection(id)` in `useMaterialStore` |
| Real-time status | WebSocket via `useMaterialUpdates()` hook |
| Fallback polling | `setInterval(fetchMaterials, 8000)` when any material is `processing` |
| Auto-create notebook | On first upload in draft mode: creates notebook, then uploads |

### Material Status Colors / Icons

```
pending       → gray spinner
processing    → blue pulsing
ocr_running   → blue scanner icon
transcribing  → purple microphone icon
embedding     → amber brain icon
completed     → green checkmark
failed        → red X icon
```

### Upload Flow

```
User drops files
  → validateFileTypes(files)   (pdf, docx, xlsx, csv, mp3, mp4, txt, md, jpg, png)
  → if draft mode: createNotebook() first
  → for each file: uploadFiles(notebookId, [file], progressCallback)
    → POST /upload/{notebookId} multipart
    → addMaterial({ id, name, status: 'pending', ... })
  → WebSocket / polling updates status until 'completed'
```

### WebSocket Integration

`useMaterialUpdates(notebookId)` hook:
- Connects to `ws://localhost:8000/ws/jobs/{userId}?token=<accessToken>` (falls back to first-message auth)
- On `material_update` message: `updateMaterial(id, { status, ... })`
- On `material_completed`: triggers auto-refresh of embeddings count
- Reconnects with exponential backoff (1s → 30s max) on disconnect

---

## 14. Header Component

**File**: `src/components/layout/Header.jsx`

Fixed 52px top bar rendered inside the notebook workspace.

### Elements

```
Left:
  ← (back button if onBack prop) | KeplerLab logo | Divider | BookOpen | Notebook name

Right:
  Sun/Moon theme toggle | Share button | Help button | User avatar button
                                                              └─ Dropdown menu:
                                                                  Settings (coming soon)
                                                                  Logout
```

### User Menu Behavior

- Click avatar → show dropdown menu (anchored via `useRef` + `mousedown` outside detection)
- Logout → `useAuthStore.logout()` → `router.replace('/auth')`

---

## 15. ChatPanel Component

**File**: `src/components/chat/ChatPanel.jsx`

The most complex component — manages chat sessions, message history, streaming state, and all intent modes.

### Internal State

```js
// Streaming output state
streamingContent        // accumulated token text
isThinking              // awaiting first token
stepLog                 // finalized tool steps
liveStepLog             // in-progress steps (updates during streaming)

// Agent mode
agentPlan               // { steps, intent }
liveAgentSteps          // agent steps as they execute
liveAgentArtifacts      // generated files/charts

// Code mode
codeBlock               // { language, code, output, error }

// Web search mode
webSearchStatus         // 'idle' | 'searching' | 'reading' | 'done'
webSources              // [ { title, url, snippet } ]

// Research mode
researchPhase           // 'searching' | 'analyzing' | 'writing'
researchSources         // []

// UI
sessions []             // all chat sessions for this notebook
```

### Session Management

```
On notebook change (useEffect):
  1. getSessions(notebookId) → setSessions()
  2. if sessions.length > 0: load latest session history
     getHistory(notebookId, session.id) → setMessages(history)
     setSessionId(session.id)

User clicks session in list → load that session's history

New session button → clearMessages() + setSessionId(null)
```

### Message Send Flow

```
handleSend(message, intentOverride, command):
  1. addMessage('user', message, { slashCommand: command })
  2. setStreaming(true), setThinking(true)
  3. abortController = new AbortController()
  4. response = await sendChat(notebookId, sessionId, message, selectedSources, intentOverride)
  5. StreamClient.connect(response)
  6. Handle SSE events:
     token      → append to streamingContent
     meta       → setSessionId(meta.session_id) if new
     step       → update liveStepLog
     agent_start→ setAgentPlan(data.plan)
     tool_start → update liveAgentSteps (mark step active)
     tool_result→ update liveAgentSteps (mark step done), add artifacts
     web_start  → setWebSearchStatus('searching')
     web_sources→ setWebSources(data.sources)
     research_* → update research phase/sources
     code_block → setCodeBlock(data)
     artifact   → addArtifact(data) → liveAgentArtifacts
     summary    → set final agent summary
     error      → addMessage('assistant', errorText)
     done       → finalize:
                   addMessage('assistant', streamingContent, { citations })
                   clearStreamingState()
                   setStreaming(false)
```

### Slash Commands

Defined in `slashCommands.js`:

| Command | Intent | Description |
|---|---|---|
| `/agent` | `AGENT` | Full multi-step AI agent with tool use |
| `/research` | `WEB_RESEARCH` | Deep web research with 5-step pipeline |
| `/code` | `CODE_EXECUTION` | Python code generation + sandbox execution |
| `/web` | `WEB_SEARCH` | Quick web search |

`parseSlashCommand(text)` — extracts command prefix from message text, returns `{ command, remainingMessage }`.

### Chat Quick Actions

```js
QUICK_ACTIONS = [
  { id: 'summarize',   label: 'Summarize',   icon: '📝' },
  { id: 'explain',     label: 'Explain',     icon: '💡' },
  { id: 'keypoints',   label: 'Key Points',  icon: '🎯' },
  { id: 'studyguide',  label: 'Study Guide', icon: '📚' },
]
```

Clicking a quick action sends `message = action.label` with no intent override → defaults to RAG.

### Message Rendering

Each message in `ChatMessageList.jsx` renders:
- **User messages**: Bubble with text + optional slash command badge
- **Assistant messages**:
  - `react-markdown` with plugins: `remark-gfm`, `remark-math`, `rehype-katex`, `rehype-raw`
  - Code blocks: `react-syntax-highlighter` (Prism styles)  
  - Citations: `[SOURCE N]` patterns linked to source names
  - Agent view: step log, artifacts with download links, final summary
  - Code view: code panel + execution output/error + generated charts (base64 img)
  - Research view: phase tracker, sources list (RESEARCH_STEPS_TEMPLATE)
  - Web search: sources grid with snippets

---

## 16. ChatInputArea Component

**File**: `src/components/chat/ChatInputArea.jsx`

### Features

```
textarea (auto-resize, max 120px)
  → onChange: detect '/' at start → show SlashCommandDropdown
  → onKeyDown: Enter (no shift) → handleSend()
  → onKeyDown: Escape → dismiss slash dropdown / clear active command

SlashCommandDropdown:
  Shows when inputValue starts with '/'
  Filters commands by text after '/'
  Arrow keys to navigate, Enter to select
  On select: setActiveCommand(cmd) + clear input prefix

ActiveCommand pill (CommandBadge):
  Shows selected command (e.g., "AGENT" badge)
  × button to clear active command

Send/Stop button:
  isStreaming? → Square icon → calls onStop (abort stream)
  else → Send icon → calls handleSend()

Suggestion button (Sparkles):
  onClick → getSuggestions(notebookId, lastMessage) → show SuggestionDropdown
  Suggestions are question strings; clicking one populates input

AI Research button (FlaskConical):
  Shows when no active command and input has text
  onClick → onResearch(inputValue) → triggers /research flow

Mind Map banner:
  Shows when mindMapBanner prop is truthy
  "Continue with: <query from mind map>" → dismiss (onDismissBanner)
```

### Input Validation

```
disabled = !notebookId || isSourceProcessing
hasSource check: shows warning toast if no sources selected when sending (for RAG mode)
INPUT_LENGTH_WARNING (1800 chars): shows character count warning
```

---

## 17. StudioPanel Component

**File**: `src/components/studio/StudioPanel.jsx`

The right panel that hosts all AI content generation features.

### Feature Cards

```
Flashcards → FlashcardConfigDialog → generateFlashcards() → InlineFlashcardsView
Quiz       → QuizConfigDialog → generateQuiz() → InlineQuizView
Slides     → PresentationConfigDialog → generatePresentation() (async job) → InlinePresentationView
Mind Map   → MindMapConfigDialog → generateMindMap() → MindMapCanvas (dynamic import)
Podcast    → PodcastStudio (dynamic import)
Explainer  → ExplainerConfigDialog → generateExplainer() (async job)
```

### Content History

```
Generated content is persisted in the DB as GeneratedContent records.
On panel open: fetchContentHistory(notebookId) → list of past generations
History item click → re-display past content (slides, flashcards, etc.)
Rename: PATCH /content/{id}
Delete: DELETE /content/{id}
```

### Async Job Pattern (Presentation, Explainer)

```
1. POST /presentation/async → { job_id }
2. Show loading spinner
3. pollJob(job_id, 3000ms, 600000ms) — poll every 3s, max 10 min
   ├── Pending: continue polling
   ├── Completed: job.result contains presentation data
   └── Failed: show error toast
4. Display result in InlinePresentationView
```

### In-Slide Preview (InlinePresentationView)

Uses `<iframe srcDoc={slideHtml} />` to safely render each slide's standalone HTML (1920×1080 logical size) scaled down via CSS `transform: scale()`.

### Lazy Loading Strategy

```js
const PodcastStudio = dynamic(() => import('@/components/podcast/PodcastStudio'), {
  loading: () => <LoadingSpinner />,
  ssr: false,
});
const MindMapCanvas = dynamic(() => import('@/components/mindmap/MindMapCanvas'), {
  loading: () => <LoadingSpinner />,
  ssr: false,
});
```

Heavy components are not loaded until the user activates that feature.

---

## 18. Presentation Feature

**File**: `src/components/presentation/PresentationView.jsx`

### Slide Rendering

```
Backend returns: { slides: [{ html: string }, ...] }
Each slide is a standalone HTML document (<!DOCTYPE html>...) at 1920×1080px

PresentationView:
├── useSlideScale hook
│   └── ResizeObserver on container → scale = containerWidth / 1920
├── Slide navigation (prev/next buttons, keyboard: ArrowLeft/Right)
├── Overview mode: thumbnail grid (all slides scaled to ~200px wide)
├── Fullscreen mode: native browser fullscreen API
└── Current slide: <iframe srcDoc={slide.html} /> × 1
    → CSS transform: scale(scale) applied to wrapper
    → pointer-events: none (non-interactive during view)
```

### `InlinePresentationView` (inside StudioPanel)

Compact version: smaller iframe embed with "Open full view" button that opens `PresentationView` in a modal overlay.

---

## 19. Podcast Studio Feature

**File**: `src/components/podcast/PodcastStudio.jsx`

### Phase State Machine

```
idle
  └─ "New Podcast" button → library
library
  ├─ Load existing sessions: getSessions(notebookId)
  ├─ Click existing session → player (load audio)
  └─ "Create New" button → mode-select
mode-select
  └─ User selects: overview | deep-dive | debate | q-and-a | full | topic
                   (topic mode requires topic input)
  └─ "Generate" → generating
generating
  ├─ Step 1: generateScript(notebookId, sourceIds, mode, topic?)
  │   → POST /podcast/generate-script (streaming or batch)
  │   → shows segment preview as script is built
  ├─ Step 2: generateAudio(scriptId, voice1, voice2)
  │   → POST /podcast/generate-audio
  │   → WebSocket progress updates (usePodcastWebSocket)
  │   → progress bar 0%→100%
  └─ On complete → player
player
  ├─ Audio player (HTML5 <audio> with custom controls)
  ├─ Chapter markers (click to jump)
  ├─ Script panel (scrolling transcript synced to playback)
  ├─ Q&A mid-playback: ask question → RAG answer without leaving player
  └─ Export: download MP3, view script
```

### Voice Assignment

Default voices: Voice 1 = Host (en-US-JennyNeural), Voice 2 = Guest (en-US-GuyNeural) — edge-tts voices. Configurable in mode-select step.

---

## 20. Mind Map Feature

**File**: `src/components/mindmap/MindMapCanvas.jsx`

### Rendering

- Uses `@xyflow/react` (ReactFlow v12) for interactive node/edge canvas.
- `dagre` performs automatic hierarchical layout: `rankdir: 'LR'` (left-to-right), `nodeSep: 60`, `rankSep: 120`.
- Node types: `root` (centered, accent color), `branch` (primary topic), `leaf` (subtopic).

### Generation Flow

```
1. User clicks "Generate Mind Map" in StudioPanel
2. MindMapConfigDialog: choose sources, topic (optional)
3. POST /mindmap/generate/{notebookId}
   → backend: RAG query → LLM JSON: { title, nodes: [{id, label, parent?}] }
4. Frontend: build ReactFlow node/edge arrays from JSON
5. dagre.layout() → assign x,y positions
6. Render: <ReactFlow nodes={} edges={} />
```

### Interactivity

```
Drag nodes: reposition (useNodesState)
Click node → expand/collapse children
Zoom/Pan: built-in ReactFlow controls
Export PNG: html-to-image → download
Export PDF: jspdf → add PNG → save PDF
Chat Bridge: click a node → sets mindMapBanner in ChatPanel
  → "Tell me more about [node label]" prefill
```

---

## 21. Hooks Reference

### `useChat.js`

Wraps `StreamClient` + `StreamState`, provides `sendChat()` function and all streaming state to `ChatPanel`.

```js
const {
  send,               // (message, intentOverride) => Promise
  stop,               // abort current stream
  isStreaming,        // bool
  content,            // accumulated text
  steps,              // tool call steps
  agentPlan,          // agent execution plan
  agentSteps,         // agent steps
  artifacts,          // generated files
  codeBlock,          // code execution block
  webSources,         // web search results
  researchPhase,      // current research phase
  error,              // stream error
} = useChat(notebookId);
```

### `useMaterialUpdates.js`

Maintains a WebSocket connection for real-time material processing updates.

```js
useMaterialUpdates(notebookId):
  Effect: connect WebSocket when notebookId changes
  Auth: send { type: 'auth', token: getAccessToken() } on open
  On message:
    type === 'material_update'   → updateMaterial(id, status)
    type === 'material_completed'→ updateMaterial(id, { status: 'completed' })
    type === 'ping'              → send { type: 'pong' }
  On close: exponential backoff reconnect
    delays: 1s → 2s → 4s → 8s → 16s → 30s (max)
  Cleanup: ws.close() on unmount or notebookId change
```

### `useResizablePanel.js`

Provides drag-to-resize for Sidebar and StudioPanel.

```js
const { width, handleMouseDown } = useResizablePanel({
  defaultWidth: 320,
  minWidth: 260,
  maxWidth: 600,
  side: 'left' | 'right',
  onWidthChange: (w) => setStoreWidth(w),
});
```

Attaches `mousemove`/`mouseup` to `document` during drag for smooth resize.

### `usePodcast.js`

Orchestrates podcast generation:
```
generatePodcast({ notebookId, sourceIds, mode, topic, voice1, voice2 })
  → setPhase('generating')
  → generateScript() → setScript()
  → generateAudio() → ws updates → setAudioUrl()
  → setPhase('player')
```

### `usePodcastWebSocket.js`

WebSocket connection specific to podcast audio generation. listens for `genaudio_progress` events with `{ percent, current_segment, total_segments }`.

### `useMicInput.js`

Wraps `navigator.mediaDevices.getUserMedia` + `MediaRecorder` for recording user audio (used in Podcast Q&A and Explainer features). Returns `{ isRecording, startRecording, stopRecording, audioBlob }`.

---

## 22. Constants & Utilities

### `lib/utils/constants.js`

```js
// Panel resize limits
PANEL.SIDEBAR  = { DEFAULT_WIDTH: 320, MIN_WIDTH: 260, MAX_WIDTH: 600 }
PANEL.STUDIO   = { DEFAULT_WIDTH: 360, MIN_WIDTH: 260, MAX_WIDTH: 600 }

// Presentation logical dimensions
SLIDE          = { WIDTH: 1920, HEIGHT: 1080 }

// Mind Map layout
MINDMAP        = { NODE_SEP: 60, RANK_SEP: 120, NODE_WIDTH: 160, NODE_HEIGHT: 40 }

// Timers
TIMERS = {
  TOAST_DURATION: 2500,            // 2.5s
  TOKEN_REFRESH_INTERVAL: 780000,  // 13 minutes
  WS_MAX_BACKOFF: 30000,           // 30s max WS reconnect delay
  INPUT_LENGTH_WARNING: 1800       // chars before showing length warning
}

// Quick action prompts
QUICK_ACTIONS = [
  { id: 'summarize', label: 'Summarize',   icon: '📝' },
  { id: 'explain',   label: 'Explain',     icon: '💡' },
  { id: 'keypoints', label: 'Key Points',  icon: '🎯' },
  { id: 'studyguide',label: 'Study Guide', icon: '📚' },
]

// Research phase labels
RESEARCH_STEPS_TEMPLATE = [
  { label: 'Understanding query',  status: 'pending' },
  { label: 'Searching sources',    status: 'pending' },
  { label: 'Analyzing results',    status: 'pending' },
  { label: 'Cross-referencing',    status: 'pending' },
  { label: 'Writing report',       status: 'pending' },
]
```

### `lib/utils/helpers.js`

```js
generateId()           // crypto.randomUUID() or Math.random() fallback
formatFileSize(bytes)  // "1.2 MB", "456 KB", etc.
truncate(str, max)     // truncate with ellipsis
debounce(fn, delay)
classNames(...args)    // conditional classname joining (like clsx)
```

---

## 23. Complete Data Flow Diagrams

### 23.1 App Initialization Flow

```
Browser loads /notebook/abc123
  │
  ▼ Next.js middleware.js (Edge)
  Check: cookies.get('refresh_token') exists?
  ├─ NO  → redirect /auth?redirect=/notebook/abc123
  └─ YES → NextResponse.next()

  ▼ layout.jsx renders
  ThemeProvider wraps app
  AuthInitializer.useEffect() fires

  ▼ useAuthStore.initAuth()
  POST /auth/refresh (cookie sent automatically)
  ├─ 401 → clearAuth() → middleware will redirect on next navigation
  └─ 200 → { access_token, expires_at }
      setAccessToken(token)        // _accessTokenRef.current = token
      GET /auth/me → setUser(user)
      setIsAuthenticated(true)
      scheduleRefresh(expires_at)  // setTimeout for 13 min

  ▼ page.jsx: /notebook/[id]/page.jsx renders
  fetchNotebook(id) → setCurrentNotebook()
  fetchMaterials(id) → setMaterials()
  ─────────────────────────────────────────
  Workspace displays with materials loaded
```

### 23.2 File Upload + Real-Time Status

```
User drops PDF on Sidebar
  │
  ▼ onDrop handler
  validateFileType(file)       // check MIME type whitelist
  if draftMode:
    POST /notebooks/ → createNotebook() → router replaceState to /notebook/{id}
  POST /upload/{notebookId}    // multipart/form-data
    Content-Type: multipart/form-data
    Body: file blob
    → returns { material: { id, name, status: 'pending' } }
  addMaterial({ id, name, status: 'pending' }) → Sidebar shows spinner
  │
  ▼ Background: Backend worker picks up job
  status: pending → processing → ocr_running → embedding → completed
  ─── each status change ───────────────────────────────────────────
  ▼ useMaterialUpdates WebSocket
  receive: { type: 'material_update', id, status }
  updateMaterial(id, { status })    // Sidebar icon updates live
  ─────────────────────────────────────────────────────
  Final: status = 'completed' → green checkmark
  Material now selectable as RAG source
```

### 23.3 Chat Message + RAG Streaming

```
User types message, selects sources, clicks Send
  │
  ▼ ChatPanel.handleSend()
  addMessage('user', text) → render user bubble immediately
  setStreaming(true), setThinking(true)
  abortController = new AbortController()
  │
  ▼ sendChat(notebookId, sessionId, text, selectedSources, intentOverride)
  POST /chat/{notebookId}/stream
  Body: {
    session_id: sessionId | null,
    message: text,
    source_ids: [id1, id2],        // empty = all sources or notebook-wide search
    intent_override: null          // 'AGENT' | 'WEB_RESEARCH' | 'CODE_EXECUTION' | null
  }
  Returns: ReadableStream (SSE)
  │
  ▼ StreamClient.connect(response)
  Reads chunks, splits on '\n\n' event boundaries
  Dispatches events to handlers:

  event: token  data: {"content": "The "}
    → streamingContent += "The "        → React re-render shows typing
  event: token  data: {"content": "answer is..."}
    → streamingContent += "answer is..."
  event: meta   data: {"session_id": "xyz", "intent": "RAG"}
    → setSessionId("xyz")
  event: done   data: {}
    → addMessage('assistant', streamingContent, { citations })
    → clearStreamingContent()
    → setStreaming(false), setThinking(false)
  ─────────────────────────────────────────────────────
  Final: AssistantMessage renders with markdown + citation badges
```

### 23.4 Agent Flow Streaming

```
User selects /agent command → sends "analyze this data"

POST /chat/{id}/stream  body: { intent_override: 'AGENT', ... }
  │
  ▼ SSE Events received:
  event: agent_start
  data: {"plan": {"steps": ["Load data", "Analyze", "Visualize"], "intent": "ANALYSIS"}}
    → setAgentPlan(plan) → show AgentPlan UI in ChatPanel

  event: tool_start  data: {"tool": "rag_tool", "step": 0, "query": "..."}
    → liveAgentSteps[0].status = 'running' → step card shows spinner

  event: step  data: {"tool": "rag_tool", "status": "done", "preview": "Found 5 chunks"}
    → liveAgentSteps[0].status = 'done' → step card shows checkmark

  event: code_block  data: {"language": "python", "code": "import pandas..."}
    → setCodeBlock({ code, language })

  event: step  data: {"tool": "python_tool", "status": "running"}
    → step 1 spinner

  event: artifact  data: {"type": "image", "url": "/output/chart.png", "name": "bar_chart"}
    → liveAgentArtifacts.push(artifact) → thumbnail shows in artifact panel

  event: token (repeated)
    → streaming final summary text

  event: summary  data: {"content": "Analysis complete..."}
    → set agentSummary → displayed in summary section

  event: done
    → addMessage('assistant', content, { agentLog, artifacts })
    → full agent execution log saved to DB via backend AgentExecutionLog
```

### 23.5 Presentation Async Job Flow

```
User clicks "Generate Presentation" in StudioPanel
  │
  ▼ PresentationConfigDialog
  User selects: style, sources, slide count
  Clicks Generate

  ▼ generatePresentation(notebookId, sourceIds, { style, count })
  POST /presentation/async
    → { job_id: "abc-123" }
  setIsLoading(true) → show spinner

  ▼ pollJob("abc-123", 3000ms, 600000ms)
  loop: GET /jobs/abc-123 every 3s
  ├─ { status: 'pending' | 'processing' } → continue polling
  ├─ { status: 'completed', result: { slides: [...], title: "..." } } → break
  └─ { status: 'failed', error: "..." } → throw error

  ▼ On completed:
  setPresentationData(result)     // usePodcastStore or local state
  setIsLoading(false)
  Show InlinePresentationView
    ├─ Slide 1: <iframe srcDoc={slide.html} style="transform: scale(0.28)" />
    ├─ Prev / Next buttons
    └─ "Open Full View" → opens PresentationView modal
         → Full 1:1 rendering with keyboard nav (←/→)
```

### 23.6 Token Refresh Cycle

```
App startup:
  initAuth() → refresh token → scheduleRefresh(expires_at)

Time = T+0:00: access token issued, expires in 15 min
Time = T+13:00: setTimeout fires (TIMERS.TOKEN_REFRESH_INTERVAL)
  _refreshToken():
    POST /auth/refresh (HttpOnly cookie auto-sent)
    ├─ 200: setAccessToken(new_token), scheduleRefresh(new_expires_at)  ← repeat cycle
    └─ 401:
        retry 1: wait 2s, POST /auth/refresh
        retry 2: wait 4s, POST /auth/refresh
        retry 3: wait 8s, POST /auth/refresh
        all failed: _handleSessionExpiry() → router.push('/auth?reason=expired')

Parallel 401 handling (mid-request):
  If apiFetch() gets 401:
    _refreshTokenOnce() — synchronized via _refreshPromise
    (if another request is already refreshing, awaits same promise)
    → retry original request with new token
```

---

## 24. Component Tree Reference

```
RootLayout (layout.jsx)
└── ThemeProvider (next-themes)
    └── Providers (providers.jsx)
        ├── AuthInitializer (headless)
        ├── Toast
        ├── ConfirmDialog
        └── {children}
            │
            ├── /  → Dashboard (page.jsx)
            │   ├── Header (simplified, no back button)
            │   ├── Hero section
            │   └── NotebookGrid
            │       └── NotebookCard × N
            │           └── (rename inline edit, delete confirm)
            │
            ├── /auth → AuthPage (auth/page.jsx)
            │   └── LoginSignupForm
            │
            └── /notebook/[id] → NotebookPage (notebook/[id]/page.jsx)
                ├── Header
                │   └── UserMenu (dropdown)
                ├── PanelErrorBoundary × 3 (wraps each panel)
                │   ├── Sidebar
                │   │   ├── UploadDropzone
                │   │   ├── MaterialList
                │   │   │   └── MaterialCard × N
                │   │   │       └── StatusIcon, Name, Actions
                │   │   └── DragResizeHandle (right edge)
                │   │
                │   ├── ChatPanel
                │   │   ├── SessionList (collapsible left drawer)
                │   │   │   └── SessionItem × N
                │   │   ├── ChatMessageList
                │   │   │   └── ChatMessage × N
                │   │   │       ├── UserBubble
                │   │   │       │   └── CommandBadge (if slash cmd)
                │   │   │       └── AssistantMessage
                │   │   │           ├── ReactMarkdown (text + citations)
                │   │   │           ├── AgentView (steps + artifacts)
                │   │   │           ├── CodeView (code + output)
                │   │   │           ├── WebSearchView (sources grid)
                │   │   │           └── ResearchView (phase steps + sources)
                │   │   ├── StreamingBubble (live output, shown during stream)
                │   │   │   └── (same sub-views as AssistantMessage)
                │   │   └── ChatInputArea
                │   │       ├── SlashCommandDropdown (conditional)
                │   │       ├── SuggestionDropdown (conditional)
                │   │       ├── MindMapBanner (conditional)
                │   │       ├── CommandBadge (active command, conditional)
                │   │       ├── QuickActionPills (when no input)
                │   │       └── Send / Stop button
                │   │
                │   └── StudioPanel
                │       ├── FeatureGrid
                │       │   ├── FlashcardCard → FlashcardConfigDialog
                │       │   ├── QuizCard → QuizConfigDialog
                │       │   ├── PresentationCard → PresentationConfigDialog
                │       │   ├── MindMapCard → MindMapConfigDialog
                │       │   ├── PodcastCard → PodcastStudio (dynamic)
                │       │   └── ExplainerCard → ExplainerConfigDialog
                │       ├── ContentHistory (past generations)
                │       │   └── HistoryItem × N
                │       ├── ActiveView (conditional)
                │       │   ├── InlineFlashcardsView
                │       │   ├── InlineQuizView
                │       │   ├── InlinePresentationView
                │       │   ├── MindMapCanvas (dynamic)
                │       │   │   ├── ReactFlow
                │       │   │   │   └── CustomNode × N
                │       │   │   └── FlowControls (zoom, export)
                │       │   └── PodcastStudio (dynamic)
                │       │       ├── PodcastSessionLibrary
                │       │       ├── PodcastModeSelector
                │       │       ├── PodcastGenerating (progress)
                │       │       └── PodcastPlayer
                │       │           ├── AudioControls
                │       │           ├── ChapterMarkers
                │       │           ├── ScriptPanel
                │       │           └── QAPanel (mid-playback)
                │       └── DragResizeHandle (left edge)
```

---

## 25. CSS & Theming System

**File**: `src/styles/globals.css`

### CSS Custom Properties

All colors, radii, shadows, and spacing are defined as CSS variables on `:root` and overridden per theme:

```css
/* Dark theme (default) */
[data-theme="dark"] {
  --surface-base:    #0a0a0f;     /* page background */
  --surface-raised:  #12121a;     /* panels, cards */
  --surface-overlay: #1a1a24;     /* modals, dropdowns */
  --accent:          #7c6af7;     /* primary accent (purple) */
  --accent-dark:     #6355d5;
  --accent-subtle:   rgba(124, 106, 247, 0.12);
  --text-primary:    #e8e8f0;
  --text-secondary:  #9898b0;
  --text-muted:      #606078;
  --border:          rgba(255,255,255,0.06);
  --shadow-glow-sm:  0 0 12px rgba(124, 106, 247, 0.3);
}

/* Light theme */
[data-theme="light"] {
  --surface-base:    #f8f8fc;
  --surface-raised:  #ffffff;
  --surface-overlay: #f0f0f8;
  --accent:          #6355d5;
  --text-primary:    #1a1a2e;
  --text-secondary:  #4a4a6a;
  --text-muted:      #8a8aaa;
  --border:          rgba(0,0,0,0.08);
}
```

### Tailwind Integration

`tailwind.config.js` extends with custom color tokens that reference CSS variables:

```js
theme: {
  extend: {
    colors: {
      'surface-base':    'var(--surface-base)',
      'surface-raised':  'var(--surface-raised)',
      'accent':          'var(--accent)',
      'text-primary':    'var(--text-primary)',
      'border':          'var(--border)',
    }
  }
}
```

### Utility CSS Classes (globals.css)

```css
.btn-icon-sm    — 28px square icon button with hover state
.btn-ghost      — text+icon button, ghost style
.btn-primary    — accent background button
.panel-card     — surface-raised rounded panel
.input-field    — styled input/textarea
.shadow-glow-sm — accent glow shadow
.scrollbar-hide — hide scrollbar but allow scroll
```

---

## App-Level Environment Variables

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend base URL |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8000` | WebSocket base URL |

Set in `.env.local` for development:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

---

*End of frontend.md — covers all 25 sections of the KeplerLab frontend codebase.*
