# KeplerLab Frontend - Complete Architecture and Feature Flow

## 1. Scope and What Was Read

This document summarizes the frontend after a full workspace scan and direct source inspection.

- Workspace root: `/disk1/KeplerLab_Agentic`
- Frontend folder: `frontend/`
- Total files in frontend directory (includes `.next` build cache): `41501`
- Source-focused frontend files under `src/`: `125`
- Core files read directly: `package.json`, `next.config.mjs`, `src/app/layout.jsx`, `src/app/providers.jsx`, `src/middleware.js`, `src/lib/api/config.js`, plus route/component/store inventories.

Notes:
- The very high file count is mostly `.next` development/build artifacts.
- Architecture coverage in this doc focuses on maintained source code.

## 2. Frontend Stack Overview

- Framework: Next.js `16.1.6` (App Router)
- React: `19.2.3`
- Styling: Tailwind CSS + CSS variables (`src/styles/globals.css`)
- State management: Zustand stores (`src/stores/`)
- Markdown/math/code rendering: `react-markdown`, `remark-gfm`, `remark-math`, `rehype-katex`, `react-syntax-highlighter`
- Diagram/graph UI: `@xyflow/react`, `dagre`
- Theming: `next-themes`
- Document viewing: `@cyntler/react-doc-viewer`

## 3. Runtime App Structure

### 3.1 App Routes (`src/app`)

- `/` -> `src/app/page.jsx`
- `/auth` -> `src/app/auth/page.jsx` + `src/app/auth/layout.jsx`
- `/notebook/[id]` -> `src/app/notebook/[id]/page.jsx` + layout
- `/view` -> `src/app/view/page.jsx`
- global error/loading pages:
- `src/app/error.jsx`
- `src/app/global-error.jsx`
- `src/app/loading.jsx`
- `src/app/not-found.jsx`

### 3.2 Root Layout and Providers

Source: `src/app/layout.jsx`, `src/app/providers.jsx`.

- Fonts loaded via Next font system:
- Inter (`--font-inter`)
- JetBrains Mono (`--font-jetbrains`)
- Plus Jakarta Sans (`--font-headline`)
- Root provider stack:
- `ThemeProvider` (`next-themes`, class mode)
- `AuthInitializer` (calls `useAuthStore.initAuth()` on mount)
- global UI overlays: `ToastContainer` and `ConfirmDialog`

### 3.3 Route Protection (Middleware)

Source: `src/middleware.js`.

Behavior:

- Public paths: `/`, `/auth`, `/view`, `/api`, static assets.
- All other paths require `refresh_token` cookie.
- If cookie missing -> redirect to `/auth` with optional `redirect` query.

## 4. API Integration Architecture

### 4.1 Base API Layer

Source: `src/lib/api/config.js`.

- Base URL from `NEXT_PUBLIC_API_BASE_URL` (fallback `http://localhost:8000`).
- Access token stored in-memory (not localStorage).
- `apiFetch` and `apiFetchFormData` include:
- credentials mode `include`
- bearer auth header when token exists
- automatic refresh-on-401 using `/auth/refresh`
- one-flight refresh promise to prevent duplicate refresh calls
- session expiry callback support (`onSessionExpired`)

### 4.2 Streaming Layer

Source: `src/lib/stream/streamClient.js`.

- SSE parser utility for streaming responses.
- Used by chat and streaming generation features.
- Event-driven handlers parse server `event` + `data` payloads.

### 4.3 API Client Modules

Files under `src/lib/api/`:

- `auth.js`
- `chat.js`
- `notebooks.js`
- `materials.js`
- `generation.js`
- `presentation.js`
- `podcast.js`
- `mindmap.js`
- `explainer.js`
- `aiResource.js`
- `agent.js`

These modules isolate endpoint definitions and request/response handling away from component code.

### 4.4 Next.js Rewrites and Proxying

Source: `frontend/next.config.mjs`.

Rewrites:

