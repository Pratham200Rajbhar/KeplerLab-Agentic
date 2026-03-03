## Plan: Migrate React/Vite Frontend to Next.js + Chakra UI

**TL;DR**: Migrate the existing 48-component React 19 + Vite SPA to Next.js 14 App Router with Chakra UI v3, Zustand for state management, and a restructured modular codebase. The app is heavily interactive (SSE streaming, WebSocket, audio playback, drag-and-drop), so most components will be client-rendered (`'use client'`) with an SSR shell for layouts. Key wins: file-based routing, layout nesting (unify duplicate headers), Zustand replacing 6 bloated contexts, Chakra UI replacing 2,274 lines of raw CSS, and a cleaner folder structure.

**Steps**

### Phase 1: Project Scaffolding

1. **Initialize Next.js project** in a new `frontend-next/` directory alongside the existing frontend. Use `npx create-next-app@latest` with App Router, TypeScript optional (keep JSX since codebase is JS), Tailwind CSS (to coexist with Chakra), ESLint. Configure next.config.js with API rewrites to proxy `/api/` to the backend (`http://localhost:8000`) — replacing the current nginx.conf proxy behavior during development.

2. **Install dependencies**: `@chakra-ui/react @chakra-ui/next-js @emotion/react zustand lucide-react react-markdown react-syntax-highlighter @xyflow/react dagre html-to-image jspdf katex rehype-katex rehype-raw remark-gfm remark-math next-themes`

3. **Environment variables**: Rename `VITE_API_BASE_URL` → `NEXT_PUBLIC_API_BASE_URL`, `VITE_APP_NAME` → `NEXT_PUBLIC_APP_NAME`, `VITE_APP_VERSION` → `NEXT_PUBLIC_APP_VERSION` in `.env.local`. Update all `import.meta.env.VITE_*` references in api/config.js to `process.env.NEXT_PUBLIC_*`.

4. **Migrate Google Fonts**: Remove font loading from index.html and use `next/font/google` in root layout for Inter, Google Sans, JetBrains Mono — enables automatic font optimization.

### Phase 2: Project Structure

