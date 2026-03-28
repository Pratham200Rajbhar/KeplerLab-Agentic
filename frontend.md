# Frontend Architecture (KeplerLab Agentic)

## 1. Overview
Frontend is a Next.js App Router application focused on a notebook-centric AI workspace.

Primary responsibilities:
- authenticate user and bootstrap session
- provide notebook workbench (sidebar + source management + chat + studio + viewer)
- orchestrate generation workflows (flashcards, quiz, mindmap, presentation, explainer, podcast)
- consume SSE + websocket realtime updates from backend
- persist and restore UI state through URL/store/session APIs

Core technologies:
- Next.js (App Router)
- React client components
- Zustand stores for domain state
- Tailwind CSS and custom component styling
- fetch-based API layer with automatic token refresh

## 2. Application Structure

### 2.1 App Router Layout
Key app entries under `frontend/src/app`:
- `layout.jsx`: global shell and providers
- `providers.jsx`: client-side provider wiring
- `page.jsx`: authenticated landing/dashboard flow
- `auth/page.jsx`: login/signup UI
- `view/page.jsx`: standalone file viewer flow
- `notebook/[id]/page.jsx`: notebook workspace route

### 2.2 Middleware and Route Protection
`frontend/src/middleware.js`:
- protects app pages by checking auth token cookies
- redirects unauthenticated users to `/auth`
- prevents authenticated users from revisiting auth pages
- allows static and API exceptions as configured

### 2.3 Runtime Config
`next.config.mjs` and `src/lib/api/config.js` control:
- backend base URL selection
- proxy/rewrite behavior for API routes (where configured)
- environment-specific endpoint composition

## 3. Provider and Bootstrap Model

## 3.1 Global Bootstrap
`src/app/layout.jsx` mounts global providers and baseline app frame.

`src/app/providers.jsx` initializes client-side concerns (state subscriptions, query/global wrappers if configured).

## 3.2 Auth Bootstrap
`src/stores/useAuthStore.js` manages:
- token state and auth status
- `initializeAuth` bootstrapping on app load
- `login`, `signup`, `logout`, `refreshToken` flows
- session-expired callback integration with API layer

Auth restoration pattern:
1. attempt current-user fetch/validation
2. if access token expired, call refresh endpoint
3. on refresh success, retry original request
4. on failure, clear auth state and redirect to auth route

## 4. State Architecture (Zustand Stores)

## 4.1 Store Topology
Major stores in `src/stores`:
- `useAuthStore`: auth lifecycle
- `useAppStore`: global UI + selected notebook context
- `useNotebookStore`: notebook list and active notebook metadata
- `useMaterialStore`: material list/status and source operations
- `useChatStore`: chat sessions/messages/stream state
- `usePodcastStore`: podcast session and playback/progress state
- `useMindMapStore`: mindmap generation/render state

### 4.2 Cross-Store Interaction Patterns
Common interaction style:
- auth store provides token/session validity
- API utilities call auth refresh logic on 401
- feature stores call domain API clients then update local slices
- websocket hooks fan out live events into relevant stores

## 5. API Transport Layer

### 5.1 Centralized Fetch Wrapper
`src/lib/api/auth.js` and `src/lib/api/config.js` provide common request behavior:
- attach bearer token
- include credentials when needed for refresh cookie
- normalized error handling
- 401 retry with token refresh

### 5.2 Domain API Clients
`src/lib/api/*` modules encapsulate endpoint groups:
- `notebooks.js`, `materials.js`, `chat.js`
- `generation.js`, `presentation.js`, `podcast.js`, `explainer.js`
- `mindmap.js`, `aiResource.js`, `agent.js`

Benefits:
- route constants stay centralized
- components/hooks avoid hand-rolled fetch calls
- retry and auth behavior consistent across domains

## 6. Realtime Architecture

## 6.1 SSE Client for Chat/Tool Streams
`src/lib/stream/streamClient.js` parses text/event-stream messages and dispatches event callbacks.

Consumed by chat hooks/components to process:
- incremental tokens
- tool progress blocks
- agent status/plan/step events
- artifacts and completion markers

## 6.2 Websocket Hook for Background Progress
`src/hooks/useMaterialUpdates.js` maintains websocket connection to backend `/ws/jobs/{user_id}`:
- auth token included in connection contract
- reconnect with backoff behavior
- ping/pong and lifecycle handling
- dispatch of `material_update`, notebook updates, podcast and presentation progress

## 7. Notebook Workspace Composition