- `/api/presentation/slides/:path*` -> `${backend}/presentation/slides/:path*`
- `/api/:path*` -> `${backend}/:path*`

This allows frontend-origin API calls through Next runtime while targeting backend service.

## 5. State Management (Zustand)

Stores in `src/stores/`:

- `useAuthStore.js`: auth lifecycle, login/signup/logout/init refresh scheduling
- `useAppStore.js`: cross-feature notebook/session/material/UI state
- `useChatStore.js`: chat message/session/streaming state
- `useNotebookStore.js`: notebook context state
- `useMaterialStore.js`: material lists and selection state
- `usePodcastStore.js`: podcast session/playback/generation state
- `useMindMapStore.js`: mind map UI/data state
- `useUIStore.js`: generic loading/panel state
- `useToastStore.js`: toast queue/state
- `useConfirmStore.js`: confirm dialog control state

Auth store details (`useAuthStore.js`):

- `initAuth` attempts refresh and user fetch at app startup.
- Refresh timer schedules token refresh at configured interval.
- Includes retry backoff for refresh failures.
- On terminal refresh failure, user is logged out and redirected.

## 6. UI and Component Architecture

### 6.1 Top-Level Feature Areas

- `src/components/layout/`: header and sidebar frame
- `src/components/chat/`: full chat experience (messages, input, streaming panels, artifact rendering)
- `src/components/studio/`: multi-feature generation panel and history dialogs
- `src/components/notebook/`: source/material actions
- `src/components/presentation/`: presentation creation/edit/view flows
- `src/components/podcast/`: podcast studio, player, transcript, export and Q&A interactions
- `src/components/mindmap/`: visual mind map rendering
- `src/components/viewer/`: generic file/document viewer
- `src/components/ui/`: modal/confirm/toast/error boundary primitives

### 6.2 Main Notebook Workspace Composition

Source: `src/app/notebook/[id]/page.jsx`.

Workspace composition:

1. Header
2. Sidebar (materials/sources)
3. Chat panel
4. Studio panel

Additional behavior:

- Dynamic imports for heavy panels (`Sidebar`, `ChatPanel`, `StudioPanel`).
- Draft notebook mode support (`id === 'draft'`).
- Notebook load/switch reset logic to avoid stale cross-notebook state.
- Mobile sidebar overlay toggling.

### 6.3 Reusable Hooks

Files in `src/hooks/`:

- `useChat.js`
- `useMaterialUpdates.js`
- `usePodcastPlayer.js`
- `useMicInput.js`
- `useAutoScroll.js`
- `useResizablePanel.js`

`useMaterialUpdates` handles realtime update channel behavior from backend websocket job notifications.

## 7. End-to-End Frontend Feature Flows

## 7.1 Authentication Flow

1. User visits protected route.
2. Middleware checks `refresh_token` cookie.
3. If present, app mounts and `AuthInitializer` runs `initAuth`.
4. `initAuth` calls `/auth/refresh`, stores access token in memory, then fetches current user.
5. UI state transitions to authenticated mode.

Failure path:

- If refresh fails, auth store clears state and user returns to `/auth`.

## 7.2 Notebook Load and Workspace Init

1. Route `/notebook/[id]` resolves ID.
2. If draft mode, local draft notebook state is created.
3. Else frontend fetches notebook details via API module.
4. App store is reset for notebook switch and repopulated.
5. Sidebar/chat/studio render on hydrated state.

## 7.3 Material Ingestion and Status

1. User uploads file/URL/text through sidebar dialogs.
2. API calls hit backend `/upload*` endpoints.
3. Backend returns async job/material IDs.
4. Frontend subscribes to status updates (websocket hook/store integration).
5. Materials list updates through lifecycle states until completed.

## 7.4 Chat and Streaming Interaction

1. User submits prompt in chat input.
2. Chat API call opens streaming response.
3. SSE parser dispatches events incrementally.
4. Message list and progress/tool panels update in near-real-time.
5. Final state persisted in chat/session stores and notebook context.

Supports advanced actions:

