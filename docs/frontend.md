# KeplerLab — Frontend Documentation

> **Application:** KeplerLab AI Learning Platform  
> **Framework:** Next.js 16 (App Router)  
> **Runtime:** React 19  
> **Styling:** Tailwind CSS + Chakra UI v3 + Framer Motion

---

## Table of Contents

1. [Overview](#1-overview)
2. [Technology Stack](#2-technology-stack)
3. [High-Level Architecture](#3-high-level-architecture)
4. [Directory Structure](#4-directory-structure)
5. [Routing & Pages](#5-routing--pages)
6. [Authentication Flow](#6-authentication-flow)
7. [State Management (Zustand)](#7-state-management-zustand)
8. [API Layer (lib/api)](#8-api-layer-libapi)
9. [Components — Layout](#9-components--layout)
10. [Components — Chat Panel](#10-components--chat-panel)
11. [Components — Studio Panel](#11-components--studio-panel)
12. [Components — Notebook Sidebar](#12-components--notebook-sidebar)
13. [Components — Presentation Viewer](#13-components--presentation-viewer)
14. [Components — Mind Map Canvas](#14-components--mind-map-canvas)
15. [Components — Podcast Studio](#15-components--podcast-studio)
16. [Components — UI Primitives](#16-components--ui-primitives)
17. [Hooks](#17-hooks)
18. [Slash Commands](#18-slash-commands)
19. [Theming & Dark Mode](#19-theming--dark-mode)
20. [Middleware (Auth Guard)](#20-middleware-auth-guard)
21. [Real-time Updates (WebSocket)](#21-real-time-updates-websocket)
22. [SSE Streaming (Chat)](#22-sse-streaming-chat)
23. [Data Flow Diagrams](#23-data-flow-diagrams)

---

## 1. Overview

KeplerLab's frontend is a **Next.js 16 App Router** application that serves as the interactive learning interface. Users can:

- Upload and manage study materials (files, URLs, YouTube, text)
- Chat with an AI agent about their materials using natural language
- Generate flashcards, quizzes, PowerPoint presentations, and mind maps
- Listen to AI-generated live podcasts based on their materials
- Run code and see live charts in the chat interface
- Conduct deep web research with structured reports and inline citations

The entire app is a **dark-first single-page-app experience** with a three-panel layout: sidebar (materials), chat (AI conversation), and studio (content generation).

---

## 2. Technology Stack

| Category | Technology |
|----------|-----------|
| **Framework** | Next.js 16.1.6 (App Router) |
| **Runtime** | React 19.2.3 |
| **Language** | JavaScript (JSX) |
| **Styling** | Tailwind CSS 3.4 |
| **Component Library** | Chakra UI v3 (layout primitives) |
| **Animation** | Framer Motion 12 |
| **State Management** | Zustand v5 |
| **Themes** | next-themes 0.4.6 |
| **Markdown Rendering** | react-markdown 10 + remark-gfm + remark-math |
| **Math Rendering** | KaTeX + rehype-katex |
| **Syntax Highlighting** | react-syntax-highlighter |
| **Canvas / Diagrams** | @xyflow/react 12 (React Flow) + dagre (auto-layout) |
| **Icons** | lucide-react 0.576 |
| **PDF Export** | jspdf |
| **Image Export** | html-to-image |
| **Audio** | Web Audio API + HTML5 `<Audio>` |
| **Build** | Next.js SWC compiler |
| **Linting** | ESLint + eslint-config-next |

---

## 3. High-Level Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                  Browser (Client-Side App)                     │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                  Next.js App Router                      │ │
│  │                                                          │ │
│  │  /                ← Dashboard (notebook list)            │ │
│  │  /auth            ← Login / Signup                       │ │
│  │  /notebook/[id]   ← Main workspace                       │ │
│  │  /view            ← Shared view (public)                 │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │   Sidebar    │  │  Chat Panel  │  │    Studio Panel      │ │
│  │ (materials)  │  │  (AI agent)  │  │  (generate content)  │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              State Management (Zustand)                  │ │
│  │  useAppStore  useAuthStore  usePodcastStore  useToast    │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              API Layer (lib/api/)                        │ │
│  │   auth.js  chat.js  generation.js  notebooks.js          │ │
│  │   materials.js  podcast.js  mindmap.js  agent.js         │ │
│  └───────────────────────────┬──────────────────────────────┘ │
└───────────────────────────────│────────────────────────────────┘
                                │ HTTP / SSE / WebSocket
                                │
┌───────────────────────────────▼────────────────────────────────┐
│             FastAPI Backend (localhost:8000)                   │
└────────────────────────────────────────────────────────────────┘
```

---

## 4. Directory Structure

```
frontend/
├── public/                         # Static assets, favicon
├── src/
│   ├── middleware.js                # Edge auth guard (refresh cookie check)
│   ├── styles/
│   │   └── globals.css             # Tailwind base + custom CSS variables
│   ├── app/                        # Next.js App Router pages
│   │   ├── layout.jsx              # Root layout (fonts, dark mode, Providers)
│   │   ├── providers.jsx           # ThemeProvider + ChakraUI + AuthInitializer
│   │   ├── page.jsx                # / — Dashboard (notebook list)
│   │   ├── loading.jsx             # Global loading fallback
│   │   ├── error.jsx               # Global error boundary
│   │   ├── not-found.jsx           # 404 page
│   │   ├── global-error.jsx        # Root-level error boundary
│   │   ├── auth/                   # /auth — Login/Signup
│   │   ├── notebook/
│   │   │   └── [id]/
│   │   │       ├── layout.jsx      # Notebook layout wrapper
│   │   │       └── page.jsx        # /notebook/[id] — Main workspace
│   │   └── view/
│   │       └── page.jsx            # /view — Public shared view
│   ├── components/
│   │   ├── auth/                   # Login + Signup forms
│   │   ├── chat/                   # Full chat system
│   │   │   ├── ChatPanel.jsx       # Main orchestrator (1200+ lines)
│   │   │   ├── ChatMessage.jsx     # Individual message renderer
│   │   │   ├── MarkdownRenderer.jsx # Full-featured markdown with streaming
│   │   │   ├── AgentActionBlock.jsx # Collapsible agent step block
│   │   │   ├── AgentStepsPanel.jsx  # Animated steps timeline
│   │   │   ├── AgentThinkingBar.jsx # "Thinking..." animation bar
│   │   │   ├── CodeReviewBlock.jsx  # Code block with run/copy actions
│   │   │   ├── ChartRenderer.jsx    # Data-URI chart renderer
│   │   │   ├── ExecutionPanel.jsx   # Code execution output panel
│   │   │   ├── ResearchProgress.jsx # 5-phase research progress
│   │   │   ├── SlashCommandDropdown.jsx # /command autocomplete picker
│   │   │   ├── SlashCommandPills.jsx # Active command badge
│   │   │   ├── CommandBadge.jsx     # Individual command tag
│   │   │   ├── SuggestionDropdown.jsx # Autocomplete suggestions
│   │   │   ├── ChatHistoryModal.jsx  # Session history browser
│   │   │   ├── ChatEmptyState.jsx    # Quick action buttons (empty state)
│   │   │   ├── DocumentPreview.jsx   # Material citation preview
│   │   │   ├── GeneratedFileCard.jsx # Generated file download card
│   │   │   ├── MiniBlockChat.jsx     # Per-block follow-up mini chat
│   │   │   ├── BlockHoverMenu.jsx    # Hover actions on message blocks
│   │   │   ├── CopyButton.jsx       # Copy-to-clipboard button
│   │   │   └── slashCommands.js     # Slash command definitions + parser
│   │   ├── layout/
│   │   │   ├── Header.jsx           # Top navigation bar
│   │   │   └── Sidebar.jsx          # Material list + upload panel
│   │   ├── mindmap/
│   │   │   └── MindMapCanvas.jsx    # React Flow mind map renderer
│   │   ├── notebook/
│   │   │   ├── SourceItem.jsx       # Single material list item
│   │   │   ├── UploadDialog.jsx     # File/URL/YouTube/text upload modal
│   │   │   └── WebSearchDialog.jsx  # Add web source dialog
│   │   ├── podcast/
│   │   │   ├── PodcastStudio.jsx    # Full podcast player + controls
│   │   │   ├── PodcastConfigDialog.jsx # Session creation modal
│   │   │   └── ...
│   │   ├── presentation/
│   │   │   └── PresentationView.jsx # Slide deck viewer + explainer
│   │   ├── studio/
│   │   │   ├── StudioPanel.jsx      # Right panel (tabs: Quiz/Flash/PPT/Podcast/Map)
│   │   │   ├── FeatureCard.jsx      # Individual feature tile
│   │   │   ├── InlineFlashcardsView.jsx # Flashcard flipper
│   │   │   ├── InlineQuizView.jsx   # Interactive quiz
│   │   │   ├── InlineExplainerView.jsx  # Explainer video player
│   │   │   ├── ExplainerDialog.jsx  # Explainer generation config
│   │   │   ├── ConfigDialogs.jsx    # Flashcard/Quiz config modals
│   │   │   ├── ContentHistory.jsx   # Generated content history list
│   │   │   └── HistoryRenameModal.jsx # Rename generated content
│   │   ├── ui/
│   │   │   ├── ErrorBoundary.jsx    # Panel-level error isolation
│   │   │   ├── ToastContainer.jsx   # Toast notification renderer
│   │   │   ├── ConfirmDialog.jsx    # Generic confirm dialog
│   │   │   └── ...
│   │   └── viewer/                 # Shared/public content viewer
│   ├── hooks/
│   │   ├── useMaterialUpdates.js   # WebSocket listener for material status
│   │   ├── useMicInput.js          # Microphone input hook
│   │   ├── useMindMap.js           # Mind map state + API integration
│   │   ├── usePodcast.js           # Podcast combined hook (store + context)
│   │   ├── usePodcastPlayer.js     # Audio playback control hook
│   │   ├── usePodcastWebSocket.js  # Podcast-specific WebSocket events
│   │   └── useResizablePanel.js    # Drag-to-resize panel hook
│   ├── lib/
│   │   ├── api/
│   │   │   ├── config.js           # Fetch utils, token management, auto-refresh
│   │   │   ├── auth.js             # login, signup, logout, getCurrentUser, refresh
│   │   │   ├── chat.js             # streamChat, getChatHistory, sessions, research
│   │   │   ├── generation.js       # generateFlashcards, generateQuiz, generatePresentation
│   │   │   ├── notebooks.js        # CRUD notebooks + generated content
│   │   │   ├── materials.js        # upload, URL, YouTube, delete, status polling
│   │   │   ├── mindmap.js          # generateMindMap
│   │   │   ├── podcast.js          # Full podcast lifecycle API
│   │   │   ├── agent.js            # Direct agent API
│   │   │   ├── jobs.js             # Background job status
│   │   │   └── explainer.js        # Explainer video API
│   │   ├── chakra/
│   │   │   └── provider.jsx        # Chakra UI theme provider
│   │   └── utils/
│   │       ├── helpers.js          # generateId, formatRelativeDate, readSSEStream
│   │       └── constants.js        # Panel dimensions, timers, quick actions
│   └── stores/
│       ├── useAppStore.js          # Master app state (notebook, materials, chat)
│       ├── useAuthStore.js         # Auth state + token lifecycle
│       ├── usePodcastStore.js      # Podcast session + playback state
│       ├── useToastStore.js        # Toast notification queue
│       └── useConfirmStore.js      # Confirm dialog state
├── tailwind.config.js
├── next.config.mjs
├── jsconfig.json                   # Path aliases (@/ → src/)
└── package.json
```

---

## 5. Routing & Pages

The app uses the **Next.js App Router** with file-system-based routes. Authentication is enforced at the Edge via `middleware.js`.

### Route Map

| URL | Page | Description |
|-----|------|-------------|
| `/` | `app/page.jsx` | Dashboard — lists all user notebooks, create/edit/delete |
| `/auth` | `app/auth/page.jsx` | Login / Signup UI |
| `/notebook/[id]` | `app/notebook/[id]/page.jsx` | Main workspace (sidebar + chat + studio) |
| `/notebook/draft` | Same page, `id=draft` | Draft mode for new notebooks before saving |
| `/view` | `app/view/page.jsx` | Public shared content viewer |

### Page: Dashboard (`/`)

Main entry point after login. Features:
- **Notebook grid** — displays all user notebooks with creation date
- **Create notebook** — auto-generates AI name, then user can rename
- **Context menu** per notebook — rename, delete with confirm dialog
- **Theme toggle** (dark/light)
- **User menu** — logout
- Navigation to `/notebook/[id]` on click

### Page: Auth (`/auth`)

- **Login form** — email + password → access token + refresh cookie
- **Signup form** — email + username + password (with validation)
- Redirects back to `?redirect=` path on success

### Page: Notebook (`/notebook/[id]`)

Three-column responsive workspace:

```
┌──────────────┬──────────────────────────┬───────────────────┐
│   Sidebar    │       Chat Panel         │   Studio Panel    │
│  (320px)     │   (remaining width)      │   (360px)         │
│              │                          │                   │
│  Materials   │  Message history         │  Flashcards       │
│  Upload      │  Text input              │  Quiz             │
│  Source list │  Agent steps             │  Presentation     │
│              │  Research progress       │  Mind Map         │
│              │  Code blocks             │  Podcast          │
└──────────────┴──────────────────────────┴───────────────────┘
```

- Both sidebar and studio are **lazy-loaded** (`next/dynamic`) to avoid blocking initial paint
- Each panel is wrapped in a `PanelErrorBoundary` to prevent full-page crashes
- Mobile: sidebar slides in as overlay, studio hidden/toggled

---

## 6. Authentication Flow

### Initial Load (Token Hydration)

```
App mounts → Providers.jsx → AuthInitializer.useEffect
    │
    ▼
useAuthStore.initAuth()
    │
    ├── POST /auth/refresh (credentials: 'include')
    │     └── Backend reads HttpOnly refresh cookie
    │     └── Returns new access_token
    │
    ├── syncToken → setAccessToken (in-memory, module-level ref)
    │
    ├── GET /auth/me (with Bearer token)
    │     └── Returns user profile
    │
    ├── set({ user, isAuthenticated: true })
    │
    └── scheduleRefresh() → setTimeout(13 min) for next silent refresh
```

**Deduplication:** `_initPromise` ensures only one `initAuth` runs even with React StrictMode double-invoke.

### Silent Token Refresh

```
Token expiry in 15 min, refresh scheduled at 13 min
    │
    ▼
setTimeout fires → POST /auth/refresh
    │
    ├── New access_token received
    ├── syncToken (update in-memory ref)
    └── scheduleRefresh again (recursive)
```

### Token Injection on API Calls

Every API call goes through `apiFetch()` in `config.js`:
```
apiFetch() → adds "Authorization: Bearer <token>" header
           → on 401 response → _refreshTokenOnce() (deduplicated)
           → retry original request with new token
           → on repeated 401 → _handleSessionExpiry() → redirect to /auth
```

### Session Expiry

When refresh fails:
1. In-memory token cleared
2. `_onSessionExpired` callback fires (registered by auth store)
3. If on a protected page → `window.location.href = '/auth'`

### Middleware Auth Guard (`middleware.js`)

Edge middleware runs before every request:

```javascript
PUBLIC_PREFIXES = ['/auth', '/view', '/api']

// All other routes:
if (!request.cookies.get('refresh_token')) {
  redirect('/auth?redirect=<pathname>')
}
```

This protects all pages at the **network layer** before any client-side code runs.

---

## 7. State Management (Zustand)

The app uses **Zustand v5** for global state. All stores are module-level singletons with no Context provider needed.

### `useAppStore` — Master Application State

The central store for the notebook workspace.

**State Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `currentNotebook` | Object | Loaded notebook (`{id, name, isDraft}`) |
| `draftMode` | boolean | True when in `/notebook/draft` |
| `materials` | Array | List of materials in notebook |
| `currentMaterial` | Object | Currently focused material |
| `selectedSources` | Set<string> | Set of material IDs selected for AI context |
| `sessionId` | string | Current chat session UUID |
| `messages` | Array | Chat message history |
| `flashcards` | Object | Latest generated flashcards |
| `quiz` | Object | Latest generated quiz |
| `notes` | Array | User notes |
| `activePanel` | string | `'chat'` or `'studio'` |
| `loading` | Object | Loading state map by key |
| `pendingChatMessage` | string | Bridged message from Mind Map → Chat |

**Key Actions:**

| Action | Description |
|--------|-------------|
| `setCurrentNotebook` | Switch active notebook |
| `setMaterials` | Replace material list |
| `addMaterial` | Add single material |
| `toggleSourceSelection(id)` | Toggle material in AI context |
| `selectAllSources` | Select all materials |
| `addMessage(role, content)` | Append chat message |
| `clearMessages` | Reset chat + session |
| `resetForNotebookSwitch` | Full reset when changing notebooks |
| `setLoadingState(key, bool)` | Per-key loading control |

### `useAuthStore` — Authentication State

| Field | Type | Description |
|-------|------|-------------|
| `user` | Object | `{id, email, username, role}` |
| `isAuthenticated` | boolean | Login state |
| `isLoading` | boolean | During initial token hydration |

**Actions:** `login`, `signup`, `logout`, `initAuth`, `scheduleRefresh`

Internal module refs (non-serialized):
- `_refreshTimer` — `setTimeout` handle for auto-refresh
- `_accessTokenRef` — Current access token (not stored in Zustand state to prevent re-renders)

### `usePodcastStore` — Podcast Playback State

Management of the full podcast lifecycle:

| Field | Type | Description |
|-------|------|-------------|
| `session` | Object | Current podcast session |
| `sessions` | Array | All user podcast sessions |
| `segments` | Array | Audio segments |
| `chapters` | Array | Chapter markers |
| `doubts` | Array | Q&A doubts |
| `bookmarks` | Array | User bookmarks |
| `annotations` | Array | User notes |
| `currentSegmentIndex` | number | Playback position |
| `isPlaying` | boolean | Audio playing state |
| `playbackSpeed` | number | 0.5x – 2x |
| `phase` | string | `idle → generating → player` |
| `_audioEl` | Audio | HTML5 Audio element (non-serialized) |
| `_audioCache` | Map | Blob URL cache for segments |

### `useToastStore` — Toast Notifications

Simple queue-based toast system:

```javascript
const toast = useToast();
toast.success('Saved!');
toast.error('Upload failed');
toast.info('Processing...');
```

### `useConfirmStore` — Confirm Dialog

Global confirm dialog with promise-based API:

```javascript
const confirm = useConfirm();
const confirmed = await confirm({ title: 'Delete?', message: 'This is permanent' });
```

---

## 8. API Layer (`lib/api`)

All API calls are centralized in `lib/api/`. Every module uses `apiFetch` or `streamFetch` from `config.js`.

### `config.js` — Core Fetch Utilities

**Core function:** `apiFetch(path, options)`
- Adds `Authorization: Bearer <token>` header
- On 401 → silent token refresh → retry → session expire
- Throws structured errors with `.status` and `.data`

**Streaming:** `fetchSSE(path, options)` for Server-Sent Events

**Audio:** `fetchAudioObjectUrl(url)` with auth headers → returns Blob URL for podcast segments

### Token Refresh Deduplication

Multiple concurrent API calls that all get 401 are handled via promise deduplication:
```javascript
let _refreshPromise = null;

function _refreshTokenOnce() {
  if (!_refreshPromise) {
    _refreshPromise = _doRefresh().finally(() => { _refreshPromise = null; });
  }
  return _refreshPromise;
}
```
Only one refresh request fires regardless of how many concurrent 401 responses arrive.

### API Modules

#### `auth.js`
```javascript
login(email, password)     // → {access_token}
signup(email, username, password)
logout()
getCurrentUser(token?)     // → {id, email, username, role}
refreshToken()             // → {access_token}
```

#### `chat.js`
```javascript
streamChat(payload, onChunk, signal)    // SSE streaming
getChatHistory(notebookId, sessionId)   // → [{role, content}]
streamResearch(payload, onChunk)        // Research SSE
getSuggestions(partial, notebookId)     // Autocomplete
getChatSessions(notebookId)             // → [sessions]
createChatSession(notebookId, title)    // → session
deleteChatSession(sessionId)
```

#### `generation.js`
```javascript
generateFlashcards(notebookId, materialIds, count, language)
generateQuiz(notebookId, materialIds, count, difficulty, language)
generatePresentation(notebookId, materialIds, options)
```

#### `notebooks.js`
```javascript
getNotebooks()                          // → [notebooks]
getNotebook(id)                         // → notebook
createNotebook(name, description)
updateNotebook(id, data)
deleteNotebook(id)
saveGeneratedContent(notebookId, type, data, materialIds)
getGeneratedContent(notebookId, type)
deleteGeneratedContent(id)
updateGeneratedContent(id, data)
```

#### `materials.js`
```javascript
getMaterials(notebookId?)              // → [materials]
uploadFile(file, notebookId, onProgress)
uploadUrl(url, notebookId)
uploadYouTube(url, notebookId)
uploadText(text, title, notebookId)
deleteMaterial(id)
updateMaterial(id, data)
getMaterialFileUrl(id)                 // → file token URL
```

#### `podcast.js`
```javascript
createPodcastSession(config)
listPodcastSessions(notebookId)
getPodcastSession(sessionId)           // → {session, segments, chapters}
startPodcastGeneration(sessionId)
submitPodcastQuestion(sessionId, data)
addPodcastBookmark(sessionId, data)
addPodcastAnnotation(sessionId, data)
triggerPodcastExport(sessionId, format) // 'pdf' | 'json'
generatePodcastSummary(sessionId)
deletePodcastSession(sessionId)
```

---

## 9. Components — Layout

### `Header.jsx`

Top navigation bar present on the notebook page:
- KeplerLab logo / back-to-dashboard button
- Current notebook name (editable inline)
- Theme toggle (dark/light)
- User avatar dropdown (logout)

### `Sidebar.jsx`

Left panel (320px default, resizable). Contains:

**Material List:**
- Each material shown as a `SourceItem` with:
  - Status badge: `pending / processing / completed / failed` (with animated spinner)
  - Checkbox for including in AI context
  - File type icon
  - Title / filename display
  - Context menu: rename, delete, download original

**Action Bar:**
- Upload button → opens `UploadDialog`
- "Select All / Deselect All" toggles
- Material count badge
- Source type filters

**UploadDialog:**
- Four tabs: **File**, **URL**, **YouTube**, **Text**
- File: drag-and-drop zone + file browser, accepts PDF/DOCX/PPT/images/audio/video/CSV/Excel
- URL: input with validation, web scraping
- YouTube: URL input, extracts transcript
- Text: raw text paste with title
- Shows upload progress bar
- Posts to `/upload`, `/upload/url`, `/upload/youtube`, `/upload/text`

---

## 10. Components — Chat Panel

**`ChatPanel.jsx`** is the largest component (~1200 lines). It orchestrates the entire chat interface.

### Message Types Rendered

| Content | Component | Trigger |
|---------|-----------|---------|
| Plain markdown | `MarkdownRenderer` | All assistant messages |
| Code block | `CodeReviewBlock` | Code in markdown |
| Data chart | `ChartRenderer` | `data:image/png;base64` in response |
| Agent steps | `AgentActionBlock` | When `agent_meta.tools_used` present |
| Research progress | `ResearchProgress` | RESEARCH intent in-flight |
| Agent thinking | `AgentThinkingBar` | While agent is active |
| Generated file | `GeneratedFileCard` | File generation responses |
| Document preview | `DocumentPreview` | Citation references |

### Input Area

- **Text input** with auto-resize
- **Slash command support** (`/agent`, `/web`, `/code`) — dropdown picker on `/` key
- **Active command pill** shown above input when slash command selected
- **Quick action buttons** (Summarize, Explain, Key Points, Study Guide)
- **Microphone button** — `useMicInput` → speech-to-text
- **Send button** or Enter to submit

### Streaming Flow

```javascript
streamChat({message, material_ids, notebook_id, session_id, intent_override})
    │
    ▼
readSSEStream(response, (event) => {
    switch(event.type) {
        case 'agent_step':  // update live step text + show AgentThinkingBar
        case 'token':       // append to streaming message buffer
        case 'citations':   // store citation array
        case 'agent_meta':  // update final message metadata
        case 'done':        // finalize message, add to store
        case 'error':       // show error toast
    }
})
```

**Token buffering:** Streaming tokens are buffered per-frame to prevent excessive React re-renders.

### `MarkdownRenderer.jsx`

Full-featured markdown renderer with streaming support:
- **GFM** (tables, strikethrough, task lists)
- **Math** (inline `$...$` and block `$$...$$` via KaTeX)
- **Code highlighting** via `react-syntax-highlighter` (Dracula / GitHub Light theme per darkMode)
- **Streaming sanitizer** (`sanitizeStreamingMarkdown`) — fixes incomplete markdown mid-stream
- **Code blocks** — injected with copy button + language badge
- **Raw HTML** support via rehype-raw

### `AgentActionBlock.jsx`

Collapsible block showing agent reasoning steps:
- Tool used + icon (search, code, research, etc.)
- Input query or code snippet
- Output preview (truncated)
- Expand/collapse toggle
- Timeline visualization

### `CodeReviewBlock.jsx`

Interactive code block with:
- Syntax highlighted code
- Copy button
- "Run" button (for Python code) → sends to execution endpoint
- Output panel with stdout/stderr
- Chart display if code produces matplotlib output
- Code repair feedback if execution fails

### `ResearchProgress.jsx`

5-phase progress tracker for web research:
1. Understanding query
2. Searching sources
3. Analyzing results
4. Cross-referencing
5. Writing report

Each phase animates from `pending → active → complete`.

### `ChartRenderer.jsx`

Renders base64-encoded PNG charts from code execution:
- Detects `data:image/png;base64,` prefix
- Renders as `<img>` with download button
- Fullscreen expand option

### `ChatHistoryModal.jsx`

Session browser modal:
- Lists all chat sessions for the current notebook
- Shows session title + creation date
- Click to switch session
- Delete session with confirm

### Slash Commands

Three active commands accessible via `/` prefix:

| Command | Intent Sent | Description | Color |
|---------|-------------|-------------|-------|
| `/agent` | `AGENT_TASK` | Autonomous multi-step executor | Orange |
| `/web` | `WEB_RESEARCH` | 5-phase structured web research | Blue |
| `/code` | `CODE_GENERATION` | Generate code (no auto-run) | Purple |

After typing `/`, a `SlashCommandDropdown` shows all commands. On selection, a `CommandBadge` pill appears above the input and `intent_override` is sent to the backend.

---

## 11. Components — Studio Panel

**`StudioPanel.jsx`** is the right panel with tabs for all content generation features.

### Tabs

| Tab | Icon | Component |
|-----|------|-----------|
| Flashcards | ClipboardCheck | `InlineFlashcardsView` |
| Quiz | Monitor | `InlineQuizView` |
| Presentation | Layers | `InlinePresentationView` |
| Explainer | Video | `InlineExplainerView` |
| Podcast | Mic | `PodcastStudio` |
| Mind Map | Network | `MindMapCanvas` |

All heavy panels (`PresentationView`, `PodcastStudio`, `MindMapCanvas`) are **lazily loaded** via `next/dynamic` to avoid bundle bloat.

### Feature Cards

When no content is generated, each tab shows a `FeatureCard` with:
- Feature icon + title + description
- Configuration options (count, difficulty, language)
- Generate button

### `InlineFlashcardsView`

- Card flip animation (CSS perspective transform)
- Progress indicator (card X of Y)
- Keyboard navigation (arrow keys)
- Shuffle mode
- Save to notebook
- Download as PDF (`jspdf`)

### `InlineQuizView`

- One question at a time
- 4 answer options (radio buttons)
- "Check" reveals correct/wrong with explanation
- Progress bar
- Score summary at end
- Restart option

### `ContentHistory`

History panel showing all previously generated content per type:
- List with title + creation date
- Click to reload into current view
- Delete with confirm
- Rename (`HistoryRenameModal`)

### `ExplainerDialog`

Configuration for generating explainer videos from slides:
- Language selection
- Narration voice (host gender)
- Duration control

---

## 12. Components — Notebook Sidebar

### `SourceItem.jsx`

A single material entry in the sidebar list:
- **Left**: Checkbox for AI context inclusion
- **Center**: File type icon + title/filename + source type badge
- **Right**: Status badge with icon
  - `completed` → green checkmark
  - `processing` → animated spinner
  - `failed` → red warning icon
  - `pending` → clock icon
- **Hover actions**: Delete button, download button

Status colors:
```
completed  → text-emerald-500
processing → text-accent (animated pulse)
failed     → text-error
pending    → text-text-muted
```

### `UploadDialog.jsx`

Modal with four upload modes:

**File Upload tab:**
- Drag-and-drop with visual feedback
- File type validation (client-side extension check + displays supported types)
- Progress bar via `xhr.upload.onprogress`
- Error messages (size exceeded, type not supported)

**URL tab:**
- URL validation
- Optional title override
- Calls `POST /upload/url`

**YouTube tab:**
- YouTube URL validation (regex)
- Shows extracted video ID preview
- Calls `POST /upload/youtube`

**Text tab:**
- Large textarea for raw content
- Required title field
- Calls `POST /upload/text`

---

## 13. Components — Presentation Viewer

**`PresentationView.jsx`** renders the generated PowerPoint in-browser.

### Features

- Full slide navigation (prev/next + keyboard arrow keys)
- Slide thumbnail strip
- Fullscreen mode
- Download `.pptx` button
- Share link generation
- **Explainer trigger** — button to generate narrated explainer video from slides

### Slide Rendering

Slides are rendered as HTML divs using the JSON structure from the backend:
- Title + bullet points
- Background gradients from slide metadata
- Speaker notes shown below slide
- Slide number indicator

### `PresentationConfigDialog`

Before generation:
- Language selector (25+ languages)
- Slide count (5–20)
- Presentation style (academic, business, casual)
- Source material multi-select

---

## 14. Components — Mind Map Canvas

**`MindMapCanvas.jsx`** uses **React Flow** (@xyflow/react) + **dagre** auto-layout.

### Features

- Auto-arranged hierarchical layout (dagre tree layout)
- Zoom + pan
- Node click → shows detail tooltip
- **Chat bridge**: double-click a node → pre-fills chat input with that topic
- Export as PNG (`html-to-image`)
- Light/dark aware node colors

### Node Types

| Level | Style | Example |
|-------|-------|---------|
| Root (0) | Large, accent color | Main topic |
| Level 1 | Medium, primary | Main branches |
| Level 2+ | Small, surface | Sub-topics |

### Layout Algorithm

```
dagre.layout(graph, {
  rankdir: 'TB',        // top-to-bottom
  nodesep: 60,
  ranksep: 120,
})
```

React Flow `fitView` animates into position after layout calculation.

### Mind Map → Chat Bridge

```javascript
// When user clicks "Ask about this" on a node:
useAppStore.setState({ pendingChatMessage: node.label })
// ChatPanel watches pendingChatMessage and auto-fills + submits
```

---

## 15. Components — Podcast Studio

**`PodcastStudio.jsx`** is the complete interactive podcast player.

### Session Creation (`PodcastConfigDialog`)

Configuration options:
- **Mode**: Overview / Deep-dive / Debate / Q&A / Full coverage
- **Language**: 15+ supported languages
- **Topic** (optional override)
- **Host voice**: Male/Female selector with preview playback
- **Guest voice**: Male/Female selector with preview playback
- **Materials**: Multi-select from notebook sources

### Generation Phase

```
User clicks "Generate Podcast"
    │
    ▼
POST /podcast/sessions (creates DB record)
    │
    ▼
POST /podcast/sessions/{id}/start (triggers backend generation)
    │
    ▼
usePodcastWebSocket polls session status
    │
    ├── phase='script_generating' → shows script animation
    ├── phase='audio_generating'  → shows audio bars animation  
    └── phase='ready'             → transition to player

Player loads first segment, begins progressive streaming
```

### Player Features

- Custom audio controls (not native `<audio>` HTML controls)
- Host/Guest speaker indicator with color coding
- **Transcript view** — highlighted as audio plays
- Chapter navigation (jump to chapter)
- Playback speed: 0.5x / 0.75x / 1x / 1.25x / 1.5x / 2x
- **Interrupt Q&A** (pause → ask question → AI responds with audio)
- Bookmark current segment
- Add text annotation to a segment
- Export as PDF (transcript) or JSON (data)

### Audio Cache System

```javascript
// Podcast segments are cached as Blob URLs:
_audioCache: new Map()  // segment index → blob URL

fetchAudioObjectUrl(url)  // authenticated fetch → Blob URL
URL.revokeObjectURL(url)  // cleanup on session end
```

Pre-fetching: Next 2 segments are pre-fetched while current segment plays.

### Doubt / Q&A System

```
User presses "Interrupt" button (pauses audio)
    │
    ▼
Modal opens: type question or use microphone
    │
    ▼
POST /podcast/sessions/{id}/doubts
    │
    ├── Backend: RAG search + LLM answer + TTS
    └── Returns: answerText + answerAudioUrl
    │
    ▼
Audio answer plays in-panel
satisfaction_detector checks if question was resolved
```

---

## 16. Components — UI Primitives

### `ToastContainer.jsx`

Positioned at bottom-right. Manages queue of toasts with:
- Auto-dismiss (2500ms default)
- Manual dismiss
- Types: success (green), error (red), info (blue), warning (yellow)
- Slide-in animation

### `ConfirmDialog.jsx`

Global modal dialog driven by `useConfirmStore`:
```javascript
// Usage:
const { confirm } = useConfirm();
const ok = await confirm({
  title: 'Delete Notebook?',
  message: 'This action cannot be undone.',
  confirmLabel: 'Delete',
  variant: 'danger',
});
```

### `ErrorBoundary.jsx` (`PanelErrorBoundary`)

Wraps each major panel. On React rendering error:
- Shows friendly error card instead of white screen
- "Retry" button calls `reset()`
- Error details in development mode

---

## 17. Hooks

### `useMaterialUpdates.js`

Connects to the backend WebSocket (`/ws/jobs/{user_id}?token=<jwt>`) and listens for material processing events:

```javascript
useMaterialUpdates(userId, onUpdate)
    │
    ├── Connects WebSocket with exponential backoff reconnection
    ├── MAX BACKOFF: 30 seconds
    │
    ├── On 'material_update' event:
    │     └── Updates materials in useAppStore
    │     └── Triggers re-render of SourceItem status badge
    │
    └── Handles ping/pong keepalive
```

### `useMicInput.js`

Speech-to-text using `webkitSpeechRecognition` / `SpeechRecognition` API:
- Start/stop recording
- Transcription → fills chat input
- Error handling (no microphone permission)

### `useMindMap.js`

Mind map state management hook:
- Calls `generateMindMap` API
- Transforms backend response to React Flow node/edge format
- Applies dagre layout
- Exposes zoom/pan controls
- Export to PNG

### `usePodcast.js`

Convenience wrapper combining `usePodcastStore` + `useAppStore`:
- Exposes all podcast actions
- Injects `currentNotebook.id` and `selectedSources` automatically:
```javascript
const { create, loadSessions, ...rest } = usePodcast();
// create() automatically uses currentNotebook.id
```

### `usePodcastPlayer.js`

Low-level audio playback management:
- Controls `_audioEl` (HTML5 Audio)
- Binds `ended`, `timeupdate`, `error` events
- Handles segment transitions (plays next segment on `ended`)
- Progress tracking

### `usePodcastWebSocket.js`

WebSocket channel for podcast session status polling:
- Connects when session is in generating phases
- Processes `podcast_progress` events from backend
- Updates `usePodcastStore.generationProgress`
- Handles reconnection on disconnect

### `useResizablePanel.js`

Drag-handle based panel resizing:
- Attaches `mousemove` during drag
- Clamps width to `[MIN_WIDTH, MAX_WIDTH]`
- Persists width in `localStorage`

---

## 18. Slash Commands

Three active slash commands transform the chat mode:

### `/agent` (orange)

**Intent:** `AGENT_TASK`

Routes to the autonomous agent sub-graph. The agent:
1. Plans a multi-step execution
2. Calls multiple tools in sequence
3. Has access to: RAG, web research, code execution, file generation
4. Reports each step with animated step cards

Example: `/agent analyze my CSV, find trends and create a presentation`

### `/web` (blue)

**Intent:** `WEB_RESEARCH`

Triggers 5-phase structured web research:
1. Query understanding
2. Source search (external search service)
3. Source analysis
4. Cross-referencing
5. Report synthesis with inline citations

Shows animated `ResearchProgress` component during research.

### `/code` (purple)

**Intent:** `CODE_GENERATION`

Generates code with explanation. Key difference from natural code requests:
- Code is **shown in a CodeReviewBlock** but NOT auto-executed
- User explicitly clicks "Run" to execute
- Allows review before execution

### Slash Command UX Flow

```
User types "/" in chat input
    │
    ▼
SlashCommandDropdown appears (keyboard navigable)
    │
    ▼
User selects /agent (or types full command)
    │
    ▼
CommandBadge pill appears above input showing "Agent mode"
intent_override = "AGENT_TASK" stored in component state
    │
    ▼
User types message + submits
    │
    ▼
{message, intent_override: "AGENT_TASK"} → POST /chat
```

---

## 19. Theming & Dark Mode

### Theme System

- **Provider**: `next-themes` with `attribute="class"` (toggles `dark` class on `<html>`)
- **Storage**: `localStorage['kepler-theme']`
- **Default**: `dark`
- **FOUC Prevention**: Inline `<script>` in `<head>` reads storage and applies class before first paint

### Tailwind Dark Mode

All component styles use Tailwind's `dark:` variants:
```html
<div class="bg-surface dark:bg-surface-dark text-text dark:text-text-dark">
```

Custom CSS variables defined in `globals.css`:
```css
:root {
  --color-surface: ...;
  --color-accent: ...;
  --color-text: ...;
}
.dark {
  --color-surface: ...;
  --color-accent: ...;
}
```

### Fonts

Loaded via `next/font/google`:
- **Inter** — UI text (variable: `--font-inter`)
- **JetBrains Mono** — Code blocks (variable: `--font-jetbrains`)

### Chakra UI Integration

Chakra UI v3 is used alongside Tailwind for complex layout components. A custom `ChakraUIProvider` wraps the app and extends the Chakra theme to match KeplerLab's color palette.

---

## 20. Middleware (Auth Guard)

`src/middleware.js` runs at the **Next.js Edge Runtime** before any page renders.

```javascript
// Protected: all routes except these
PUBLIC_PREFIXES = ['/auth', '/view', '/api']
STATIC_EXTENSIONS = .ico|.png|.jpg|.css|.js|...

export function middleware(request) {
  // Pass through public routes
  if (isPublic(pathname)) return NextResponse.next();
  
  // Check for refresh_token HttpOnly cookie
  const refreshToken = request.cookies.get('refresh_token');
  if (!refreshToken?.value) {
    // Redirect to /auth with ?redirect= for post-login redirect
    return NextResponse.redirect('/auth?redirect=' + pathname);
  }
  
  return NextResponse.next();
}
```

This means:
- **Server-side**, pages never render for unauthenticated users
- Only the existence of the cookie is checked (not its validity — the client `initAuth` handles that)
- `/view` is public (shareable content)
- `/api` is public (Next.js API routes if any)

---

## 21. Real-time Updates (WebSocket)

### Material Processing Updates

Hook: `useMaterialUpdates.js`

```
Backend (ws_manager) pushes event:
{"type": "material_update", "material_id": "<uuid>", "status": "completed", "chunk_count": 142}

Frontend receives → updates material status in useAppStore:
setMaterials(prev => prev.map(m => m.id === material_id ? {...m, status} : m))

→ SourceItem re-renders with new status badge
```

### Connection Strategy

- Initial connection on notebook load (after `userId` is available)
- **Exponential backoff reconnection**: 1s → 2s → 4s → 8s → ... → 30s max
- **Ping/Pong keepalive**: Server sends `{"type":"ping"}` every 30s
- On page unload: WebSocket closed cleanly

### Auth in WebSocket

The HTTP `Authorization` header cannot be sent on WebSocket upgrade. Instead:
```
ws://localhost:8000/ws/jobs/{user_id}?token=<access_token>
```
The backend validates the JWT from the query parameter and confirms `user_id` matches.

---

## 22. SSE Streaming (Chat)

Chat responses stream from the backend via **Server-Sent Events (SSE)**.

### Client-side Streaming Handler

`readSSEStream(response, onEvent)` in `lib/utils/helpers.js`:

```javascript
// Reads the ReadableStream line by line
// Every "data: {...}" line → parses JSON → calls onEvent(event)

// Event types:
{type: "agent_step", step: {tool, intent, query}}
{type: "token", content: "...next token..."}
{type: "citations", citations: [{...}]}
{type: "agent_meta", ...}
{type: "data_analysis", ...}
{type: "done"}
{type: "error", detail: "..."}
```

### Rendering Strategy

1. On first `token` event: a new assistant message is added to `messages` array
2. Subsequent `token` events: `content` field of the message is appended
3. `sanitizeStreamingMarkdown(partialContent)` is called before each render to handle incomplete markdown syntax (unclosed `**`, `\`\`\`` etc.)
4. React re-renders are batched using `startTransition` to keep UI smooth
5. On `done`: message is finalized, `agent_meta` attached, citations stored

### Cancellation

The `AbortController` signal is passed to `streamChat()`. When user clicks the stop button:
```javascript
abortController.abort()
→ fetch request cancelled
→ streaming stops
→ partial response kept in message
```

---

## 23. Data Flow Diagrams

### Complete Chat Message Flow

```
User types message + selects /web command + clicks send
    │
    ▼
ChatPanel.handleSend()
    ├── Adds user message to useAppStore.messages
    ├── Creates AbortController
    ├── Calls streamChat({message, material_ids, notebook_id, intent_override: "WEB_RESEARCH"})
    │
    ▼
lib/api/chat.js → POST /chat (text/event-stream)
    │
    ▼
FastAPI /chat route
    ├── Validates materials
    ├── Creates/retrieves chat session
    └── Invokes LangGraph agent with intent_override="WEB_RESEARCH"
    │
    │  SSE Stream back to browser:
    │  data: {"type":"agent_step","step":{"tool":"research_tool"}}
    │  data: {"type":"token","content":"## Research Report\n\n"}
    │  data: {"type":"token","content":"Based on 12 sources..."}
    │  data: {"type":"citations","citations":[...]}
    │  data: {"type":"done"}
    │
    ▼
readSSEStream processes each event:
    ├── agent_step → updates AgentThinkingBar + ResearchProgress
    ├── token → appends to streaming message buffer → MarkdownRenderer re-renders
    ├── citations → stored on message object
    └── done → finalizes message, hides thinking indicators
    │
    ▼
Final state in useAppStore.messages:
{
  id: "abc123",
  role: "assistant",
  content: "## Research Report\n\nBased on 12 sources...",
  citations: [{title, url, snippet}],
  slashCommand: {command: "/web", intent: "WEB_RESEARCH"}
}
```

### Material Upload Flow

```
User drops file in UploadDialog
    │
    ▼
UploadDialog.handleFileUpload()
    ├── Client-side size/type check
    ├── POST /upload (multipart, with progress callback)
    │
    ▼
Backend responds immediately:
{"material_id": "uuid", "status": "pending", "job_id": "uuid"}
    │
    ▼
Frontend:
    ├── Adds material to useAppStore.materials (status=pending)
    ├── Closes upload dialog
    │
    ▼
useMaterialUpdates WebSocket listener:
    ├── Receives: {type:"material_update", material_id, status:"processing"}
    │     → updates SourceItem spinner
    ├── Receives: {type:"material_update", material_id, status:"embedding"}
    │     → keeps spinner
    └── Receives: {type:"material_update", material_id, status:"completed", chunk_count:87}
          → updates SourceItem to green checkmark
          → material now selectable for AI context
```

### Flashcard Generation Flow

```
User in StudioPanel → Flashcards tab → clicks "Generate"
    │
    ▼
FlashcardConfigDialog: count=15, language="en"
    │
    ▼
StudioPanel.handleGenerateFlashcards()
    ├── setLoadingState('flashcard', true)
    ├── calls generateFlashcards(notebookId, [...selectedSources], 15, 'en')
    │
    ▼
POST /flashcards/generate → wait (~10-30s) → {cards: [{question, answer}]}
    │
    ▼
saveGeneratedContent(notebookId, 'flashcard', data, materialIds)
    │
    ▼
useAppStore.setFlashcards(data)
InlineFlashcardsView renders cards
    └── User flips cards, marks known/unknown, downloads PDF
```

---

## Summary: Full Feature List

| Feature | Frontend Components | Backend Endpoint |
|---------|-------------------|-----------------|
| Auth | LoginForm, SignupForm, useAuthStore | /auth/* |
| Dashboard | page.jsx (home) | GET /notebooks |
| Notebook CRUD | page.jsx, Header | /notebooks/* |
| File Upload | UploadDialog, SourceItem | POST /upload |
| URL Scrape | UploadDialog (URL tab) | POST /upload/url |
| YouTube | UploadDialog (YouTube tab) | POST /upload/youtube |
| Text Input | UploadDialog (Text tab) | POST /upload/text |
| AI Chat | ChatPanel, ChatMessage | POST /chat (SSE) |
| Chat Sessions | ChatHistoryModal | /chat/sessions/* |
| Agent Steps | AgentActionBlock, AgentThinkingBar | (streamed) |
| Web Research | ResearchProgress | /chat (RESEARCH intent) |
| Code Execution | CodeReviewBlock, ExecutionPanel | (python_tool) |
| Charts | ChartRenderer | (python_tool output) |
| Slash Commands | SlashCommandDropdown, CommandBadge | intent_override |
| Flashcards | InlineFlashcardsView, ConfigDialogs | POST /flashcards/generate |
| Quiz | InlineQuizView | POST /quiz/generate |
| Presentation | PresentationView | POST /presentations/generate |
| Mind Map | MindMapCanvas | POST /mindmap/generate |
| Explainer Video | InlineExplainerView, ExplainerDialog | POST /explainer |
| Live Podcast | PodcastStudio, PodcastConfigDialog | /podcast/* |
| Podcast Q&A | PodcastStudio (interrupt) | POST /podcast/sessions/{id}/doubts |
| Material Status | SourceItem, useMaterialUpdates | WS /ws/jobs/{userId} |
| Content History | ContentHistory | GET /notebooks/{id}/generated |
| Dark Mode | ThemeProvider, useTheme | (client-only) |
