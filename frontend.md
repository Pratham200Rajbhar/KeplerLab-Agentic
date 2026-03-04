# KeplerLab Frontend — Complete Technical Documentation

---

## Table of Contents

1. [Overview](#1-overview)
2. [Technology Stack](#2-technology-stack)
3. [Project Structure](#3-project-structure)
4. [Configuration & Environment](#4-configuration--environment)
5. [Routing (Next.js App Router)](#5-routing-nextjs-app-router)
6. [Middleware & Authentication Guard](#6-middleware--authentication-guard)
7. [Global Providers & Theme](#7-global-providers--theme)
8. [State Management (Zustand)](#8-state-management-zustand)
    - [useAppStore](#useappstore)
    - [useAuthStore](#useauthstore)
    - [useChatStore](#usechatstore)
    - [useMaterialStore](#usematerialstore)
    - [useNotebookStore](#usenotebookstore)
    - [useUIStore](#useuistore)
    - [usePodcastStore](#usepodcaststore)
    - [useToastStore](#usetoaststore)
    - [useConfirmStore](#useconfirmstore)
9. [API Layer](#9-api-layer)
    - [Authentication & Token Management](#authentication--token-management)
    - [API Modules](#api-modules)
10. [Pages](#10-pages)
    - [Home / Dashboard](#home--dashboard)
    - [Auth Page](#auth-page)
    - [Notebook Page](#notebook-page)
    - [View Page](#view-page)
11. [Components](#11-components)
    - [Layout](#layout)
    - [Chat Components](#chat-components)
    - [Studio Components](#studio-components)
    - [Mind Map Components](#mind-map-components)
    - [Podcast Components](#podcast-components)
    - [Presentation Components](#presentation-components)
    - [Notebook Components](#notebook-components)
    - [UI Components](#ui-components)
    - [Viewer Components](#viewer-components)
12. [Custom Hooks](#12-custom-hooks)
13. [Slash Commands System](#13-slash-commands-system)
14. [SSE (Server-Sent Events) Streaming](#14-sse-server-sent-events-streaming)
15. [WebSocket Integration](#15-websocket-integration)
16. [Styling](#16-styling)
17. [Build & Deployment](#17-build--deployment)
18. [End-to-End User Flows](#18-end-to-end-user-flows)

---

## 1. Overview

The KeplerLab frontend is a **Next.js 16 (App Router)** application built with **React 19** and styled with **Tailwind CSS**. It provides:

- A **notebook-centric interface**: users create notebooks, upload source materials, and interact with AI tools
- A **real-time chat interface** with SSE streaming, slash commands for intent routing, and rich response rendering
- A **Studio panel** for generating flashcards, quizzes, presentations, mind maps, explainer videos, and podcasts
- A **Podcast Studio** with audio playback, doubts, bookmarks, annotations, and export
- A **Mind Map Canvas** powered by React Flow (`@xyflow/react`)
- **Code execution REPL** with chart rendering
- **Research mode** with progress tracking and source citations
- Full **dark/light theme** support via `next-themes`

---

## 2. Technology Stack

| Layer | Technology |
|---|---|
| Framework | Next.js 16.1.6 (App Router) |
| React | React 19.2.3 |
| Styling | Tailwind CSS 3.4.17 |
| State Management | Zustand 5.0.11 |
| Charts / Graphs | @xyflow/react 12.10.1 (React Flow), dagre 0.8.5 |
| Markdown | react-markdown 10.1.0 + remark-gfm + remark-math + rehype-katex + rehype-raw |
| Math | KaTeX 0.16.33 |
| Code Highlight | react-syntax-highlighter 16.1.1 |
| PDF Export | jspdf 4.2.0 |
| Image Export | html-to-image 1.11.13 |
| Virtual List | react-window 2.2.7 |
| Icons | lucide-react 0.576.0 |
| Theme | next-themes 0.4.6 |
| Linting | ESLint 9 + eslint-config-next |
| Build | PostCSS, Autoprefixer |

---

## 3. Project Structure

```
frontend/
├── Dockerfile
├── eslint.config.mjs
├── jsconfig.json               # Path aliases: @/ → src/
├── next.config.mjs             # API proxy rewrites, standalone output
├── package.json
├── postcss.config.mjs
├── tailwind.config.js
├── public/                     # Static assets
└── src/
    ├── middleware.js            # Edge middleware — auth cookie guard
    ├── app/
    │   ├── layout.jsx           # Root layout (fonts, providers, theme)
    │   ├── page.jsx             # Home / Dashboard
    │   ├── loading.jsx          # Global suspense loading UI
    │   ├── error.jsx            # Global error boundary
    │   ├── global-error.jsx     # Root-level error (replaces layout)
    │   ├── not-found.jsx        # 404 page
    │   ├── providers.jsx        # React context providers wrapper
    │   ├── auth/
    │   │   ├── layout.jsx       # Auth layout (centered card)
    │   │   └── page.jsx         # Login / Signup page
    │   ├── notebook/
    │   │   └── [id]/
    │   │       ├── layout.jsx   # Notebook layout
    │   │       └── page.jsx     # Main notebook workspace
    │   └── view/
    │       └── page.jsx         # Public file viewer
    ├── components/
    │   ├── chat/                # All chat-related components
    │   ├── layout/              # Header, Sidebar
    │   ├── mindmap/             # Mind map canvas + nodes
    │   ├── notebook/            # Source item, upload dialog, web search
    │   ├── podcast/             # Full podcast studio UI
    │   ├── presentation/        # Presentation viewer
    │   ├── studio/              # Content generation panel
    │   ├── ui/                  # Generic UI (Modal, Toast, Confirm, ErrorBoundary)
    │   └── viewer/              # File viewer content
    ├── hooks/
    │   ├── useChatStream.js     # SSE stream handler
    │   ├── useMaterialUpdates.js # WebSocket material status updates
    │   ├── useMicInput.js       # Microphone input for voice
    │   ├── useMindMap.js        # Mind map state + actions
    │   ├── usePodcast.js        # Podcast lifecycle
    │   ├── usePodcastPlayer.js  # Audio playback state machine
    │   ├── usePodcastWebSocket.js # Podcast WS events
    │   └── useResizablePanel.js # Panel resize handle
    ├── lib/
    │   ├── api/
    │   │   ├── config.js        # apiFetch, apiJson, token management
    │   │   ├── auth.js          # Auth API calls
    │   │   ├── agent.js         # Agent/code execution API
    │   │   ├── chat.js          # Chat + session API
    │   │   ├── explainer.js     # Explainer video API
    │   │   ├── generation.js    # Flashcards, quiz, presentation
    │   │   ├── jobs.js          # Background jobs API
    │   │   ├── materials.js     # Materials CRUD API
    │   │   ├── mindmap.js       # Mind map API
    │   │   ├── notebooks.js     # Notebooks CRUD API
    │   │   └── podcast.js       # Podcast sessions API
    │   └── utils/
    │       ├── constants.js     # App-wide constants
    │       └── helpers.js       # Utility functions (SSE reader, formatters, etc.)
    ├── stores/
    │   ├── useAppStore.js       # Global app state (re-exports focused stores)
    │   ├── useAuthStore.js      # Auth state + token lifecycle
    │   ├── useChatStore.js      # Chat messages + response state
    │   ├── useConfirmStore.js   # Confirmation dialog state
    │   ├── useMaterialStore.js  # Material list + selection state
    │   ├── useNotebookStore.js  # Notebook list state
    │   ├── usePodcastStore.js   # Podcast session state
    │   ├── useToastStore.js     # Toast notification queue
    │   └── useUIStore.js        # UI panel visibility state
    └── styles/
        └── globals.css          # Tailwind base + custom CSS variables
```

---

## 4. Configuration & Environment

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | Backend API URL |
| `NEXT_PUBLIC_API_PROTOCOL` | `http` | Backend protocol (for Next.js Image) |
| `NEXT_PUBLIC_API_HOST` | `localhost` | Backend hostname |
| `NEXT_PUBLIC_API_PORT` | `8000` | Backend port |

### Path Aliases (`jsconfig.json`)

```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

All imports inside `src/` use `@/` prefix to reference from `src/`.

### Next.js Config (`next.config.mjs`)

- **API Proxy**: `/api/:path*` → `http://localhost:8000/:path*` (development only);
  `/api/presentation/slides/:path*` also proxied
- **Output**: `standalone` (optimized for Docker deployment)
- **React Strict Mode**: enabled
- **Remote Images**: configured for backend image serving

---

## 5. Routing (Next.js App Router)

Next.js 16 App Router with file-system-based routing:

| Route | Page | Description |
|---|---|---|
| `/` | `app/page.jsx` | Home / Dashboard — lists all notebooks |
| `/auth` | `app/auth/page.jsx` | Login and Signup |
| `/notebook/[id]` | `app/notebook/[id]/page.jsx` | Notebook workspace |
| `/notebook/draft` | Same page, special case | New unsaved notebook |
| `/view` | `app/view/page.jsx` | Public file viewer (no auth required) |

### Not Found & Error Pages

- `app/not-found.jsx` — Custom 404 UI
- `app/error.jsx` — Page-level error boundary with retry button
- `app/global-error.jsx` — Root layout error (replaces shell entirely)
- `app/loading.jsx` — Global suspense skeleton

---

## 6. Middleware & Authentication Guard

**File**: `src/middleware.js` (Next.js Edge Middleware)

Runs at the edge on every request before page rendering.

**Logic**:
1. Allow public paths without auth: `/auth`, `/view`, `/api`
2. Allow Next.js internals: `/_next`, `/favicon`, static file extensions
3. Check for `refresh_token` cookie (HttpOnly, set by backend)
4. If cookie missing → redirect to `/auth?redirect=<original_path>`

```javascript
const PUBLIC_PREFIXES = ['/auth', '/view', '/api'];
// Cookie name: 'refresh_token' (HttpOnly, matches backend setting)
```

> The middleware only checks for the **cookie's presence**, not validity. Actual token validation happens on the first API call (`initAuth`).

**Matcher**: All routes except `_next/static`, `_next/image`, `favicon.ico`.

---

## 7. Global Providers & Theme

**File**: `src/app/providers.jsx`

Wraps the app with:
- `ThemeProvider` (next-themes, `defaultTheme: "dark"`, attribute: `"class"`)
- Toast container
- Confirm dialog
- Auth initialization effect

**Root Layout** (`src/app/layout.jsx`):
- Sets HTML font families
- Applies Tailwind base styles
- Wraps children in `<Providers>`

### Theme

- Dark and light themes available
- CSS class toggling on `<html>` root
- Toggle available on Home dashboard and notebook header
- Uses `useTheme()` hook from `next-themes`

---

## 8. State Management (Zustand)

All application state is managed with **Zustand** stores (no Redux, no Context for most state).

### useAppStore

**File**: `src/stores/useAppStore.js`

Main aggregator store. Also re-exports `useChatStore`, `useMaterialStore`, `useNotebookStore`, `useUIStore` for gradual migration.

**State**:

| Key | Type | Description |
|---|---|---|
| `currentNotebook` | Object? | Currently active notebook |
| `draftMode` | Boolean | Whether the notebook is unsaved draft |
| `currentMaterial` | Object? | Currently selected material |
| `materials` | Array | All materials for current notebook |
| `selectedSources` | Array\<ID\> | IDs of checked source materials |
| `sessionId` | String? | Current chat session ID |
| `messages` | Array | Chat messages for current session |
| `flashcards` | Object? | Last generated flashcards |
| `quiz` | Object? | Last generated quiz |
| `notes` | Array | Notebook notes |
| `pendingChatMessage` | String? | Bridge: mind map → chat |
| `loading` | Object | Per-feature loading flags |
| `error` | String? | Global error |
| `activePanel` | String | `'chat'` or `'studio'` |
| `podcastWsHandlerRef` | Ref | WebSocket handler reference |

**Key actions**:
- `setCurrentNotebook(notebook)` — switches active notebook
- `setMaterials(materials)` — replaces full material list
- `addMaterial(material)` — appends material, sets as current
- `setSelectedSources(ids)` — set selected source IDs
- `toggleSourceSelection(id)` — toggle one source in/out
- `selectAllSources()` / `deselectAllSources()`
- `setLoadingState(key, bool)` — per-feature loading flag
- `resetForNotebookSwitch()` — clear all transient state

---

### useAuthStore

**File**: `src/stores/useAuthStore.js`

Handles JWT lifecycle: init, login, refresh, logout.

**State**:

| Key | Description |
|---|---|
| `user` | Current user object (id, email, username, role) |
| `isLoading` | True during initial auth check |
| `isAuthenticated` | Boolean |
| `error` | Auth error message |

**Key actions**:

| Action | Description |
|---|---|
| `initAuth()` | Called once on app mount — calls `POST /auth/refresh`, then `GET /auth/me` |
| `login(email, password)` | Calls API, syncs access token, schedules refresh |
| `signup(email, username, password)` | Register + auto-login |
| `logout()` | Calls `POST /auth/logout`, clears token + user |
| `scheduleRefresh()` | Sets timer to refresh access token before expiry |

**Token refresh strategy**:
- Access token refreshed with `setTimeout` before its 15-min expiry
- On failure: 3 retries with exponential backoff (2s, 4s, 8s)
- If all retries fail → redirect to `/auth?reason=expired`
- Token stored in **module-level ref** (not in Zustand state) to avoid serialization issues
- `setAccessToken()` syncs token to the `lib/api/config.js` module

---

### useChatStore

**File**: `src/stores/useChatStore.js`

Chat-specific state for the active session.

**State**:
- `messages` — array of chat message objects
- `isStreaming` / `streamingContent` — current streaming response
- `sessionId` — active session ID
- `sessions` — list of all sessions for current notebook

---

### useMaterialStore

**File**: `src/stores/useMaterialStore.js`

Material list + WebSocket-driven status updates.

**State**:
- `materials` — array of material objects
- Status updates merged in real-time via WebSocket

---

### useNotebookStore

**File**: `src/stores/useNotebookStore.js`

Notebook list management for the dashboard.

---

### useUIStore

**File**: `src/stores/useUIStore.js`

Panel visibility and UI flags.

---

### usePodcastStore

**File**: `src/stores/usePodcastStore.js`

Podcast session state: current session, segments, playback position, doubts, bookmarks.

---

### useToastStore

**File**: `src/stores/useToastStore.js`

Toast notification queue (success, error, warning, info).

Usage:
```javascript
const toast = useToast();
toast.success('Action completed!');
toast.error('Something went wrong');
```

---

### useConfirmStore

**File**: `src/stores/useConfirmStore.js`

Global confirmation dialog state.

Usage:
```javascript
const { confirm } = useConfirm();
const yes = await confirm({ title: 'Delete?', message: 'Are you sure?', confirmText: 'Delete', danger: true });
```

---

## 9. API Layer

### Authentication & Token Management

**File**: `src/lib/api/config.js`

Central fetch utilities with:
- **In-memory access token** (`_accessToken`) — never stored in localStorage
- **Auto-refresh on 401** — deduplicates concurrent refresh calls
- **Session expiry callback** — soft redirect to `/auth`

**Core functions**:

| Function | Description |
|---|---|
| `setAccessToken(token)` | Store access token in memory |
| `getAccessToken()` | Read current access token |
| `onSessionExpired(callback)` | Register session expiry handler |
| `apiFetch(path, options)` | Authenticated fetch with auto-retry on 401 |
| `apiJson(path, options)` | apiFetch + JSON parse |
| `apiStream(path, options)` | Returns raw Response for SSE streaming |

**Retry logic**:
1. Add `Authorization: Bearer <token>` header
2. If response is `401` → call `_refreshTokenOnce()` (deduplicated)
3. If refresh succeeds → retry original request once
4. If refresh fails → call `_handleSessionExpiry()` → redirect to `/auth`

---

### API Modules

#### `lib/api/auth.js`

| Function | Method | Endpoint |
|---|---|---|
| `login(email, password)` | POST | `/auth/login` |
| `signup(email, username, password)` | POST | `/auth/signup` |
| `logout()` | POST | `/auth/logout` |
| `getCurrentUser()` | GET | `/auth/me` |
| `refreshToken()` | POST | `/auth/refresh` (raw fetch, bypasses apiFetch) |

---

#### `lib/api/notebooks.js`

| Function | Method | Endpoint |
|---|---|---|
| `getNotebooks()` | GET | `/notebooks` |
| `getNotebook(id)` | GET | `/notebooks/{id}` |
| `createNotebook(name, description)` | POST | `/notebooks` |
| `updateNotebook(id, data)` | PATCH | `/notebooks/{id}` |
| `deleteNotebook(id)` | DELETE | `/notebooks/{id}` |
| `saveGeneratedContent(notebookId, data)` | POST | `/notebooks/{id}/content` |
| `getGeneratedContent(notebookId, type?)` | GET | `/notebooks/{id}/content` |
| `deleteGeneratedContent(notebookId, contentId)` | DELETE | `/notebooks/{id}/content/{contentId}` |
| `updateGeneratedContent(notebookId, contentId, data)` | PATCH | `/notebooks/{id}/content/{contentId}` |
| `updateGeneratedContentTitle(notebookId, contentId, title)` | PATCH | `/notebooks/{id}/content/{contentId}/title` |

---

#### `lib/api/materials.js`

| Function | Endpoint |
|---|---|
| `getMaterials(notebookId?)` | GET `/materials` |
| `uploadFile(file, notebookId)` | POST `/upload/file` (FormData) |
| `uploadUrl(url, notebookId)` | POST `/upload/url` |
| `uploadYouTube(url, notebookId)` | POST `/upload/youtube` |
| `uploadText(text, title, notebookId)` | POST `/upload/text` |
| `deleteMaterial(id)` | DELETE `/materials/{id}` |
| `updateMaterial(id, data)` | PATCH `/materials/{id}` |
| `getMaterialText(id)` | GET `/materials/{id}/text` |

---

#### `lib/api/chat.js`

| Function | Description |
|---|---|
| `streamChat(materialId, message, notebookId, materialIds, sessionId, signal, intentOverride)` | POST `/chat` — returns raw Response for SSE |
| `getChatHistory(notebookId, sessionId?)` | GET `/chat/history` |
| `createChatSession(notebookId, title)` | POST `/chat/sessions` |
| `getChatSessions(notebookId)` | GET `/chat/sessions` |
| `deleteChatSession(sessionId)` | DELETE `/chat/sessions/{id}` |

---

#### `lib/api/generation.js`

| Function | Endpoint |
|---|---|
| `generateFlashcards(materialId, options)` | POST `/flashcard` |
| `generateQuiz(materialId, options)` | POST `/quiz` |
| `generatePresentation(materialId, options)` | POST `/presentation/async` (polls for completion) |
| `downloadBlob(blob, filename)` | Local utility (creates download link) |

**Presentation polling**: polls `GET /jobs/{jobId}` every 3 seconds, max 10 minutes.

---

#### `lib/api/mindmap.js`

| Function | Endpoint |
|---|---|
| `generateMindMap(materialIds, notebookId)` | POST `/mindmap` |
| `getMindMap(notebookId)` | GET `/mindmap/{notebookId}` |
| `deleteMindMap(id)` | DELETE `/mindmap/{id}` |

---

#### `lib/api/agent.js`

| Function | Endpoint |
|---|---|
| `executeCode(code, notebookId, timeout, signal)` | POST `/agent/execute` (SSE stream) |
| `analyzeData(query, notebookId, materialIds, signal)` | POST `/agent/analyze` (SSE stream) |
| `runResearch(query, notebookId, materialIds, signal)` | POST `/agent/research` (SSE stream) |
| `runGeneratedCode(code, language, notebookId, sessionId, timeout)` | POST `/agent/run-generated` |
| `getAgentStatus(jobId)` | GET `/agent/status/{jobId}` |
| `getGeneratedFileUrl(filename, token)` | GET `/agent/file/{filename}?token=` |

---

#### `lib/api/explainer.js`

| Function | Endpoint |
|---|---|
| `checkExistingPresentations(materialIds, notebookId)` | POST `/explainer/check-presentations` |
| `generateExplainerVideo(data)` | POST `/explainer/generate` |
| `getExplainerStatus(id)` | GET `/explainer/{id}/status` |
| `getExplainerVideoUrl(id)` | GET `/explainer/{id}/video` |

---

#### `lib/api/podcast.js`

| Function | Endpoint |
|---|---|
| `createPodcastSession(data)` | POST `/podcast/session` |
| `getPodcastSessions()` | GET `/podcast/sessions` |
| `getPodcastSession(id)` | GET `/podcast/session/{id}` |
| `updatePodcastSession(id, data)` | PATCH `/podcast/session/{id}` |
| `deletePodcastSession(id)` | DELETE `/podcast/session/{id}` |
| `startPodcastGeneration(id)` | POST `/podcast/session/{id}/generate` |
| `getSegmentAudioUrl(sessionId, index)` | GET `/podcast/session/{id}/audio/{index}` |
| `askPodcastDoubt(sessionId, data)` | POST `/podcast/session/{id}/question` |
| `getPodcastDoubts(sessionId)` | GET `/podcast/session/{id}/doubts` |
| `addBookmark(sessionId, data)` | POST `/podcast/session/{id}/bookmark` |
| `getBookmarks(sessionId)` | GET `/podcast/session/{id}/bookmarks` |
| `addAnnotation(sessionId, data)` | POST `/podcast/session/{id}/annotation` |
| `exportPodcast(sessionId, format)` | POST `/podcast/session/{id}/export` |
| `getVoices(language?)` | GET `/podcast/voices` |
| `getVoicePreview(voice, text)` | GET `/podcast/voice-preview` |

---

#### `lib/api/jobs.js`

| Function | Endpoint |
|---|---|
| `getJobs()` | GET `/jobs` |
| `getJob(jobId)` | GET `/jobs/{jobId}` |

---

## 10. Pages

### Home / Dashboard

**File**: `src/app/page.jsx`

The main landing page for authenticated users.

**Features**:
- List all notebooks (loaded via `GET /notebooks`)
- Create new notebook (opens inline form or navigates to `/notebook/draft`)
- Rename notebook (inline edit)
- Delete notebook (confirmation dialog)
- Dark/light theme toggle
- User menu (logout)
- Navigate to notebook workspace

**State**: Local React state (no Zustand needed — single-page data).

---

### Auth Page

**File**: `src/app/auth/page.jsx`

Tabbed login / signup form.

**Features**:
- Login tab: email + password
- Signup tab: email + username + password
- Client-side validation mirroring backend rules
- Post-auth redirect: reads `?redirect=` param, navigates to original destination
- Shows errors inline

---

### Notebook Page

**File**: `src/app/notebook/[id]/page.jsx`

The core workspace. Layout: `Header` + `Sidebar` + `ChatPanel` + `StudioPanel`.

**Behaviour**:
- `id === 'draft'` → sets draftMode, notebook is created on first material upload
- Loads notebook from `GET /notebooks/{id}` on first visit
- Lazy-loads `Sidebar`, `ChatPanel`, `StudioPanel` with `dynamic()` (no SSR)
- Mobile: slide-in sidebar via hamburger menu

---

### View Page

**File**: `src/app/view/page.jsx`

Public file viewer (no auth required).
- Reads `?url=` query param
- Renders file content using `FileViewerContent` component

---

## 11. Components

### Layout

#### `components/layout/Header.jsx`
- Navigation bar for notebook workspace
- Shows notebook name (editable inline)
- Panel toggle buttons (Chat / Studio)
- Theme toggle
- Back to dashboard button

#### `components/layout/Sidebar.jsx`
- Left sidebar in the notebook workspace
- Lists all materials (source documents)
- Upload dialog trigger
- Web search dialog trigger
- Material status indicators (processing, completed, failed)
- Checkbox-based multi-source selection for RAG

---

### Chat Components

#### `ChatPanel.jsx`
Main chat UI container. Orchestrates:
- `ChatMessageList` (scrollable message history)
- `ChatInputArea` (text input + slash commands)
- `SlashCommandDropdown` (command picker overlay)
- Agent step panel, artifact panel, execution panel

#### `ChatMessage.jsx`
Renders a single message (user or assistant):
- `MarkdownRenderer` for rich text
- Code blocks with syntax highlighting
- Agent metadata display (intent, tools, steps)
- Source citations

#### `ChatMessageList.jsx`
Virtualized or standard list of `ChatMessage` components with auto-scroll.

#### `ChatInputArea.jsx`
Multi-line textarea with:
- Slash command activation (`/agent`, `/research`, `/code`, `/web`)
- Active command pill display
- Source selection indicator
- Submit / stop streaming buttons
- Microphone input button

#### `SlashCommandDropdown.jsx`
Overlay showing available slash commands filtered by typed prefix.

#### `SlashCommandPills.jsx`
Horizontal pills displaying active slash command context.

#### `MarkdownRenderer.jsx`
Full-featured Markdown renderer:
- `react-markdown` + `remark-gfm` + `remark-math` + `rehype-katex` + `rehype-raw`
- Syntax highlighting via `react-syntax-highlighter`
- Table rendering with GFM
- Math equations (KaTeX)
- Raw HTML support

#### `ChartRenderer.jsx`
Renders matplotlib-generated charts (base64 PNG data URIs) returned by the Python sandbox.

#### `CodeReviewBlock.jsx`
Displays LLM-generated code before user executes it:
- Shows code with syntax highlighting
- "Run" button triggers `POST /agent/run-generated`
- Shows output (stdout / chart) after execution

#### `AgentStepsPanel.jsx`
Collapsible panel showing agent step-by-step execution log.

#### `AgentActionBlock.jsx`
Individual agent action display: tool name, input, output.

#### `AgentThinkingBar.jsx`
Animated thinking indicator while agent is processing.

#### `AgentReflectionChip.jsx`
Shows agent's self-reflection reasoning.

#### `ArtifactPanel.jsx`
Side panel that shows generated artifacts (files, charts).

#### `ExecutionPanel.jsx`
Code execution output panel (stdout, stderr, exit code, chart).

#### `ResearchProgress.jsx`
Live progress tracker for web research:
- Phase indicators (search → scrape → synthesize)
- Source URLs loading in real-time

#### `ResearchReport.jsx`
Final rendered research report with inline citations.

#### `GeneratedFileCard.jsx`
Card showing a downloadable file generated by the agent.

#### `DocumentPreview.jsx`
Inline preview of uploaded document content.

#### `BlockHoverMenu.jsx`
Context menu on chat response blocks: simplify, translate, explain, copy.

#### `MiniBlockChat.jsx`
Inline follow-up chat within a response block.

#### `ChatHistoryModal.jsx`
Modal showing all chat sessions for the current notebook.

#### `ChatEmptyState.jsx`
Empty state when no messages exist yet.

#### `CopyButton.jsx`
One-click copy button for code blocks and text.

#### `CommandBadge.jsx`
Small badge showing which slash command was used for a message.

#### `SuggestionDropdown.jsx`
Autocomplete suggestions fetched from `POST /chat/suggest`.

---

### Studio Components

#### `StudioPanel.jsx`
The right-side content generation panel. Tabs / feature cards:

| Feature | Icon | Action |
|---|---|---|
| Flashcards | ClipboardCheck | Generate + view inline |
| Quiz | FlaskConical | Generate + take quiz inline |
| Presentation | Monitor | Generate PPT, view, download |
| Explainer Video | Video | Generate video, watch |
| Podcast | Mic | Open Podcast Studio |
| Mind Map | Network | Generate + view interactive map |

Also manages:
- **Content history**: saved flashcards, quizzes, presentations, mind maps per notebook
- **Config dialogs**: per-feature configuration (card count, difficulty, theme, etc.)
- Lazy-loaded heavy components

#### `FeatureCard.jsx`
Individual feature card with icon, title, description, and generate button.

#### `InlineFlashcardsView.jsx`
Interactive flashcard deck within the studio panel:
- Card flip animation
- Navigation (prev/next)
- Progress indicator
- Keyboard shortcuts

#### `InlineQuizView.jsx`
MCQ quiz interface:
- Question display
- Option selection
- Submit + show correct answer
- Score summary

#### `InlineExplainerView.jsx`
Video player for explainer videos:
- Play/pause, seek
- Chapter navigation

#### `ConfigDialogs.jsx`
Modal dialogs for each feature's generation settings:
- `FlashcardConfigDialog`: card count, difficulty, topic, additional instructions
- `QuizConfigDialog`: question count, difficulty, topic, additional instructions

#### `ExplainerDialog.jsx`
Configuration for explainer video generation:
- PPT selection (reuse existing or generate new)
- Language selection (PPT content + narration)
- Voice gender selection

#### `ContentHistory.jsx`
Scrollable history of all previously generated content for the notebook.

#### `HistoryRenameModal.jsx`
Rename modal for saved content entries.

---

### Mind Map Components

#### `MindMapCanvas.jsx`
Interactive mind map using `@xyflow/react` (React Flow):
- Hierarchical node layout via `dagre` graph algorithm
- Pan + zoom
- Node click → opens chat with the node topic
- Export as PNG (html-to-image)
- Export as PDF (jspdf)
- Node expand on click (loads sub-topics)

#### `MindMapNode.jsx`
Custom React Flow node component:
- Styled card with topic text
- Color-coded by depth level
- Click handler for chat bridge

#### `MindMapView.jsx`
Wrapper that manages mind map data loading, generation trigger, and rendering.

---

### Podcast Components

#### `PodcastStudio.jsx`
Top-level podcast UI container:
- Shows session library or active session player
- Manages mode selection, generation, playback

#### `PodcastConfigDialog.jsx`
Session setup wizard:
- Mode selection (overview, deep-dive, debate, q-and-a, topic)
- Topic input (for topic/deep-dive modes)
- Language selection
- Voice selection (host + guest)
- Material selection

#### `PodcastPlayer.jsx`
Full podcast player:
- Segment-by-segment audio playback
- Play/pause/seek controls
- Current segment text display
- Chapter navigation
- Doubt (question) interruption button

#### `PodcastMiniPlayer.jsx`
Sticky mini player bar shown when podcast is playing.

#### `PodcastTranscript.jsx`
Full transcript view with highlighted current segment.

#### `PodcastChapterBar.jsx`
Chapter timeline navigation.

#### `PodcastModeSelector.jsx`
Mode selection cards (overview, deep-dive, etc.).

#### `PodcastGenerating.jsx`
Loading screen during script + audio generation with progress.

#### `PodcastInterruptDrawer.jsx`
Drawer for asking doubts during playback.

#### `PodcastDoubtHistory.jsx`
List of all Q&A doubts and answers for the session.

#### `PodcastExportBar.jsx`
Export controls (PDF transcript / JSON).

#### `PodcastSessionLibrary.jsx`
Grid of all saved podcast sessions with resume/delete actions.

#### `VoicePicker.jsx`
Voice selection component with preview audio playback.

---

### Presentation Components

#### `PresentationView.jsx`
Full HTML presentation renderer:
- Renders LLM-generated HTML slides
- Slide navigation (prev/next, keyboard arrows)
- Fullscreen mode
- Export as HTML file
- `PresentationConfigDialog` embedded here

---

### Notebook Components

#### `UploadDialog.jsx`
Material upload modal:
- File upload (drag & drop + file picker)
- URL ingestion input
- YouTube URL input
- Plain text input
- Progress indication during upload

#### `SourceItem.jsx`
Individual material row in the sidebar:
- Status icon (pending → processing → completed/failed)
- Filename / title display
- Checkbox for source selection
- Context menu: rename, delete, view

#### `WebSearchDialog.jsx`
Quick web search UI:
- Query input
- Results list
- Option to add result URL as a material

---

### UI Components

#### `Modal.jsx`
Generic accessible modal with backdrop and close button.

#### `ToastContainer.jsx`
Fixed-position toast notification stack (success, error, warning, info) with auto-dismiss.

#### `ConfirmDialog.jsx`
Accessible confirmation modal with "confirm" + "cancel" buttons.
Can be configured as destructive (red confirm button).

#### `ErrorBoundary.jsx`
React error boundary for panels:
```jsx
<PanelErrorBoundary fallback="Panel failed to load">
  <ChatPanel />
</PanelErrorBoundary>
```

---

### Viewer Components

#### `FileViewerContent.jsx`
Content area for the `/view` page.
Renders documents from a URL (PDF iframe, text, etc.).

---

## 12. Custom Hooks

### `useChatStream`

**File**: `src/hooks/useChatStream.js`

Owns all SSE event processing. Called by `ChatPanel`.

**Input callbacks** (called per SSE event type):

| Callback | SSE Event | Description |
|---|---|---|
| `onToken` | `token` | Streaming text chunk |
| `onStep` | `step` | Agent step started |
| `onStepDone` | `step_done` | Agent step completed |
| `onCodeWritten` | `code_written` | LLM produced code |
| `onCodeGenerating` | `code_generating` | Code generation in progress |
| `onCodeStdout` | `code_stdout` | Sandbox stdout chunk |
| `onStdout` | `stdout` | General stdout |
| `onAgentStep` | `agent_step` | Agent framework step |
| `onAgentStart` | `agent_start` | Agent loop started |
| `onAgentReflection` | `agent_reflection` | Agent self-reflection |
| `onWebResearchPhase` | `web_research_phase` | Research phase update |
| `onCodeForReview` | `code_for_review` | Generated code ready for user approval |
| `onRepairAttempt` | `repair_attempt` | Code repair attempt N |
| `onRepairSuccess` | `repair_success` | Code repair succeeded |
| `onFileReady` | `file_ready` | Downloadable file ready |
| `onMeta` | `meta` | Message metadata (token count, latency) |
| `onBlocks` | `blocks` | Paragraph response blocks |
| `onArtifact` | `artifact` | Artifact (chart, file) ready |
| `onResearchPhase` | `research_phase` | Deep research phase |
| `onResearchSource` | `research_source` | New source discovered |
| `onCitations` | `citations` | Source citation map |
| `onDone` | `done` | Stream complete |
| `onError` | `error` | Server error |

**Returns**: `{ startStream, stopStream, isStreaming }`

---

### `useMaterialUpdates`

**File**: `src/hooks/useMaterialUpdates.js`

Establishes WebSocket connection to `/ws/jobs/{userId}?token=<jwt>`.

- Receives `material_update` events → updates material status in store
- Receives `podcast_event` → routes to podcast WS handler
- Auto-reconnect on disconnect
- Sends periodic pings

---

### `useMicInput`

**File**: `src/hooks/useMicInput.js`

Microphone input for voice-to-text:
- Uses `MediaRecorder` API
- Sends audio to backend for Whisper transcription (or uses browser speech if available)

---

### `useMindMap`

**File**: `src/hooks/useMindMap.js`

Mind map state + actions:
- Generates mind map via `POST /mindmap`
- Loads saved mind map via `GET /mindmap/{notebookId}`
- Node expansion
- Export (PNG, PDF)
- Chat bridge: sets `pendingChatMessage` on node click

---

### `usePodcast`

**File**: `src/hooks/usePodcast.js`

High-level podcast lifecycle:
- Create / load sessions
- Start generation
- Session CRUD

---

### `usePodcastPlayer`

**File**: `src/hooks/usePodcastPlayer.js`

Audio playback state machine:
- Loads segment audio URLs
- Play/pause/seek
- Auto-advance to next segment
- Tracks current segment index
- Communicates with `PodcastPlayer` component

---

### `usePodcastWebSocket`

**File**: `src/hooks/usePodcastWebSocket.js`

Listens for `podcast_event` WebSocket messages:
- Generation progress updates
- Segment-ready notifications

---

### `useResizablePanel`

**File**: `src/hooks/useResizablePanel.js`

Drag-to-resize panel handle between `ChatPanel` and `StudioPanel`.

---

## 13. Slash Commands System

**File**: `src/components/chat/slashCommands.js`

The slash command system is the **only** way intent is communicated to the backend. The frontend never guesses intent.

### Available Commands

| Command | Intent | Backend behavior |
|---|---|---|
| `/agent` | `AGENT` | Full LangGraph agentic loop |
| `/research` | `WEB_RESEARCH` | Deep multi-iteration web research |
| `/code` | `CODE_EXECUTION` | NL → Python code → sandbox execute |
| `/web` | `WEB_SEARCH` | Quick DuckDuckGo + LLM summarize |
| _(none)_ | _(omitted)_ | RAG pipeline (default) |

### How Commands Work

1. User types `/agent analyze this data` in the chat input
2. `parseSlashCommand(message)` detects the command
3. Input area shows active command pill (colored badge)
4. Remaining message text (`"analyze this data"`) is sent as the actual message
5. `intent_override: "AGENT"` is included in the `POST /chat` request body

### Helper Functions

```javascript
getSlashCommand(command)        // Look up by "/agent" string
getSlashCommandByIntent(intent) // Look up by "AGENT" string
parseSlashCommand(message)      // Parse input, extract command + rest
```

---

## 14. SSE (Server-Sent Events) Streaming

Chat responses are streamed via **Server-Sent Events (SSE)**.

**Utility**: `src/lib/utils/helpers.js` → `readSSEStream(response, callbacks)`

### Stream Event Format

Each event from the backend is:
```
data: {"type": "token", "content": "Hello"}
data: {"type": "done", "session_id": "..."}
```

### Event Types Handled

| Type | Data | Frontend Action |
|---|---|---|
| `token` | `{content: "..."}` | Append to streaming text |
| `step` | `{step: N, tool: "..."}` | Show agent step indicator |
| `step_done` | `{step: N, result: "..."}` | Complete step column |
| `code_written` | `{code: "..."}` | Show code block |
| `code_generating` | — | Show "generating code..." indicator |
| `code_stdout` | `{content: "..."}` | Append to stdout panel |
| `agent_start` | `{plan: [...]}` | Show plan preview |
| `agent_step` | `{step, tool, input}` | Append to steps panel |
| `agent_reflection` | `{reasoning: "..."}` | Show reflection chip |
| `web_research_phase` | `{phase: "..."}` | Update research progress |
| `code_for_review` | `{code, language}` | Show `CodeReviewBlock` |
| `repair_attempt` | `{attempt: N, error: "..."}` | Show repair status |
| `repair_success` | `{code: "..."}` | Show repaired code |
| `file_ready` | `{filename, url, token}` | Show download card |
| `artifact` | `{type, data}` | Render chart or artifact |
| `blocks` | `{blocks: [...]}` | Replace streaming text with blocks |
| `citations` | `{map: {...}}` | Link source citations |
| `research_source` | `{url, title}` | Add to research source list |
| `meta` | `{tokens, latency, model}` | Show message metadata footer |
| `done` | `{session_id, ...}` | Finalize message, save session |
| `error` | `{message: "..."}` | Show error in chat |

---

## 15. WebSocket Integration

**Hook**: `src/hooks/useMaterialUpdates.js`

**Connection**: `ws://{apiHost}/ws/jobs/{userId}?token={accessToken}`

### Message Types Received

| Type | Action |
|---|---|
| `material_update` | Update material status in store (`pending` → `processing` → `completed`/`failed`) |
| `ping` | Keepalive (no-op on client) |
| `podcast_event` | Route to podcast WS handler (`usePodcastWebSocket`) |

### Reconnect Behavior

- Auto-reconnect with delay on unexpected disconnect
- Re-authenticates with fresh access token on reconnect

---

## 16. Styling

### Tailwind CSS

**Config**: `tailwind.config.js`

Custom CSS variables defined in `src/styles/globals.css`:
- `--color-surface` — main background
- `--color-card` — card background
- `--color-border` — border colors
- `--color-text-primary` / `--color-text-secondary`
- `--color-accent` — brand accent color
- Loading spinner animation

### Dark / Light Theme

- Managed by `next-themes` with class strategy
- `dark:` Tailwind variants throughout components
- CSS variables toggle between dark/light values

### Typography

- `react-markdown` + KaTeX for rich text and math equations
- Code blocks: `react-syntax-highlighter` (GitHub Dark theme)
- Monospace font for code, sans-serif for UI

---

## 17. Build & Deployment

### Development

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
```

### Production Build

```bash
npm run build      # Outputs to .next/
npm run start      # Serve production build
```

### Docker

```dockerfile
# Dockerfile included
# Uses standalone output mode
# Copies .next/standalone + .next/static + public/
```

### Environment

Set `NEXT_PUBLIC_API_BASE_URL` to the backend URL:
```bash
NEXT_PUBLIC_API_BASE_URL=https://api.keplerlab.example.com npm run build
```

---

## 18. End-to-End User Flows

### Flow 1: First Use — Signup & Create Notebook

```
User visits /
Middleware checks refresh_token cookie → missing → redirect to /auth
/auth page: user fills signup form
POST /auth/signup → returns user object
POST /auth/login → sets refresh cookie + returns access token
initAuth() runs → access token stored in memory
scheduleRefresh() sets timer
User lands on / (dashboard)
  ↓
User clicks "New Notebook"
POST /notebooks → notebook created
Navigate to /notebook/{id}
```

---

### Flow 2: Upload Material & Chat

```
/notebook/{id} loads
Sidebar shows empty state
User clicks "Upload" → UploadDialog opens
User selects PDF file
POST /upload/file → Material record created (status: pending)
WebSocket receives: {type: "material_update", status: "processing"}
  UI: source item shows spinner
WebSocket receives: {type: "material_update", status: "completed"}
  UI: green checkmark, chunk_count shown

User selects source (checkbox in sidebar)
User types question in chat input
"No slash command" → intent omitted in request
POST /chat {message, material_ids, notebook_id}
  ↓
Backend: RAG retrieval → LLM → SSE stream
Frontend: useChatStream handles events
  token events → text appears token by token
  done event → message finalized, session_id set
  blocks event → response rendered as rich Markdown blocks
```

---

### Flow 3: Generate Flashcards

```
User selects sources (sidebar checkboxes)
User opens Studio panel           
User clicks "Flashcards" feature card
FlashcardConfigDialog opens:
  - Card count: 20
  - Difficulty: Medium
  - Topic: "Chapter 3"
User clicks Generate
  ↓
POST /flashcard {material_ids, card_count: 20, difficulty: "medium", topic: "Chapter 3"}
Backend generates flashcards (LLM call in thread pool)
  ↓
Response: {flashcards: [{question, answer}, ...]}
InlineFlashcardsView renders flip cards
User can save to notebook history
  ↓
POST /notebooks/{id}/content {contentType: "flashcard", data: {...}}
```

---

### Flow 4: Agent Code Execution

```
User types in chat: "/code plot a bar chart of the CSV data"
SlashCommandDropdown shows /code command
User selects it → pill shows "Code 💻"
User submits message
  ↓
POST /chat {message: "plot a bar chart...", intent_override: "CODE_EXECUTION", material_ids: [...]}
Backend:
  → agentic loop (CODE_EXECUTION)
  → LLM generates Python code
  → SSE: {type: "code_for_review", code: "import pandas..."}
Frontend: CodeReviewBlock rendered
User clicks "Run"
  ↓
POST /agent/run-generated {code, notebook_id}
Backend sandbox executes code → detects matplotlib output
SSE: {type: "stdout", content: "..."} 
SSE: {type: "artifact", type: "chart", data: "data:image/png;base64,..."}
Frontend: ChartRenderer shows the bar chart inline
```

---

### Flow 5: Podcast

```
User selects sources, opens Studio → Podcast
PodcastConfigDialog:
  - Mode: "overview"
  - Language: English
  - Host: "en-US-GuyNeural"
  - Guest: "en-US-JennyNeural"
User clicks Create
  ↓
POST /podcast/session {notebook_id, mode, language, host_voice, guest_voice, material_ids}
POST /podcast/session/{id}/generate
Backend: generates script via LLM → TTS each segment
WebSocket: podcast_event → segment-ready signals
  ↓
PodcastPlayer: streams audio segment by segment
 GET /podcast/session/{id}/audio/0
 GET /podcast/session/{id}/audio/1 ...
User pauses at segment 3, asks doubt
POST /podcast/session/{id}/question {question_text, paused_at_segment: 3}
Backend LLM answers question → TTS → audio URL returned
Doubt answer plays inline
User exports: POST /podcast/session/{id}/export {format: "pdf"}
GET /podcast/export/{export_id}/file → downloads transcript PDF
```

---

### Flow 6: Mind Map

```
User opens Studio → Mind Map
MindMapView: checks for saved mind map
GET /mindmap/{notebookId} → 404 (none exists)
User clicks Generate (sources selected)
  ↓
POST /mindmap {material_ids, notebook_id}
Backend: LLM generates hierarchical graph JSON
Response: {nodes: [...], edges: [...]}
Saved to GeneratedContent (contentType = "mindmap")
  ↓
Frontend: MindMapCanvas renders with React Flow + dagre layout
User clicks a node (e.g. "Photosynthesis")
pendingChatMessage = "Tell me more about Photosynthesis"
Chat panel activates with pre-filled message
User sends → RAG response about that topic
```