5. **Create the new directory structure**:
```
frontend-next/src/
├── app/                          # Next.js App Router
│   ├── layout.jsx                # Root layout (providers, fonts, theme)
│   ├── page.jsx                  # / → HomePage (protected)
│   ├── loading.jsx               # Root loading skeleton
│   ├── not-found.jsx             # 404 page
│   ├── auth/
│   │   └── page.jsx              # /auth → AuthPage
│   ├── notebook/
│   │   └── [id]/
│   │       ├── layout.jsx        # Workspace layout (Header + 3-panel shell)
│   │       └── page.jsx          # /notebook/:id → Workspace
│   └── view/
│       └── page.jsx              # /view → FileViewerPage
├── components/
│   ├── ui/                       # Reusable Chakra-based primitives
│   │   ├── Button.jsx
│   │   ├── Modal.jsx
│   │   ├── Card.jsx
│   │   ├── Input.jsx
│   │   ├── Toast.jsx
│   │   ├── ConfirmDialog.jsx
│   │   ├── Spinner.jsx
│   │   └── DropZone.jsx
│   ├── layout/                   # Shell components
│   │   ├── Header.jsx
│   │   ├── Sidebar.jsx
│   │   └── ResizablePanel.jsx
│   ├── chat/                     # Chat feature module
│   │   ├── ChatPanel.jsx
│   │   ├── ChatMessage.jsx
│   │   ├── ChatEmptyState.jsx
│   │   ├── ChatHistoryModal.jsx
│   │   ├── MarkdownRenderer.jsx
│   │   ├── SlashCommand/
│   │   │   ├── Dropdown.jsx
│   │   │   ├── Pills.jsx
│   │   │   └── Badge.jsx
│   │   ├── Agent/
│   │   │   ├── ActionBlock.jsx
│   │   │   ├── StepsPanel.jsx
│   │   │   └── ThinkingBar.jsx
│   │   ├── CodeExecution/
│   │   │   ├── ExecutionPanel.jsx
│   │   │   └── ChartRenderer.jsx
│   │   ├── SuggestionDropdown.jsx
│   │   ├── ResearchProgress.jsx
│   │   ├── DocumentPreview.jsx
│   │   ├── GeneratedFileCard.jsx
│   │   ├── MiniBlockChat.jsx
│   │   └── BlockHoverMenu.jsx
│   ├── studio/                   # Studio feature module
│   │   ├── StudioPanel.jsx
│   │   ├── FlashcardsView.jsx
│   │   ├── QuizView.jsx
│   │   ├── ExplainerView.jsx
│   │   ├── ConfigDialogs.jsx
│   │   ├── ContentHistory.jsx
│   │   └── HistoryRenameModal.jsx
│   ├── podcast/                  # Podcast feature module (13 components, keep as-is)
│   │   ├── PodcastStudio.jsx
│   │   ├── ... (all 13 podcast components)
│   ├── mindmap/                  # Mind map feature module
│   │   ├── MindMapView.jsx
│   │   ├── MindMapCanvas.jsx
│   │   └── MindMapNode.jsx
│   ├── presentation/
│   │   └── PresentationView.jsx
│   ├── auth/
│   │   ├── LoginForm.jsx
│   │   ├── SignupForm.jsx
│   │   └── ProtectedRoute.jsx
│   └── notebook/
│       ├── NotebookCard.jsx      # Extract from HomePage inline
│       ├── SourceItem.jsx
│       ├── UploadDialog.jsx
│       └── WebSearchDialog.jsx
├── stores/                       # Zustand stores (replacing 6 contexts)
│   ├── useAuthStore.js
│   ├── useAppStore.js
│   ├── useThemeStore.js          # (or use next-themes directly)
│   ├── useToastStore.js
│   ├── usePodcastStore.js
│   └── useConfirmStore.js
├── lib/                          # Utilities & API layer
│   ├── api/                      # API modules (11 files, mostly portable)
│   │   ├── config.js
│   │   ├── auth.js
│   │   ├── notebooks.js
│   │   ├── materials.js
│   │   ├── chat.js
│   │   ├── generation.js
│   │   ├── mindmap.js
│   │   ├── podcast.js
│   │   ├── explainer.js
│   │   ├── agent.js
│   │   └── jobs.js
│   ├── utils/
│   │   ├── sse-parser.js         # Extract readSSEStream from ChatPanel
│   │   ├── constants.js          # From current constants/index.js
│   │   └── helpers.js
│   └── chakra/
│       └── theme.js              # Custom Chakra theme with current design tokens
├── hooks/                        # Custom hooks (5 existing + new)
│   ├── useMaterialUpdates.js
│   ├── useMicInput.js
│   ├── useMindMap.js
│   ├── usePodcastPlayer.js
│   ├── usePodcastWebSocket.js
│   └── useResizablePanel.js      # Extract from Sidebar/StudioPanel
├── styles/
│   └── globals.css               # Minimal — Tailwind base + any Chakra overrides
└── middleware.js                  # Auth middleware (redirect unauthenticated → /auth)
```

### Phase 3: Foundation Layer

6. **Create Chakra UI theme** in lib/chakra/theme.js: Map the current 80+ CSS custom properties from index.css into a Chakra theme config. Define `semanticTokens` for light/dark mode (surfaces, borders, text, accents, status colors). Configure the component variants to replace `.btn-primary`, `.btn-secondary`, `.btn-ghost`, `.btn-icon`, `.panel-surface`, `.glass`, `.card`, `.input`, `.textarea`, `.modal` classes. Use Chakra's `colorMode` system (integrated with `next-themes`) to replace the current `.dark` class toggle.

7. **Root layout** app/layout.jsx: Set up `ChakraProvider` with custom theme, `next-themes` `ThemeProvider`, and minimal global providers. Import fonts via `next/font/google`. Add the dark-mode FOUC prevention that's currently in index.html.

8. **Build Zustand stores** (replacing 6 contexts):
   - `useAuthStore` — from AuthContext.jsx (157 lines): JWT state, login/signup/logout actions, auto-refresh timer. Use Zustand middleware for persist (if needed).
   - `useAppStore` — from AppContext.jsx (157 lines): Split the massive context into slices: `notebookSlice` (currentNotebook, draftMode, materials, selectedSources), `chatSlice` (sessionId, messages, pendingChatMessage), `studioSlice` (flashcards, quiz, notes, activePanel), `uiSlice` (loading, error). Keep the `_podcastWsHandlerRef` as a Zustand ref.
   - `useToastStore` — from ToastContext.jsx: Queue management with Chakra Toast integration.
   - `useConfirmStore` — from ConfirmContext.jsx: Promise-based dialog state.
   - `usePodcastStore` — from PodcastContext.jsx (484 lines): Full podcast state machine.
   - Theme: Use `next-themes` directly instead of a custom store — replaces ThemeContext.jsx.