- Follow-up on block-level content
- Suggestions/empty-state suggestions
- Prompt optimization
- Artifact rendering and download cards

## 7.5 Generation Feature Flows

Studio panel integrates generation features with shared material selection context:

- Flashcards
- Quiz
- Mind map
- Presentation
- Explainer
- Podcast

General flow pattern:

1. Select source materials.
2. Trigger feature-specific API call.
3. Receive structured response or async job status.
4. Render result in inline feature view/editor/player.
5. Persist history/state in store and notebook content collections.

## 8. Styling and Theming Architecture

### 8.1 Tailwind Setup

Source: `frontend/tailwind.config.js`.

- Dark mode strategy: class-based.
- Tailwind scans all source app/components paths.
- Design tokens mapped from CSS variables:
- surface/border/text semantic colors
- accent/success/danger/info variables
- stitch-* themed landing page token set
- Custom font families bound to Next font CSS variables.
- Custom animation/keyframe utilities included.

### 8.2 Global CSS

Source: `src/styles/globals.css`.

- Defines design-system-level CSS variables used by Tailwind semantic mappings.
- Provides light/dark theme value sets consumed throughout components.

## 9. Tooling and Build Config

- ESLint config (`eslint.config.mjs`): Next core-web-vitals preset + custom global ignores.
- PostCSS config (`postcss.config.mjs`): Tailwind + autoprefixer.
- Path alias (`jsconfig.json`): `@/*` -> `./src/*`.
- Next output mode: standalone (Docker-friendly).
- React strict mode enabled.

## 10. Frontend Source Inventory (Complete, Source-Focused)

All source-focused frontend files discovered under `src/`:

