# KeplerLab Frontend — Complete Technical Documentation

> **Application:** KeplerLab AI Learning Platform Frontend  
> **Framework:** Next.js 16.1.6 + React 19.2.3  
> **Styling:** Tailwind CSS 3.4  
> **State Management:** Zustand 5  
> **Last Updated:** March 2026

---

## Table of Contents

1. [Overview](#1-overview)
2. [Project Directory Structure](#2-project-directory-structure)
3. [Technology Stack & Dependencies](#3-technology-stack--dependencies)
4. [Routing Architecture (Next.js App Router)](#4-routing-architecture)
5. [Application Entry Points](#5-application-entry-points)
6. [State Management — Zustand Stores](#6-state-management)
7. [API Client Layer](#7-api-client-layer)
8. [Authentication Flow](#8-authentication-flow)
9. [Notebook Workspace Page](#9-notebook-workspace-page)
10. [Components — Complete Reference](#10-components)
    - 10.1 [Layout Components](#101-layout-components)
    - 10.2 [Chat Components](#102-chat-components)
    - 10.3 [Studio Components](#103-studio-components)
    - 10.4 [Podcast Components](#104-podcast-components)
    - 10.5 [MindMap Components](#105-mindmap-components)
    - 10.6 [Presentation Components](#106-presentation-components)
    - 10.7 [Notebook Components](#107-notebook-components)
    - 10.8 [Viewer Components](#108-viewer-components)
    - 10.9 [UI / Common Components](#109-ui--common-components)
11. [Custom Hooks](#11-custom-hooks)
12. [Slash Command System](#12-slash-command-system)
13. [Feature Flows — End to End](#13-feature-flows)
    - 13.1 [Auth Flow](#131-auth-flow)
    - 13.2 [Material Upload](#132-material-upload)
    - 13.3 [Chat (RAG + Intents)](#133-chat-rag--intents)
    - 13.4 [Flashcard Generation](#134-flashcard-generation)
    - 13.5 [Quiz Generation](#135-quiz-generation)
    - 13.6 [Presentation Generation](#136-presentation-generation)
    - 13.7 [Mind Map Generation](#137-mind-map-generation)
    - 13.8 [Podcast Feature](#138-podcast-feature)
    - 13.9 [Explainer Video](#139-explainer-video)
    - 13.10 [Code Mode](#1310-code-mode)
    - 13.11 [Research Mode](#1311-research-mode)
    - 13.12 [Agent Mode](#1312-agent-mode)
14. [Streaming (SSE) Implementation](#14-streaming-sse-implementation)
15. [WebSocket Integration](#15-websocket-integration)
16. [Theme & Styling System](#16-theme--styling-system)
17. [Next.js Configuration](#17-nextjs-configuration)
18. [Middleware](#18-middleware)
19. [Error Handling](#19-error-handling)
20. [Build & Deployment](#20-build--deployment)

---

## 1. Overview

KeplerLab frontend is a **Next.js 16 App Router** single-page application providing an AI-powered learning workspace. It features:

- **Notebook management** — create and switch between named learning notebooks
- **Material management** — upload PDFs, URLs, YouTube, text; view real-time processing status via WebSocket
- **Multi-mode AI chat** — RAG, Agent, Code, Web Search, Research (via slash commands)
- **Content generation panels** — Flashcards, Quiz, Presentation (PPT), MindMap
- **AI Podcast** — generate and play host/guest podcast from materials with Q&A interruption
- **Explainer Videos** — AI-narrated slide-by-slide video from presentations
- **Dark mode** — default dark theme with light mode toggle
- **Streaming UI** — all AI responses streamed token-by-token via SSE

### Architecture Pattern
```
App Router Page → Zustand Store ↔ API Client → FastAPI Backend
                     ↕
               React Components
```

---

## 2. Project Directory Structure

```
frontend/
├── src/
│   ├── app/                            # Next.js App Router
│   │   ├── layout.jsx                  # Root layout (Inter + JetBrains fonts, metadata)
│   │   ├── page.jsx                    # Home / notebook list dashboard
│   │   ├── providers.jsx               # Theme + Auth initializer + Toast + Confirm
│   │   ├── loading.jsx                 # Global loading state
│   │   ├── error.jsx                   # Global error boundary
│   │   ├── global-error.jsx            # Global error (layout-level)
│   │   ├── not-found.jsx               # 404 page
│   │   ├── auth/
│   │   │   ├── layout.jsx              # Auth layout (centered card)
│   │   │   └── page.jsx                # Login / Signup page
│   │   ├── notebook/
│   │   │   └── [id]/
│   │   │       ├── layout.jsx          # Notebook layout wrapper
│   │   │       └── page.jsx            # Main notebook workspace
│   │   └── view/
│   │       └── page.jsx                # Standalone viewer route (PPT/files)
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Header.jsx              # Top navigation bar
│   │   │   └── Sidebar.jsx             # Left material sidebar
│   │   ├── chat/
│   │   │   ├── ChatPanel.jsx           # Main chat container
│   │   │   ├── ChatInputArea.jsx       # Message input + slash command UI
│   │   │   ├── ChatMessage.jsx         # Individual message renderer
│   │   │   ├── ChatMessageList.jsx     # Virtualized message list
│   │   │   ├── ChatEmptyState.jsx      # Empty chat placeholder
│   │   │   ├── ChatHistoryModal.jsx    # Session history selector
│   │   │   ├── MarkdownRenderer.jsx    # Markdown + KaTeX + GFM renderer
│   │   │   ├── OutputRenderer.jsx      # Code/table/chart output renderer
│   │   │   ├── CodePanel.jsx           # Generated code viewer + run button
│   │   │   ├── CopyButton.jsx          # Copy-to-clipboard button
│   │   │   ├── BlockHoverMenu.jsx      # Per-paragraph hover actions
│   │   │   ├── CommandBadge.jsx        # Active slash command badge in input
│   │   │   ├── SlashCommandDropdown.jsx # Slash command suggestion popup
│   │   │   ├── SlashCommandPills.jsx   # Row of commands below input
│   │   │   ├── SuggestionDropdown.jsx  # Input suggestions dropdown
│   │   │   ├── WebSources.jsx          # Web search source links
│   │   │   ├── WebSearchStrip.jsx      # Animated search progress strip
│   │   │   ├── ResearchProgress.jsx    # Research mode progress bar
│   │   │   ├── ResearchProgressPanel.jsx # Detailed research status
│   │   │   ├── ResearchReport.jsx      # Rendered research report with citations
│   │   │   ├── AgentStatusStrip.jsx    # Agent mode step tracker
│   │   │   ├── MiniBlockChat.jsx       # Mini chat for block follow-ups
│   │   │   ├── DocumentPreview.jsx     # Inline document preview
│   │   │   └── slashCommands.js        # Slash command definitions & parsers
│   │   ├── studio/
│   │   │   ├── StudioPanel.jsx         # Right panel container (tabbed)
│   │   │   ├── FeatureCard.jsx         # Feature selection card
│   │   │   ├── ConfigDialogs.jsx       # Config modals (flashcard/quiz/PPT/mindmap)
│   │   │   ├── ContentHistory.jsx      # Saved content history
│   │   │   ├── HistoryRenameModal.jsx  # Rename saved content
│   │   │   ├── InlineFlashcardsView.jsx # Flashcard flipper UI
│   │   │   ├── InlineQuizView.jsx      # Interactive quiz UI
│   │   │   ├── InlineExplainerView.jsx # Explainer video player
│   │   │   ├── ExplainerDialog.jsx     # Explainer generation config dialog
│   │   │   └── index.js               # Studio exports
│   │   ├── podcast/
│   │   │   ├── PodcastStudio.jsx       # Full podcast workspace
│   │   │   ├── PodcastConfigDialog.jsx # Podcast configuration (mode, voices)
│   │   │   ├── PodcastSessionLibrary.jsx # List of podcast sessions
│   │   │   ├── PodcastModeSelector.jsx # Mode picker (overview/debate/etc.)
│   │   │   ├── PodcastPlayer.jsx       # Playback controls + waveform
│   │   │   ├── PodcastMiniPlayer.jsx   # Compact player (bottom bar)
│   │   │   ├── PodcastTranscript.jsx   # Scrollable transcript view
│   │   │   ├── PodcastChapterBar.jsx   # Chapter navigation bar
│   │   │   ├── PodcastDoubtHistory.jsx # Q&A history list
│   │   │   ├── PodcastInterruptDrawer.jsx # Slide-up interrupt Q&A drawer
│   │   │   ├── PodcastGenerating.jsx   # Generation progress screen
│   │   │   ├── PodcastExportBar.jsx    # Export (PDF/JSON) controls
│   │   │   ├── VoicePicker.jsx         # Voice selection with preview
│   │   │   └── index.js               # Podcast exports
│   │   ├── mindmap/
│   │   │   ├── MindMapCanvas.jsx       # React Flow canvas wrapper
│   │   │   ├── MindMapView.jsx         # Full mindmap view with controls
│   │   │   └── MindMapNode.jsx         # Custom node renderer
│   │   ├── presentation/
│   │   │   └── PresentationView.jsx    # HTML slide renderer + fullscreen
│   │   ├── notebook/
│   │   │   ├── UploadDialog.jsx        # Upload flow modal (file/url/youtube/text)
│   │   │   ├── SourceItem.jsx          # Material list item component
│   │   │   └── WebSearchDialog.jsx     # Web source search dialog
│   │   ├── viewer/
│   │   │   └── FileViewerContent.jsx   # File viewing (PDF, PPT, etc.)
│   │   └── ui/
│   │       ├── Modal.jsx               # Generic modal wrapper
│   │       ├── ToastContainer.jsx      # Toast notification container
│   │       ├── ConfirmDialog.jsx       # Confirmation dialog (Zustand-driven)
│   │       └── ErrorBoundary.jsx       # React error boundary for panels
│   │
│   ├── hooks/
│   │   ├── useChatStream.js            # SSE streaming for chat responses
│   │   ├── useMaterialUpdates.js       # WebSocket material status updates
│   │   ├── useMicInput.js              # Microphone input for voice questions
│   │   ├── useMindMap.js               # Mind map data + React Flow state
│   │   ├── usePodcast.js               # Podcast session management
│   │   ├── usePodcastPlayer.js         # Audio playback engine
│   │   ├── usePodcastWebSocket.js      # Podcast real-time updates
│   │   └── useResizablePanel.js        # Drag-to-resize panel divider
│   │
│   ├── stores/
│   │   ├── useAppStore.js              # Main workspace store (master store)
│   │   ├── useAuthStore.js             # Authentication + token management
│   │   ├── useChatStore.js             # Chat messages + session
│   │   ├── useMaterialStore.js         # Materials + source selection
│   │   ├── useNotebookStore.js         # Current notebook state
│   │   ├── useUIStore.js               # Loading states + active panel
│   │   ├── usePodcastStore.js          # Podcast session store
│   │   ├── useToastStore.js            # Toast notification queue
│   │   └── useConfirmStore.js          # Confirm dialog state
│   │
│   ├── lib/
│   │   ├── api/                        # Backend API client modules
│   │   │   ├── config.js               # Axios/fetch config, token injection
│   │   │   ├── auth.js                 # Auth endpoints
│   │   │   ├── notebooks.js            # Notebook CRUD
│   │   │   ├── materials.js            # Materials API
│   │   │   ├── chat.js                 # Chat + sessions
│   │   │   ├── generation.js           # Flashcard/Quiz/PPT/MindMap
│   │   │   ├── mindmap.js              # MindMap endpoints
│   │   │   ├── podcast.js              # Podcast API
│   │   │   ├── explainer.js            # Explainer video API
│   │   │   ├── agent.js                # Agent/code execution
│   │   │   └── jobs.js                 # Job polling
│   │   └── utils/
│   │       ├── helpers.js              # generateId(), formatDate(), etc.
│   │       └── constants.js            # TIMERS, limits, string constants
│   │
│   ├── styles/
│   │   └── globals.css                 # Global styles + Tailwind directives
│   │
│   └── middleware.js                   # Next.js middleware (auth route guard)
│
├── public/
│   └── favicon.ico
│
├── next.config.mjs                     # Next.js config + API rewrites
├── tailwind.config.js                  # Tailwind theme config
├── postcss.config.mjs
├── eslint.config.mjs
├── jsconfig.json                       # Path aliases (@/...)
├── package.json
└── Dockerfile                          # Production container
```

---

## 3. Technology Stack & Dependencies

### Core
| Package | Version | Purpose |
|---------|---------|---------|
| `next` | 16.1.6 | React framework (App Router, SSR, API rewrites) |
| `react` | 19.2.3 | UI framework |
| `react-dom` | 19.2.3 | DOM renderer |
| `zustand` | ^5.0.11 | State management |
| `next-themes` | ^0.4.6 | Dark/light mode |

### Rendering
| Package | Version | Purpose |
|---------|---------|---------|
| `react-markdown` | ^10.1.0 | Markdown rendering |
| `remark-gfm` | ^4.0.1 | GitHub Flavored Markdown |
| `remark-math` | ^6.0.0 | Math expressions in markdown |
| `rehype-katex` | ^7.0.1 | KaTeX math rendering |
| `rehype-raw` | ^7.0.0 | Raw HTML in markdown |
| `katex` | ^0.16.33 | Math equation rendering |
| `react-syntax-highlighter` | ^16.1.1 | Code block syntax highlighting |

### Data Visualization & Flow
| Package | Version | Purpose |
|---------|---------|---------|
| `@xyflow/react` | ^12.10.1 | ReactFlow for mind maps |
| `dagre` | ^0.8.5 | Automatic graph layout for mind maps |

### Export & Utilities
| Package | Version | Purpose |
|---------|---------|---------|
| `html-to-image` | ^1.11.13 | Export mind maps to PNG |
| `jspdf` | ^4.2.0 | Client-side PDF export |
| `react-window` | ^2.2.7 | Virtualized lists (large message lists) |
| `lucide-react` | ^0.576.0 | Icon library |

### Dev Dependencies
| Package | Purpose |
|---------|---------|
| `tailwindcss` ^3.4.17 | Utility CSS framework |
| `autoprefixer` | Vendor prefix addition |
| `postcss` | CSS processing |
| `eslint` ^9 | Linting |
| `eslint-config-next` | Next.js ESLint rules |

### Path Aliases
All imports use `@/` prefix mapping to `src/` (configured in `jsconfig.json`):
```js
import ChatPanel from '@/components/chat/ChatPanel';
import useAppStore from '@/stores/useAppStore';
import { chatAPI } from '@/lib/api/chat';
```

---

## 4. Routing Architecture

Next.js 15+ App Router with file-based routing:

| Route | File | Description |
|-------|------|-------------|
| `/` | `app/page.jsx` | Home — notebook list dashboard |
| `/auth` | `app/auth/page.jsx` | Login / Signup |
| `/notebook/[id]` | `app/notebook/[id]/page.jsx` | Main workspace |
| `/view` | `app/view/page.jsx` | Standalone content viewer |

### Route Guards
`src/middleware.js` — Next.js Edge Middleware:
- Runs on all routes except `/auth` and static files
- Reads `refresh_token` cookie (HttpOnly, set by backend)
- If no cookie → redirect to `/auth`
- If on `/auth` with valid cookie → redirect to `/`

### Dynamic Route — `/notebook/[id]`
- `[id]` = notebook UUID from DB, or `"draft"` for unsaved notebooks
- `draft` mode creates a temporary workspace without a DB notebook
- When first material uploaded in draft → auto-creates notebook

---

## 5. Application Entry Points

### `app/layout.jsx` — Root Layout
```jsx
// Fonts: Inter (body) + JetBrains Mono (code)
// CSS variables: --font-inter, --font-jetbrains
// Metadata: title "KeplerLab — AI Learning Platform"
// Wraps everything in <Providers>
```

### `app/providers.jsx` — Provider Tree
```jsx
<ThemeProvider attribute="class" defaultTheme="dark" storageKey="kepler-theme">
  <AuthInitializer>         // Calls initAuth() on mount
    {children}
    <ToastContainer />      // Global toast notifications
    <ConfirmDialog />       // Global confirm dialog
  </AuthInitializer>
</ThemeProvider>
```

**AuthInitializer**: Calls `useAuthStore.initAuth()` once on app mount. This calls `POST /auth/refresh` to restore session from the HttpOnly cookie.

---

## 6. State Management

All state managed with **Zustand 5** (no Redux, no React Context for global state).

### Store Architecture

```
useAppStore (master)
  ├── notebook state (currentNotebook, draftMode)
  ├── material state (materials[], currentMaterial, selectedSources[])
  ├── chat state (messages[], sessionId)
  ├── generated content (flashcards, quiz, notes[])
  └── UI state (loading{}, error, activePanel)

useAuthStore (auth)
  ├── user, isAuthenticated, isLoading
  ├── access token management (module-level ref, not in state)
  └── scheduleRefresh (auto-refresh timer)

useChatStore (focused chat)
  ├── messages[], sessionId
  ├── isStreaming, abortController
  └── pendingChatMessage

useMaterialStore (focused materials)
  ├── materials[], currentMaterial
  └── selectedSources[]

useNotebookStore (focused notebook)
  ├── currentNotebook
  └── draftMode

useUIStore (focused UI)
  ├── loading{}
  └── activePanel

usePodcastStore (podcast)
  ├── sessions[], currentSession
  ├── segments[], currentSegment
  └── doubts[], bookmarks[]

useToastStore
  ├── toasts[] 
  └── add/remove actions

useConfirmStore
  ├── isOpen, message, onConfirm
  └── trigger/resolve actions
```

### Key Design Patterns

**Token Management:**
Access token stored in module-level ref (`_accessTokenRef`), NOT in Zustand state. This prevents unnecessary re-renders on token refresh.

**Auto Token Refresh:**
`scheduleRefresh()` schedules a `setTimeout` 14 minutes after login (1 min before 15-min expiry). Retries 3 times with exponential backoff (2s, 4s, 8s) before forcing logout. On logout: `window.location.href = '/auth?reason=expired'`.

**Source Selection:**
`selectedSources[]` in `useMaterialStore` is an array of material IDs. All AI operations use `selectedSources` as the `material_ids[]` parameter to the backend. Users can toggle, select-all, or deselect-all.

**Notebook Switch Cleanup:**
`resetForNotebookSwitch()` clears all transient state (materials, messages, studio content, selections) when the user navigates to a different notebook.

---

## 7. API Client Layer

`src/lib/api/`

### `config.js` — API Configuration
- Base URL from `NEXT_PUBLIC_API_BASE_URL` env var (default: `http://localhost:8000`)
- `setAccessToken(token)` — module-level token store for injection
- `onSessionExpired(handler)` — callback registration for 401 handling
- `apiFetch(path, options)` — base fetch wrapper:
  - Injects `Authorization: Bearer {token}` header automatically
  - Handles 401 → calls `onSessionExpired` callback if registered
  - Returns parsed JSON or throws error
- `apiStream(path, options)` — returns raw `Response` for SSE streaming

### API Modules

#### `auth.js`
```js
login({ email, password })          → POST /auth/login
signup({ email, username, password }) → POST /auth/signup
refreshToken()                      → POST /auth/refresh
getCurrentUser()                    → GET /auth/me
logout()                            → POST /auth/logout
```

#### `notebooks.js`
```js
getNotebooks()                      → GET /notebooks
getNotebook(id)                     → GET /notebooks/{id}
createNotebook({ name, description }) → POST /notebooks
updateNotebook(id, data)            → PATCH /notebooks/{id}
deleteNotebook(id)                  → DELETE /notebooks/{id}
saveNotebookContent(id, data)       → POST /notebooks/{id}/content
getNotebookContent(id)              → GET /notebooks/{id}/content
deleteNotebookContent(id, contentId) → DELETE /notebooks/{id}/content/{contentId}
```

#### `materials.js`
```js
getMaterials(notebookId?)           → GET /materials?notebook_id=
uploadFile(formData)                → POST /upload (multipart)
uploadUrl(url, notebookId, title?)  → POST /upload/url
uploadYouTube(url, notebookId)      → POST /upload/youtube
uploadText(text, title, notebookId) → POST /upload/text
deleteMaterial(id)                  → DELETE /materials/{id}
updateMaterial(id, data)            → PATCH /materials/{id}
getMaterialText(id)                 → GET /materials/{id}/text
```

#### `chat.js`
```js
sendMessage(data)                   → POST /chat (returns Response for SSE)
getSessions(notebookId)             → GET /chat/sessions?notebook_id=
createSession(notebookId, title)    → POST /chat/sessions
deleteSession(id)                   → DELETE /chat/sessions/{id}
getSessionMessages(sessionId)       → GET /chat/sessions/{id}/messages
getSuggestions(partial, notebookId) → POST /chat/suggestions
blockFollowup(data)                 → POST /chat/block-followup
```

#### `generation.js`
```js
generateFlashcards(data)            → POST /flashcard
generateQuiz(data)                  → POST /quiz
generatePresentation(data)          → POST /presentation
generateMindmap(data)               → POST /mindmap
getMindmap(notebookId)              → GET /mindmap/{notebookId}
deleteMindmap(id)                   → DELETE /mindmap/{id}
```

#### `podcast.js`
```js
createSession(data)                 → POST /podcast/session
startGeneration(id)                 → POST /podcast/session/{id}/generate
getSession(id)                      → GET /podcast/session/{id}
getSessions()                       → GET /podcast/sessions
updateSession(id, data)             → PATCH /podcast/session/{id}
deleteSession(id)                   → DELETE /podcast/session/{id}
getSegments(id)                     → GET /podcast/session/{id}/segments
getAudioUrl(sessionId, index)       → URL /podcast/audio/{sessionId}/{index}
submitDoubt(id, data)               → POST /podcast/session/{id}/doubt
getDoubts(id)                       → GET /podcast/session/{id}/doubts
addBookmark(id, data)               → POST /podcast/session/{id}/bookmark
addAnnotation(id, data)             → POST /podcast/session/{id}/annotation
exportSession(id, format)           → POST /podcast/session/{id}/export
getVoices(language?)                → GET /podcast/voices
previewVoice(voiceId, text)         → POST /podcast/voices/preview
```

#### `explainer.js`
```js
checkPresentations(data)            → POST /explainer/check-presentations
generateExplainer(data)             → POST /explainer/generate
getStatus(id)                       → GET /explainer/{id}/status
getVideoUrl(id)                     → URL /explainer/{id}/video
```

#### `agent.js`
```js
executeCode(data)                   → POST /agent/execute-code (returns Response for SSE)
getArtifactUrl(id, token)           → URL /workspace/file/{id}?token=
```

#### `jobs.js`
```js
getJob(id)                          → GET /jobs/{id}
pollJob(id, intervalMs, maxWait)    → polls until completed/failed
```

---

## 8. Authentication Flow

### Login Flow
```
User visits / → middleware.js → no cookie → redirect /auth

AuthPage renders login/signup form

[Login]
  1. User submits email + password
  2. apiLogin() → POST /auth/login
  3. Backend sets HttpOnly refresh_token cookie
  4. Returns access_token
  5. useAuthStore._syncToken(access_token) → stored in module ref
  6. Calls GET /auth/me → sets user in store
  7. useAuthStore.scheduleRefresh() starts 14-min timer
  8. router.push('/') → home page

[Signup]
  Same flow with POST /auth/signup first, then auto-login
```

### Session Restore (Page Refresh)
```
providers.jsx mounts → AuthInitializer calls initAuth()
1. POST /auth/refresh (cookie sent automatically)
2. Returns new access_token
3. Store token in module ref
4. GET /auth/me → restore user state
5. scheduleRefresh() 
```

### Token Refresh
Auto-scheduled 14 minutes after successful login:
```
scheduleRefresh():
  setTimeout(14 min):
    for attempt in 1..3:
      try: POST /auth/refresh → update token
           scheduleRefresh()  → reschedule
           return
      catch: wait 2^attempt seconds
    → all retries failed
    → clear user state
    → window.location.href = '/auth?reason=expired'
```

### Logout
```
POST /auth/logout → backend revokes all tokens, clears cookie
useAuthStore reset → user=null, isAuthenticated=false
Clear module-level token ref
router.push('/auth')
```

---

## 9. Notebook Workspace Page

`app/notebook/[id]/page.jsx` — Main application workspace

### Layout
```
┌──────────────────────────────────────────────────────────────┐
│ Header (top bar)                                             │
├─────────────┬──────────────────────┬─────────────────────────┤
│ Sidebar     │  ChatPanel           │   StudioPanel           │
│ (materials  │  (left center)       │   (right panel)         │
│  + upload)  │                      │                         │
│             │  [active slash cmd]  │   [tabs: features,      │
│             │  [messages stream]   │    flashcard, quiz,      │
│             │  [input area]        │    mindmap, podcast,     │
│             │                      │    explainer]           │
└─────────────┴──────────────────────┴─────────────────────────┘
```

### Panel System
- Three-panel layout: Sidebar + ChatPanel + StudioPanel
- Panels are **lazy-loaded** with `dynamic(() => import(...), { ssr: false })`
- `useResizablePanel` hook allows drag-to-resize between Chat and Studio
- On mobile: sidebar slides in/out with hamburger button
- `ErrorBoundary` wraps each panel (`PanelErrorBoundary`)

### Page Load Sequence
```
1. Get notebook ID from URL params
2. If id === 'draft' → create draft workspace (no API call)
3. Else → GET /notebooks/{id}
4. If not found → router.replace('/')
5. Load materials → GET /materials?notebook_id={id}
6. Set selectedSources = all completed material IDs
7. Render panels
```

---

## 10. Components

### 10.1 Layout Components

#### `Header.jsx`
- App logo + KeplerLab branding
- Current notebook name (editable inline)
- Theme toggle (dark/light)
- User menu (username, logout)
- Navigation to home

#### `Sidebar.jsx`
- **Material list** with `SourceItem` for each material
- Status indicators per material: `pending` (spinner), `completed` (green), `failed` (red)
- Checkbox selection for multi-material AI operations
- **Select All / Deselect All** toggle
- Upload button → opens `UploadDialog`
- Material rename (inline edit)
- Material delete (with confirm)
- Material text preview (via `GET /materials/{id}/text`)
- WebSearch button → opens `WebSearchDialog`
- Notebook switcher at bottom

---

### 10.2 Chat Components

#### `ChatPanel.jsx`
Main chat container orchestrating:
- Session management (create, load, switch)
- Message sending via `useChatStream`
- Active slash command state
- Streaming response assembly
- Suggestion fetching on typing

#### `ChatInputArea.jsx`
- Multiline textarea with auto-resize
- Slash command detection: typing `/` opens `SlashCommandDropdown`
- Active command displayed as `CommandBadge` above input
- `SlashCommandPills` row below input (quick-access)
- Send button (keyboard: Enter, shift+Enter for newline)
- Stop button while streaming
- Suggestion dropdown from backend (`POST /chat/suggestions`)

#### `ChatMessage.jsx`
Renders a single message:
- **User messages**: plain text with command badge
- **Assistant messages**: `MarkdownRenderer`
- **Artifacts**: image/chart/CSV rendered via `OutputRenderer`
- **Web sources**: `WebSources` component with collapsible link list
- **Research reports**: `ResearchReport` with citation footnotes
- **Agent steps**: `AgentStatusStrip` with tool call log
- **Code blocks**: `CodePanel` with run button
- Per-paragraph hover: `BlockHoverMenu` (ask, simplify, translate)

#### `ChatMessageList.jsx`
- Virtualized scroll using `react-window`
- Auto-scroll to bottom on new messages
- Loading indicator while streaming

#### `MarkdownRenderer.jsx`
Renders AI markdown responses with:
- **remark-gfm**: tables, strikethrough, task lists, links
- **remark-math + rehype-katex**: inline `$...$` and block `$$...$$` LaTeX
- **rehype-raw**: HTML in markdown (for explainer notes)
- **react-syntax-highlighter**: code blocks with language detection
- `CopyButton` on every code block

#### `CodePanel.jsx`
- Displays LLM-generated Python code in a read-only code view
- **Edit** button → makes code editable
- **Run** button → calls `POST /agent/execute-code` with SSE stream
- Progress indicator during execution
- Displays stdout, stderr, charts (image), tables (CSV) inline

#### `OutputRenderer.jsx`
Detects and renders agent/code artifacts:
- `displayType === 'chart'` → `<img>` from base64 or artifact URL
- `displayType === 'table'` → HTML table render
- `displayType === 'csv'` → tabular preview
- Generic files → download link

#### `SlashCommandDropdown.jsx`
Popup menu when user types `/`:
- Shows all 4 commands: `/agent`, `/research`, `/code`, `/web`
- Keyboard navigation (↑↓ arrows, Enter to select)
- Click to activate

#### `CommandBadge.jsx`
Inline badge showing active command:
- Colored per command (amber=agent, blue=research, purple=code, green=web)
- Click × to dismiss

#### `ResearchReport.jsx`
- Full research report with sections
- Inline `[n]` citations linked to source URLs
- Source list at bottom
- Copy report button

#### `AgentStatusStrip.jsx`
- Collapsible tool call timeline
- Shows each step: tool name → input → output summary
- Icons per tool type

#### `MiniBlockChat.jsx`
Mini chat modal opened from `BlockHoverMenu`:
- Allows follow-up questions on a specific paragraph
- Uses `POST /chat/block-followup`

---

### 10.3 Studio Components

#### `StudioPanel.jsx`
Right panel with tabs:
- **Features** — feature card grid
- **Flashcards** — `InlineFlashcardsView`
- **Quiz** — `InlineQuizView`
- **Mind Map** — `MindMapView`
- **Podcast** — `PodcastStudio`
- **Explainer** — `InlineExplainerView`
- **History** — `ContentHistory`

#### `FeatureCard.jsx`
Grid of AI feature cards:
- Flashcards, Quiz, Presentation, Mind Map, Podcast, Explainer Video
- Click → opens config dialog

#### `ConfigDialogs.jsx`
Feature-specific configuration modals:

**Flashcard Config:**
- Topic (optional)
- Card count (1-150)
- Difficulty (easy/medium/hard)
- Additional instructions

**Quiz Config:**
- Topic (optional)
- Question count (1-150)
- Difficulty
- Additional instructions

**Presentation Config:**
- Max slides (3-60)
- Theme (text description)
- Additional instructions

**Mind Map Config:**
- Source selection (uses selectedSources)
- Confirm button only

#### `InlineFlashcardsView.jsx`
- Card flip animation (front/back)
- Progress bar (current/total)
- Previous/Next navigation
- Shuffle button
- Mark as known/unknown
- Save to notebook button

#### `InlineQuizView.jsx`
- MCQ rendered with A/B/C/D options
- Submit → reveals correct answer + explanation
- Score tracker
- Review mode after completion
- Save to notebook button

#### `ContentHistory.jsx`
Displays saved content from notebook:
- Lists all saved flashcard sets, quizzes, presentations, mindmaps
- Load/delete per item
- `HistoryRenameModal` for renaming

#### `ExplainerDialog.jsx`
- Select or create presentation
- Language selection (PPT + narration)
- Voice gender toggle
- Start generation → shows progress
- Links to `InlineExplainerView` when done

#### `InlineExplainerView.jsx`
- Embeds generated MP4 video
- Chapter navigation
- Download button

---

### 10.4 Podcast Components

#### `PodcastStudio.jsx`
Master podcast component:
- Shows `PodcastSessionLibrary` or active player
- Manages `usePodcast` hook state

#### `PodcastConfigDialog.jsx`
Session creation form:
- Mode selector (`PodcastModeSelector`): overview/deep-dive/debate/q-and-a/full/topic
- Topic input (required for topic/deep-dive)
- Language selector
- Host + Guest voice pickers (`VoicePicker`)
- Material selection (from notebook)

#### `VoicePicker.jsx`
- Language-aware voice list from `GET /podcast/voices`
- Voice preview button → plays sample via `POST /podcast/voices/preview`
- Search/filter by voice name

#### `PodcastGenerating.jsx`
Progress screen during generation:
- Status text: "Generating script…" / "Generating audio…"
- Animated progress bar
- Cancel button

#### `PodcastPlayer.jsx`
Full podcast playback UI:
- Play/Pause/Stop controls
- Seek bar + current time / total duration
- Volume control
- Speed control (0.75x / 1x / 1.25x / 1.5x / 2x)
- Auto-advance to next segment
- Click transcript line to jump to segment
- **Interrupt button** → opens `PodcastInterruptDrawer`
- Mini player fallback (persists across navigation)

#### `PodcastTranscript.jsx`
- Full scrollable transcript
- Auto-scroll to current segment
- Click any line → jump to that audio position
- Host/guest speaker labels with color coding
- Chapter dividers

#### `PodcastChapterBar.jsx`
- Chapter list as clickable segments
- Visual progress indicator

#### `PodcastInterruptDrawer.jsx`
Slide-up drawer for Q&A:
- Text input or microphone (`useMicInput`)
- Submit question → shows loading
- Displays AI answer with audio playback
- Q&A added to session history

#### `PodcastDoubtHistory.jsx`
- List of all Q&As from the session
- Replay answer audio
- Timestamp + segment context

#### `PodcastExportBar.jsx`
- PDF export button
- JSON export button
- Download links after generation

#### `PodcastSessionLibrary.jsx`
- Table of all past podcast sessions
- Status badges (ready/playing/failed)
- Load/delete/play actions
- Search + filter

---

### 10.5 MindMap Components

#### `MindMapView.jsx`
- Toolbar: generate, refresh, download (PNG), zoom controls
- Container for `MindMapCanvas`
- Loading and error states
- **Chat bridge**: clicking a node sends the node label as a chat question

#### `MindMapCanvas.jsx`
- Wraps `@xyflow/react` ReactFlow component
- `dagre` auto-layout for hierarchical graph
- Custom edge types
- Configures node types → `MindMapNode`
- Pan + zoom controls
- `html-to-image` for PNG export

#### `MindMapNode.jsx`
- Custom node renderer per node type:
  - `root` — large center circle, primary color
  - `branch` — medium rounded rect, secondary color  
  - `leaf` — small rounded rect, muted color
- Hover tooltip with full label
- Click → triggers chat message via `setPendingChatMessage`

---

### 10.6 Presentation Components

#### `PresentationView.jsx`
- Renders HTML presentation in iframe or direct DOM injection
- Navigation: Previous/Next slide buttons
- Slide number indicator
- Fullscreen toggle
- Download HTML button
- Keyboard arrow key navigation
- Accessible slide labels

---

### 10.7 Notebook Components

#### `UploadDialog.jsx`
Multi-mode upload modal:

**File Upload tab:**
- Drag-and-drop zone
- File type filter display
- Multiple file support (queued)
- Progress per file
- Error display per file

**URL tab:**
- URL input with validation
- Optional custom title
- Fetches and adds web content

**YouTube tab:**
- YouTube URL input
- Video title preview (yt-dlp metadata)
- Automatic transcript extraction

**Text tab:**
- Title input
- Large text area
- Paste or type content directly

All tabs → calls appropriate upload API → creates Material in pending state → WebSocket subscription for real-time status.

#### `SourceItem.jsx`
Material list item:
- Checkbox for multi-select
- Material icon (PDF/URL/YouTube/Text)
- Filename/title (truncated)
- Status badge: pending (spinner), processing (animated), completed, failed (with error tooltip)
- Chunk count when completed
- Action menu: rename, view text, delete

#### `WebSearchDialog.jsx`
- Search input
- Search results list
- Add selected URLs as materials button

---

### 10.8 Viewer Components

#### `FileViewerContent.jsx`
- Renders uploaded file content inline
- PDF: `<embed>` or iframe
- Text: `<pre>` formatted
- Used in standalone `/view` route for sharing

---

### 10.9 UI / Common Components

#### `Modal.jsx`
Generic modal with:
- Backdrop click to close
- Escape key close
- Focus trap
- Animated enter/exit
- Customizable width

#### `ToastContainer.jsx`
Driven by `useToastStore`:
- Toasts stack in top-right corner
- Types: success (green), error (red), warning (amber), info (blue)
- Auto-dismiss after 3s (configurable)
- Manual dismiss button
- Max 5 visible at once

#### `ConfirmDialog.jsx`
Driven by `useConfirmStore`:
```js
useConfirmStore.trigger({
  message: "Delete this notebook?",
  onConfirm: () => deleteNotebook(id)
})
```
- Modal with Cancel + Confirm buttons
- Resolves the stored `onConfirm` callback

#### `ErrorBoundary.jsx`
`PanelErrorBoundary` — wraps each major panel:
- Catches render errors
- Shows error message + retry button
- Does not crash entire page

---

## 11. Custom Hooks

### `useChatStream.js`
Core hook for SSE chat streaming:

```js
const { sendMessage, isStreaming, abort } = useChatStream();
```

**Internal flow:**
```
sendMessage(text, options):
1. Add user message to store
2. Add empty assistant message placeholder
3. Create AbortController
4. POST /chat → returns Response (fetch SSE)
5. reader = response.body.getReader()
6. Read chunks:
   SSE event types:
   "token"      → append to last message content
   "citations"  → attach citations array to last message  
   "code"       → store as CodePanel artifact
   "chart"      → store as chart artifact
   "agent_step" → append to agentSteps array
   "web_sources"→ attach web sources
   "research"   → update research report
   "error"      → show error toast
   "done"       → finalize, set isStreaming=false
7. On abort → add partial message with [stopped] marker
```

### `useMaterialUpdates.js`
WebSocket hook for material processing status:

```js
useMaterialUpdates(materialId, onUpdate)
```

```
1. Connect: WS /ws/materials/{materialId}?token={accessToken}
2. On message:
   - Parse JSON event
   - If status_update → call onUpdate({status, chunkCount})
   - Update useMaterialStore.updateMaterial(id, { status, chunkCount })
3. On disconnect → reconnect with exponential backoff
4. Cleanup on unmount
```

### `useMicInput.js`
Microphone for podcast Q&A:
```
1. navigator.mediaDevices.getUserMedia({ audio: true })
2. MediaRecorder → collect audio chunks
3. Stop → combine to Blob → base64 encode
4. Returns audioBlob, isRecording, start(), stop()
```

### `useMindMap.js`
Mind map data management:
```
1. fetchMindmap(notebookId) → GET /mindmap/{notebookId}
2. generateMindmap(materialIds, notebookId) → POST /mindmap
3. Transform nodes/edges for ReactFlow format
4. Apply dagre layout algorithm
5. Returns nodes, edges, loading, error, generate, refresh
```

### `usePodcast.js`
Podcast session lifecycle:
```
1. fetchSessions() → GET /podcast/sessions
2. createSession(config) → POST /podcast/session
3. startGeneration(id) → POST /podcast/session/{id}/generate
4. deleteSession(id) → DELETE /podcast/session/{id}
5. updateSession(id, patch) → PATCH /podcast/session/{id}
6. submitDoubt(id, q) → POST /podcast/session/{id}/doubt
7. Manages loading states in useUIStore
```

### `usePodcastPlayer.js`
Audio playback engine:
```
1. Uses HTML5 Audio API
2. Preload next segment while current plays
3. onEnded → advance to next segment
4. Sends PATCH /podcast/session/{id} to sync currentSegment
5. Returns: play, pause, seek, currentTime, duration, isPlaying
```

### `usePodcastWebSocket.js`
Real-time podcast updates:
```
1. Connect WS to podcast events channel
2. On "segment_ready" → update segments in store
3. On "status_update" → update session status
4. Used during generation progress polling
```

### `useResizablePanel.js`
Drag handle for Chat/Studio resize:
```
1. MouseDown → start tracking
2. MouseMove → calculate new width ratio
3. MouseUp → finalize
4. Returns: ref, width, isDragging
```

---

## 12. Slash Command System

`src/components/chat/slashCommands.js`

### Commands

| Command | Intent | Color | Description |
|---------|--------|-------|-------------|
| `/agent` | `AGENT` | Amber | Multi-step autonomous task execution |
| `/research` | `WEB_RESEARCH` | Blue | Deep research with citations |
| `/code` | `CODE_EXECUTION` | Purple | Generate + run Python code |
| `/web` | `WEB_SEARCH` | Green | Quick web search |
| _(none)_ | _(RAG default)_ | — | Standard RAG chat over materials |

### Design Contract
> **Slash commands are the ONLY way intent is communicated to the backend.**  
> **The backend NEVER infers or guesses intent.**

When a slash command is active:
- `intent_override: command.intent` is added to the `/chat` request body
- `CommandBadge` displayed above input
- Placeholder text changes to command-specific hint

When no slash command:
- `intent_override` field is **omitted** from request body
- Backend defaults to RAG pipeline

### Helper Functions
```js
getSlashCommand('/agent')     // → command object
getSlashCommandByIntent('AGENT') // → command object  
parseSlashCommand('/code analyze this data') // → { command, remainingMessage: 'analyze this data' }
```

---

## 13. Feature Flows

### 13.1 Auth Flow

```
Home (/) → middleware reads cookie → no cookie → /auth

AuthPage:
  Default: Login form
  Toggle to: Signup form

[Login]
  form submit → apiLogin → store token → load user → /

[Signup]
  form submit → apiSignup → auto-login → /

[Auto-refresh]
  providers.jsx → initAuth() → refreshToken → getCurrentUser → start refresh timer
```

---

### 13.2 Material Upload

```
Sidebar → Upload button → UploadDialog

[File drop/select]
  FileReader validates size client-side
  POST /upload (multipart: file, notebook_id)
  → Material created with status=pending
  → WebSocket opened: WS /ws/materials/{id}
  → SourceItem shows spinner

[Real-time updates]
  useMaterialUpdates hook receives:
  { status: "processing" }   → spinner
  { status: "embedding" }    → spinner  
  { status: "completed", 
    chunkCount: 142 }        → green check + chunk count
  { status: "failed",
    error: "OCR timeout" }   → red badge + tooltip

[Selected sources]
  Completed material → auto-added to selectedSources[]
  Failed material → not selectable
```

---

### 13.3 Chat (RAG + Intents)

```
ChatInputArea → user types message → Enter

[No slash command — RAG]
  1. POST /chat { message, material_ids: selectedSources, notebook_id, stream: true }
  2. useChatStream reads SSE:
     token events → streaming text in assistant message bubble
     citations → [1], [2] markers rendered with tooltips
     done → finalize

[/research → WEB_RESEARCH]
  Same POST + intent_override: "WEB_RESEARCH"
  SSE: research_progress → ResearchProgressPanel updates
       research_complete → ResearchReport rendered

[/code → CODE_EXECUTION]  
  Phase 1 — POST /chat + intent_override: "CODE_EXECUTION"
  SSE: code event → CodePanel shows code
       (no execution yet)
  User reviews code → clicks Run
  Phase 2 — POST /agent/execute-code
  SSE: execution_start, stdout, stderr, chart, done

[/web → WEB_SEARCH]
  POST /chat + intent_override: "WEB_SEARCH"
  SSE: web_sources → WebSources component
       tokens → summary text

[/agent → AGENT]
  POST /chat + intent_override: "AGENT"
  SSE: agent_step events → AgentStatusStrip log
       token events → final answer text
       artifacts → download links
```

---

### 13.4 Flashcard Generation

```
StudioPanel → Flashcards card → click

ConfigDialog:
  topic, card_count (default 20), difficulty, instructions
  → Generate button

POST /flashcard { material_ids, topic, card_count, difficulty }

Loading indicator in StudioPanel

Response: { flashcards: [{ front, back }] }
→ setFlashcards(result)
→ Switch to Flashcards tab
→ InlineFlashcardsView renders

[Interaction]
  Click card → flip (front ↔ back)
  Next/Prev → navigate cards
  Shuffle → randomize order
  ✓ Known / ✗ Unknown → filter remaining

[Save]
  POST /notebooks/{id}/content { type: 'flashcard', data: flashcards }
  Appears in ContentHistory
```

---

### 13.5 Quiz Generation

```
Click Quiz card → ConfigDialog (topic, count, difficulty)

POST /quiz { material_ids, topic, mcq_count, difficulty }

→ InlineQuizView renders

[Interaction]
  Question displayed with 4 options (A-D)
  Select option → Submit
  → Shows: correct/incorrect indicator + explanation
  Next question
  Final score displayed
  Review mode available

[Save] same as flashcards
```

---

### 13.6 Presentation Generation

```
Click Presentation card → ConfigDialog (slides, theme, instructions)

POST /presentation → synchronous (can take 30-90s)
Loading overlay shown

Response: { title, slide_count, html, slides[] }
→ PresentationView renders HTML
→ Slide navigation (prev/next, fullscreen)
→ Download HTML button

[Explainer Video path]
  Click "Create Explainer Video" (ExplainerDialog)
  POST /explainer/generate
  Background processing (job polling with /jobs/{id})
  When complete → InlineExplainerView shows video player
```

---

### 13.7 Mind Map Generation

```
Click Mind Map card → confirm selected materials

POST /mindmap { material_ids, notebook_id }

useMindMap generates ReactFlow nodes + dagre layout

MindMapCanvas renders:
  Root node (center) + branch nodes + leaf nodes
  Connected by edges

[Controls]
  Zoom in/out/fit
  Pan (drag)
  Click node → sends node text as chat message in ChatPanel
  Download PNG → html-to-image export

[Refresh] re-generates from same materials
[Delete] DELETE /mindmap/{id}
```

---

### 13.8 Podcast Feature

```
Click Podcast card → PodcastConfigDialog

Config:
  Mode: overview | deep-dive | debate | q-and-a | full | topic
  Topic: if mode is topic/deep-dive
  Language: dropdown (20+ languages supported)
  Host Voice: VoicePicker (with preview)
  Guest Voice: VoicePicker (with preview)
  Materials: from selectedSources

POST /podcast/session → creates session
POST /podcast/session/{id}/generate → starts pipeline

PodcastGenerating screen:
  "Generating script..." → "Generating audio..."
  WebSocket updates via usePodcastWebSocket

When ready → PodcastPlayer:
  Full transcript sidebar
  Audio controls (play/pause/seek/speed)
  Chapter navigation bar

[Interrupt / Q&A]
  Interrupt button → PodcastInterruptDrawer
  Type or speak question
  POST /podcast/session/{id}/doubt
  → AI answer text + audio plays immediately
  → Added to Q&A history

[Export]
  PodcastExportBar → PDF transcript or JSON data
  POST /podcast/session/{id}/export
  Download link appears

[Session Library]
  All past sessions listed
  Reload any session
  Delete sessions
```

---

### 13.9 Explainer Video

```
StudioPanel or Chat → ExplainerDialog

1. checkPresentations → POST /explainer/check-presentations
   → shows existing presentations for reuse

2. Configure:
   PPT language, narration language, voice gender
   (optionally reuse existing PPT or create new)

3. POST /explainer/generate → creates ExplainerVideo record

4. Poll GET /explainer/{id}/status every 3s
   Progress: "Generating presentation" → "Generating scripts" →
             "Synthesizing audio" → "Composing video"

5. When status=completed:
   InlineExplainerView → <video> player with MP4
   Chapter list
   Download button (GET /explainer/{id}/video)
```

---

### 13.10 Code Mode

```
/code slash command → ChatInputArea changes placeholder

User: "/code analyze sales trends over time"

Phase 1 — Generation:
  POST /chat { intent_override: "CODE_EXECUTION", message }
  SSE returns code event with Python code
  CodePanel renders with:
  - Syntax highlighted code
  - Edit toggle (make editable)
  - Run button (disabled until reviewed)

User reviews/edits code → clicks Run

Phase 2 — Execution:
  POST /agent/execute-code { code, notebook_id }
  SSE events:
    execution_start    → spinner
    install_progress   → "Installing seaborn..."
    stdout            → print statements shown
    chart             → matplotlib PNG rendered inline
    stderr            → error shown in red
    repair_attempt    → "Auto-repairing (1/3)..."
    done              → execution complete

Artifacts registered → download tokens → download links
CodeExecutionSession saved to DB
```

---

### 13.11 Research Mode

```
/research slash command

User: "/research latest advances in transformer attention mechanisms"

POST /chat { intent_override: "WEB_RESEARCH", message }

SSE events during research:
  query_decomposed   → sub-questions shown
  search_progress    → "Searching: sub-question N"
  sources_found      → N sources fetched
  synthesizing       → "Building report..."
  token events       → final report text streaming

ResearchProgressPanel shows:
  - Sub-question list with checkmarks
  - Source count
  - Progress percentage

ResearchReport renders:
  - Titled sections
  - Inline [n] citations
  - Sources list at bottom with URLs

ResearchSession saved to DB (report, sourcesCount, sourceUrls)
```

---

### 13.12 Agent Mode

```
/agent slash command

User: "/agent create a comprehensive analysis dashboard for my CSV data"

POST /chat { intent_override: "AGENT", message }

AgentStatusStrip renders tool steps:
  Step 1: rag_search → "Found 8 relevant chunks about dataset"
  Step 2: run_code   → "Executed analysis script"
  Step 3: create_chart → "Generated bar chart"
  Step 4: final_answer → "Here's your dashboard..."

Tool outputs visible in collapsed/expanded view
Final answer text streamed as normal chat response
Artifacts (charts, CSVs) shown inline with download links
AgentExecutionLog saved to DB
```

---

## 14. Streaming (SSE) Implementation

### Backend → Frontend SSE Format
```
data: {"type": "token", "content": "Hello"}
data: {"type": "citations", "citations": [...]}
data: {"type": "code", "content": "import pandas..."}
data: {"type": "chart", "url": "...", "token": "..."}
data: {"type": "web_sources", "sources": [...]}
data: {"type": "agent_step", "tool": "rag_search", "input": "...", "output": "..."}
data: {"type": "research_progress", "stage": "searching", "count": 5}
data: {"type": "error", "message": "..."}
data: {"type": "done"}
```

### Frontend SSE Reader (`useChatStream.js`)
```js
const response = await apiStream('/chat', { method: 'POST', body: JSON.stringify(payload) });
const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const chunk = decoder.decode(value);
  const lines = chunk.split('\n');
  
  for (const line of lines) {
    if (!line.startsWith('data: ')) continue;
    const event = JSON.parse(line.slice(6));
    
    switch (event.type) {
      case 'token': appendToLastMessage(event.content); break;
      case 'citations': setLastMessageCitations(event.citations); break;
      case 'code': setCodePanelContent(event.content); break;
      // ... etc
    }
  }
}
```

### Abort Controller
User can click "Stop" during streaming:
```js
const controller = new AbortController();
setAbortController(controller);
// fetch called with: signal: controller.signal
// On stop: controller.abort()
// → adds "[stopped]" indicator to partial message
```

---

## 15. WebSocket Integration

### Material Status Updates (`useMaterialUpdates.js`)
```
On material upload:
1. Connect: new WebSocket(`ws://api/ws/materials/{id}?token={accessToken}`)
2. onmessage: parse event → updateMaterial(id, { status, chunkCount })
3. onclose: reconnect with backoff (1s, 2s, 4s, maxRetries=5)
4. Cleanup: ws.close() on component unmount
```

### Podcast WebSocket (`usePodcastWebSocket.js`)
Used during podcast generation:
```
1. Subscribe to session updates
2. On "segment_ready": add segment to store, enable player
3. On "generation_complete": set session status to ready
4. On error: show toast notification
```

---

## 16. Theme & Styling System

### Dark Mode
- Default theme: **dark** (stored in `localStorage` as `kepler-theme`)
- Toggle in Header component
- `next-themes` with `attribute="class"` — adds `class="dark"` to `<html>`
- All Tailwind classes use `dark:` variant for dark styles

### Tailwind Configuration (`tailwind.config.js`)
- Content paths: `./src/**/*.{js,jsx}`
- Dark mode: `class` strategy
- Custom colors, fonts, animations defined as needed

### Global Styles (`styles/globals.css`)
- `@tailwind base/components/utilities`
- Custom CSS variables (colors, spacing)
- Scrollbar styling for dark theme
- Code block overrides

### Typography
- **Inter**: body text, UI elements (variable font)
- **JetBrains Mono**: code blocks, monospace contexts

---

## 17. Next.js Configuration

`next.config.mjs`:

### API Rewrites (Development Proxy)
```js
rewrites: [
  { source: '/api/presentation/slides/:path*', destination: `${backendUrl}/presentation/slides/:path*` },
  { source: '/api/:path*', destination: `${backendUrl}/:path*` }
]
```
All `/api/*` calls proxied to backend (default: `http://localhost:8000`).

### Output
```js
output: 'standalone'  // Optimized Docker builds
```

### React Strict Mode
```js
reactStrictMode: true  // Catches side effects in development
```

### Image Domains
Configured to allow backend server hostnames for `next/image`:
```js
images: { remotePatterns: [{ protocol, hostname, port }] }
```

---

## 18. Middleware

`src/middleware.js` — Next.js Edge Middleware:

```js
// Runs on: all routes except /auth/* and _next/static/*
export function middleware(request) {
  const token = request.cookies.get('refresh_token');
  const isAuthRoute = request.nextUrl.pathname.startsWith('/auth');
  
  if (!token && !isAuthRoute) {
    return NextResponse.redirect('/auth');
  }
  
  if (token && isAuthRoute) {
    return NextResponse.redirect('/');  // Already logged in
  }
  
  return NextResponse.next();
}
```

The middleware only checks for the **existence** of the cookie (not validity). Actual token validation is done in the auth service on API calls.

---

## 19. Error Handling

### Global Error Boundaries
- `app/error.jsx` — catches page-level render errors
- `app/global-error.jsx` — catches layout-level errors
- `PanelErrorBoundary` — per-panel boundary (Chat, Studio, Sidebar)

### API Error Handling
`lib/api/config.js`:
```js
if (response.status === 401) {
  onSessionExpired();  // Triggers re-auth flow
  throw new UnauthorizedError();
}
if (!response.ok) {
  const error = await response.json();
  throw new ApiError(error.detail, response.status);
}
```

### Toast Notifications
`useToastStore` used throughout:
```js
useToastStore.getState().add({ type: 'error', message: 'Failed to generate flashcards' });
useToastStore.getState().add({ type: 'success', message: 'Flashcards saved!' });
```

### Loading States
`useUIStore.setLoadingState(key, true/false)`:
- Per-feature loading keys: `'flashcards'`, `'quiz'`, `'presentation'`, `'mindmap'`
- Used to show spinners/overlays in StudioPanel

---

## 20. Build & Deployment

### Development
```bash
cd frontend
npm install
npm run dev        # Next.js dev server on :3000
```

### Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Backend API base URL |
| `NEXT_PUBLIC_API_HOST` | `localhost` | For image domain config |
| `NEXT_PUBLIC_API_PORT` | `8000` | Backend port |
| `NEXT_PUBLIC_API_PROTOCOL` | `http` | http or https |

### Production Build
```bash
npm run build      # Creates .next/standalone
npm start          # Production server
```

### Docker
`Dockerfile` (standalone output):
```dockerfile
FROM node:20-alpine
COPY .next/standalone ./
COPY .next/static ./.next/static
COPY public ./public
CMD ["node", "server.js"]
```

### Deployment Notes
- Set `NEXT_PUBLIC_API_BASE_URL` to production backend URL
- Backend must have frontend origin in `CORS_ORIGINS`
- Cookies require `COOKIE_SECURE=true` and `COOKIE_SAMESITE=none` for cross-domain (or same-domain for lax)
- `output: 'standalone'` reduces Docker image size significantly

---

*Generated from full codebase analysis — March 2026*