9. **Migrate API layer** lib/api/: Copy all 11 API modules. Update `import.meta.env.VITE_*` → `process.env.NEXT_PUBLIC_*`. The `apiFetch` wrapper, token management, and refresh mutex are browser-only logic — no SSR changes needed since API calls happen in client components.

10. **Extract reusable utilities**:
    - `sse-parser.js` — extract the inline `readSSEStream` function (65 lines) from ChatPanel.jsx into a standalone utility.
    - `useResizablePanel.js` — extract the duplicated `document.addEventListener('mousemove'/'mouseup')` resize logic from Sidebar.jsx and StudioPanel.jsx into a shared hook.

### Phase 4: Auth & Middleware

11. **Next.js middleware** middleware.js: Create edge middleware that checks for the auth cookie (refresh token HttpOnly cookie set by backend). If no cookie and route is protected (`/`, `/notebook/*`), redirect to `/auth`. This replaces the `ProtectedRoute` wrapper from App.jsx. The `/auth` and `/view` routes remain public.

12. **Auth page** app/auth/page.jsx: Migrate AuthPage.jsx, Login.jsx, Signup.jsx. Replace `useNavigate` with `useRouter` from `next/navigation`. Use Chakra form components (`Input`, `FormControl`, `Button`) for improved styling.

### Phase 5: Core Pages & Layouts

13. **Home page** app/page.jsx: Migrate HomePage.jsx (368 lines). The page can have an SSR shell (loading skeleton) with a `'use client'` inner component for notebook CRUD interactivity. Replace inline notebook cards with a `NotebookCard` component. Use Chakra `SimpleGrid`, `Card`, `Menu`, `IconButton`. Replace `useNavigate()` → `useRouter().push()`. Unify the duplicate header with the layout header.

14. **Workspace layout** [app/notebook/[id]/layout.jsx](frontend-next/src/app/notebook/%5Bid%5D/layout.jsx): Create a shared workspace layout with `Header` + 3-panel flex structure (Sidebar | ChatPanel | StudioPanel). This replaces the inline `Workspace` component from App.jsx. Read `params.id` via the layout props.

15. **Workspace page** [app/notebook/[id]/page.jsx](frontend-next/src/app/notebook/%5Bid%5D/page.jsx): `'use client'` — loads notebook data via `useEffect` + `getNotebook(id)`, sets it in `useAppStore`. Renders the 3-panel workspace.

16. **File viewer** app/view/page.jsx: Migrate FileViewerPage.jsx as a public page.

### Phase 6: Feature Modules Migration

17. **Header** components/layout/Header.jsx: Migrate Header.jsx (132 lines). Use Chakra: `Flex`, `IconButton`, `Menu`/`MenuButton`/`MenuList`/`MenuItem`, `Avatar`, `Tooltip`. Replace `useNavigate` → `useRouter`. Replace `document.addEventListener` click-outside with Chakra `Menu`'s built-in outside-click handling.

18. **Sidebar** components/layout/Sidebar.jsx: Migrate Sidebar.jsx (634 lines). Use `useResizablePanel` hook (extracted). Use Chakra: `Box`, `VStack`, `Input`, `Badge`, `Tooltip`, `Tabs`. Break down the 634-line monolith into sub-components: `SourcesList`, `SourceFilters`, `MaterialUploadZone`.

19. **ChatPanel** components/chat/ChatPanel.jsx: Migrate ChatPanel.jsx (1082 lines). **CRITICAL** — this is the most complex component. Strategy:
    - Mark as `'use client'`
    - Replace `useSearchParams` import from `react-router-dom` → `next/navigation`
    - Extract `readSSEStream` to `lib/utils/sse-parser.js`
    - Extract `handleSend` logic (~150 lines) into a custom `useChatSend` hook
    - Split into sub-components: `ChatInput`, `ChatMessages`, `ChatToolbar`
    - Use Chakra: `Textarea`, `IconButton`, `Box`, `Flex`, `Spinner`
    - Keep SSE streaming logic unchanged (browser `fetch` + `ReadableStream`)

20. **StudioPanel** components/studio/StudioPanel.jsx: Migrate StudioPanel.jsx (836 lines). Use `next/dynamic` for heavy lazy imports (`PresentationView`, `PodcastStudio`, `MindMapView`). Break into sub-components. Use `useResizablePanel` hook.

21. **Mind map components**: Migrate MindMapView.jsx, MindMapCanvas.jsx, MindMapNode.jsx. Use `next/dynamic` with `{ ssr: false }` since `@xyflow/react` requires DOM.

22. **Podcast components**: Migrate all 13 podcast components. Mark all as `'use client'`. The podcast module is self-contained — minimal changes needed beyond import paths and Chakra styling.