## 7.1 Main Workspace Page
`src/app/notebook/[id]/page.jsx` composes notebook experience around:
- left navigation/sidebar
- central chat/studio tabs
- optional viewer and auxiliary dialogs

Route param notebook ID is the anchor for:
- source selection
- chat sessions/history
- generated outputs

## 7.2 Sidebar Responsibilities
`src/components/layout/Sidebar.jsx` handles:
- notebook navigation and creation
- source management entry points (upload/url/text/web)
- trigger points for generation workflows
- session-aware transitions between dashboard and notebook views

## 7.3 Dashboard Surface
`src/components/Dashboard.jsx` provides overview tiles/history/quick actions for notebook workspaces.

## 8. Chat UX and Command Routing

## 8.1 Chat Composition
Primary chat components:
- `src/components/chat/ChatPanel.jsx`
- `src/components/chat/ChatInput.jsx`
- `src/components/chat/MessageItem.jsx`

Core behavior:
- render message history by session
- stream incremental assistant updates
- display tool/status blocks and generated artifacts
- support edits/deletes and follow-up actions

## 8.2 Chat Hook Orchestration
`src/hooks/useChat.js` coordinates:
- submit message requests
- maintain local stream state
- parse SSE events into message state transitions
- persist/reload session context

## 8.3 Slash Command System
`src/lib/config/slashCommands.js` + `src/lib/utils/parseSlashCommand.js`:
- defines available commands and semantics
- extracts command/intents from user input
- forwards intent metadata to backend chat endpoint

Observed command classes include agent, research/web, code, and image generation modes.

## 9. Studio and Generation Workflows

## 9.1 Studio Panel
`src/components/studio/StudioPanel.jsx` aggregates generation actions:
- flashcards
- quiz
- mindmap
- presentation
- explainer
- podcast

Panel behavior:
- sends generation requests with notebook/material context
- tracks async status
- surfaces generated content history and opening/downloading flows

## 9.2 Domain-Specific State
Dedicated stores/hooks keep generation domains isolated:
- podcast: session timeline, playback assets, progress events
- mindmap: node/edge graph and render layout state
- presentation/explainer: generation status and content retrieval

## 10. Viewer and External Content Flow

## 10.1 Notebook Viewer Components
`src/components/viewer/FileViewerContent.jsx` and `DocViewerRenderer.jsx` render proxied remote or generated documents.

### 10.2 Standalone Viewer Route
`src/app/view/page.jsx` supports direct file-viewer mode.

Viewer security model relies on backend file-viewer endpoints (`/api/v1/file-viewer/info` and `/api/v1/file-viewer/proxy`) which enforce URL safety and controlled proxy retrieval.

## 11. UX Data Flow Patterns

### 11.1 Initial Page Load
1. middleware checks auth cookie
2. auth store initializes user/session
3. notebooks/materials/sessions fetched lazily by active route
4. websocket connection established for live updates

### 11.2 Sending a Chat Request
1. user submits prompt (possibly slash command)
2. hook builds payload with notebook/session/source selection
3. SSE stream opens
4. UI updates token-by-token and tool-by-tool
5. completion event commits final message state

### 11.3 Material Upload Feedback Loop
1. upload initiated from sidebar/dialog
2. backend queues processing
3. websocket emits `material_update`
4. material store updates status counters/list
5. chat source selector reflects availability

## 12. Error Handling and Resilience

Implemented resilience patterns:
- API wrapper normalizes errors and refreshes on 401
- auth store invalidates session cleanly on refresh failure
- websocket reconnect logic for transient drops
- chat stream parser handles partial/chunked SSE frames

Potential sensitivity areas:
- UX consistency when legacy and v2 generation endpoints coexist
- race conditions between optimistic UI updates and delayed websocket confirmations

## 13. Coupling to Backend Contracts
Critical contracts frontend depends on:
- chat SSE event names and payload schemas
- websocket event names for materials/podcast/presentation
- notebook/source selection APIs
- generated content identifiers and download URLs
- auth refresh cookie + bearer token interplay

When backend event names or payload shape changes, corresponding updates are required in:
- `useChat` stream handlers
- `streamClient` parsing callbacks
- `useMaterialUpdates` websocket dispatch mapping
- related domain stores and components

## 14. End-to-End User Journey Snapshot
1. user authenticates on `/auth`
2. lands on dashboard and opens/creates notebook
3. uploads sources from sidebar
4. receives websocket progress while materials process
5. chats with retrieval/agent/code/research modes via slash commands
6. opens Studio to generate flashcards/quiz/mindmap/presentation/explainer/podcast
7. views/downloads generated artifacts and content history