```text
src/app/auth/layout.jsx
src/app/auth/page.jsx
src/app/error.jsx
src/app/global-error.jsx
src/app/layout.jsx
src/app/loading.jsx
src/app/notebook/[id]/layout.jsx
src/app/notebook/[id]/page.jsx
src/app/not-found.jsx
src/app/page.jsx
src/app/providers.jsx
src/app/view/page.jsx
src/components/chat/AgentProgressPanel.jsx
src/components/chat/AnnotatedText.jsx
src/components/chat/ArtifactDownloadCard.jsx
src/components/chat/ArtifactGallery.jsx
src/components/chat/ArtifactTablePreview.jsx
src/components/chat/ArtifactViewer.jsx
src/components/chat/ChatHistorySidebar.jsx
src/components/chat/ChatInput.jsx
src/components/chat/ChatMessage.jsx
src/components/chat/ChatPanel.jsx
src/components/chat/CodePanel.jsx
src/components/chat/CodeWorkspace.jsx
src/components/chat/CollapsibleActionBlock.jsx
src/components/chat/CommandBadge.jsx
src/components/chat/CopyButton.jsx
src/components/chat/DocumentPreview.jsx
src/components/chat/EmptyState.jsx
src/components/chat/MarkdownRenderer.jsx
src/components/chat/MessageItem.jsx
src/components/chat/MessageList.jsx
src/components/chat/MiniBlockChat.jsx
src/components/chat/OutputRenderer.jsx
src/components/chat/PromptOptimizerDialog.jsx
src/components/chat/ResearchReport.jsx
src/components/chat/SelectionMenu.jsx
src/components/chat/TechnicalDetails.jsx
src/components/chat/TypingIndicator.jsx
src/components/chat/WebSearchProgressPanel.jsx
src/components/chat/WebSearchStrip.jsx
src/components/chat/WebSources.jsx
src/components/Dashboard.jsx
src/components/LandingPage.jsx
src/components/layout/Header.jsx
src/components/layout/Sidebar.jsx
src/components/materials/AIResourceBuilder.jsx
src/components/mindmap/MindMapCanvas.jsx
src/components/mindmap/MindMapEdge.jsx
src/components/notebook/SourceItem.jsx
src/components/notebook/UploadDialog.jsx
src/components/notebook/WebSearchDialog.jsx
src/components/podcast/index.js
src/components/podcast/PodcastChapterBar.jsx
src/components/podcast/PodcastConfigDialog.jsx
src/components/podcast/PodcastDoubtHistory.jsx
src/components/podcast/PodcastExportBar.jsx
src/components/podcast/PodcastGenerating.jsx
src/components/podcast/PodcastInterruptDrawer.jsx
src/components/podcast/PodcastMiniPlayer.jsx
src/components/podcast/PodcastModeSelector.jsx
src/components/podcast/PodcastPlayer.jsx
src/components/podcast/PodcastSessionLibrary.jsx
src/components/podcast/PodcastStudio.jsx
src/components/podcast/PodcastTranscript.jsx
src/components/podcast/VoicePicker.jsx
src/components/presentation/PresentationDialog.jsx
src/components/presentation/PresentationEditor.jsx
src/components/presentation/PresentationView.css
src/components/presentation/PresentationViewer.jsx
src/components/presentation/PresentationView.jsx
src/components/presentation/SlideCanvas.jsx
src/components/presentation/SlideInputBox.jsx
src/components/presentation/SlideList.jsx
src/components/studio/ConfigDialogs.jsx
src/components/studio/ContentHistory.jsx
src/components/studio/ExplainerDialog.jsx
src/components/studio/FeatureCard.jsx
src/components/studio/HistoryRenameModal.jsx
src/components/studio/index.js
src/components/studio/InlineExplainerView.jsx
src/components/studio/InlineFlashcardsView.jsx
src/components/studio/InlineQuizView.jsx
src/components/studio/StudioPanel.jsx
src/components/ui/ConfirmDialog.jsx
src/components/ui/ErrorBoundary.jsx
src/components/ui/Modal.jsx
src/components/ui/ToastContainer.jsx
src/components/viewer/DocViewerRenderer.jsx
src/components/viewer/FileViewerContent.jsx
src/hooks/useAutoScroll.js
src/hooks/useChat.js
src/hooks/useMaterialUpdates.js
src/hooks/useMicInput.js
src/hooks/usePodcastPlayer.js
src/hooks/useResizablePanel.js
src/lib/api/agent.js
src/lib/api/aiResource.js
src/lib/api/auth.js
src/lib/api/chat.js
src/lib/api/config.js
src/lib/api/explainer.js
src/lib/api/generation.js
src/lib/api/materials.js
src/lib/api/mindmap.js
src/lib/api/notebooks.js
src/lib/api/podcast.js
src/lib/api/presentation.js
src/lib/config/slashCommands.js
src/lib/stream/streamClient.js
src/lib/utils/constants.js
src/lib/utils/helpers.js
src/lib/utils/parseSlashCommand.js
src/middleware.js
src/stores/useAppStore.js
src/stores/useAuthStore.js
src/stores/useChatStore.js
src/stores/useConfirmStore.js
src/stores/useMaterialStore.js
src/stores/useMindMapStore.js
src/stores/useNotebookStore.js
src/stores/usePodcastStore.js
src/stores/useToastStore.js
src/stores/useUIStore.js
src/styles/globals.css
```

## 11. Integration Crosswalk (Frontend -> Backend)

Frontend modules are aligned to backend APIs as follows:

- `lib/api/auth.js` -> `/auth/*`
- `lib/api/chat.js` -> `/chat/*`
- `lib/api/notebooks.js` -> `/notebooks/*`
- `lib/api/materials.js` -> `/upload*`, `/materials/*`, `/search/web`
- `lib/api/generation.js` -> `/flashcard`, `/quiz`
- `lib/api/presentation.js` -> `/presentation/*`
- `lib/api/podcast.js` -> `/podcast/*`
- `lib/api/mindmap.js` -> `/mindmap`
- `lib/api/explainer.js` -> `/explainer/*`
- `lib/api/aiResource.js` -> `/ai-resource-builder`

---

If needed, a next pass can add exact per-component API call references and state write-paths (function-by-function mapping).