23. **Chat sub-components**: Migrate all 15 chat sub-components. Most are presentational — use Chakra equivalents for buttons, modals, tooltips.

24. **Studio sub-components**: Migrate flashcards, quiz, explainer views and config dialogs. Use Chakra's `Radio`, `Slider`, `Switch`, `Select` for config dialogs.

### Phase 7: UI Redesign with Chakra

25. **Build reusable UI primitives** in `components/ui/`:
    - `Modal.jsx` — Chakra `Modal`/`ModalOverlay`/`ModalContent` wrapper replacing the custom Modal.jsx
    - `ConfirmDialog.jsx` — Chakra `AlertDialog` replacing ConfirmContext dialog
    - `DropZone.jsx` — Styled drag-and-drop zone with Chakra styling
    - `Toast` — Use Chakra's built-in `useToast` replacing custom toast context

26. **Design improvements**:
    - **Dashboard**: Card hover animations, better empty states, skeleton loading via Chakra `Skeleton`
    - **Sidebar**: Smoother resize with Chakra `Drawer` for mobile, collapsible sections with `Accordion`
    - **Chat**: Better message bubbles with `Card` variants, improved code block styling, typing indicator with Chakra `Spinner`
    - **Studio**: Tab-based navigation with Chakra `Tabs`, better flashcard flip animations, quiz progress bar
    - **Auth**: Full-page centered layout with `Container` + `Card`, form validation feedback with `FormErrorMessage`
    - **Responsive**: Use Chakra's responsive props (`base`, `md`, `lg`) instead of raw media queries

### Phase 8: Cleanup & Optimization

27. **Remove the 2,274-line index.css**: All custom component classes (`.btn-primary`, `.panel-surface`, `.glass`, `.card`, etc.) are replaced by Chakra component variants. Keep only minimal global resets in globals.css. Preserve any truly unique CSS (e.g., presentation iframe styles, markdown content styles) as CSS modules.

28. **Presentation styles**: Convert PresentationView.css to a CSS module PresentationView.module.css.

29. **Error handling**: Replace ErrorBoundary.jsx with Next.js error.jsx convention files at each route segment.

30. **Loading states**: Add loading.jsx files at route segments for streaming SSR loading UI using Chakra `Skeleton`.

31. **Docker migration**: Update Dockerfile for Next.js: use `next build` → `next start` (or standalone output), update env var names, remove nginx (Next.js has its own server). Alternatively, keep nginx as a reverse proxy in front of `next start`.

32. **Metadata & SEO**: Add `metadata` exports in root and page layouts for proper `<title>`, `<meta>` tags — currently hardcoded in index.html.

**Verification**
- Run `npm run dev` and verify all 4 routes render correctly (`/auth`, `/`, `/notebook/:id`, `/view`)
- Test auth flow: login → redirect to home → create notebook → navigate to workspace
- Test chat SSE streaming: send a message and verify real-time token streaming works
- Test WebSocket material updates: upload a file and verify processing status updates
- Test podcast audio playback (blob URL + auth header)
- Test mind map rendering with `@xyflow/react` (dynamic import, no SSR)
- Test dark/light theme toggle with `next-themes` + Chakra `colorMode`
- Test mobile responsiveness at 768px and 1024px breakpoints
- Run `next build` to check for any SSR errors (components using `window`/`document` without guards)
- Lighthouse audit: compare performance metrics against current Vite build

**Decisions**
- **Chakra UI v3** over raw Tailwind: Provides accessible, pre-built components (Modal, Menu, Toast, Drawer, Tabs, Accordion) that replace ~500 lines of custom CSS component classes
- **Zustand** over React Context: Avoids provider nesting hell (6 deep), enables selective re-renders, simpler API for the massive `AppContext` (30+ state variables)
- **App Router** over Pages Router: Layout nesting naturally solves the duplicate header problem (HomePage vs Workspace header), and gives us `loading.jsx`/`error.jsx` conventions
- **`next-themes`** over custom ThemeContext: Battle-tested, handles FOUC, integrates with Chakra's `colorMode`
- **Edge middleware** for auth over client-side `ProtectedRoute`: Prevents flash of protected content before redirect
- **Keep Tailwind alongside Chakra**: Utility classes still useful for one-off spacing/layout; Chakra handles component styling
- **Module-level `_podcastWsHandlerRef`**: Move to Zustand store ref to avoid SSR singleton issues
- **SSE streaming stays client-side**: No benefit from server-side proxy; keep existing `fetch` + `ReadableStream` pattern