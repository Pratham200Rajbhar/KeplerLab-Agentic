You are a senior frontend engineer working on KeplerLab — Next.js 16, React 19, Tailwind CSS, Zustand v5.
Reference: frontend.md (current state), problem.md (known issues), backend prompt (SSE event schemas).
Apply every fix and feature change below. Do not skip any section.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 1 — SLASH COMMAND SYSTEM (sole intent mechanism)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Slash commands are the ONLY way intent is communicated to the backend.
No client-side intent inference. No fallback guessing. Frontend sends what user picked.

Update `slashCommands.js`:
  Each command definition must have:
  {
    command:     string,   // "/agent", "/research", "/code", "/web"
    intent:      string,   // "AGENT", "WEB_RESEARCH", "CODE_EXECUTION", "WEB_SEARCH"
    icon:        string,   // emoji or lucide icon name
    label:       string,   // display name
    description: string,   // shown in dropdown
    placeholder: string,   // shown in input when command is active
  }

  /agent     → intent: "AGENT"         → placeholder: "Ask the agent to analyze, generate charts, build files..."
  /research  → intent: "WEB_RESEARCH"  → placeholder: "What do you want deeply researched on the web?"
  /code      → intent: "CODE_EXECUTION"→ placeholder: "Describe what Python to run..."
  /web       → intent: "WEB_SEARCH"    → placeholder: "Quick web question..."
  (none)     → omit intent_override    → placeholder: "Ask about your selected materials..."

When sending a chat message:
  - Active slash command → include `intent_override: command.intent` in request body
  - No active slash command → omit `intent_override` entirely (backend defaults to RAG)
  - Remove ALL other client-side intent logic

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 2 — CRITICAL BUG FIXES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FIX 1 — REACT KEYS (wrong reconciliation on reorder/insert)
Replace ALL `key={index}` with `key={item.id}` across:
  - ChatMessage list in ChatPanel/ChatMessageList
  - SourceItem list in Sidebar
  - Notebook grid cards on dashboard page
  - Flashcard list in InlineFlashcardsView
  - Quiz option list in InlineQuizView
  - Any other mapped list — audit all .map() calls

FIX 2 — SERIALIZABLE ZUSTAND STATE

  useAppStore:
    Change `selectedSources: new Set()` → `selectedSources: []`
    Add selector: `isSourceSelected: (id) => state.selectedSources.includes(id)`
    Update `toggleSourceSelection(id)`:
      selected → filter out id
      not selected → [...selectedSources, id]
    Update `selectAllSources()` to set array of all material ids
    Update `deselectAllSources()` to set []

  usePodcastStore:
    Remove `_audioEl` from store state entirely
    Remove `_audioCache` from store state entirely
    Move both to `useRef` inside `usePodcastPlayer.js`:
      const audioElRef = useRef(new Audio())
      const audioCacheRef = useRef(new Map())
    Add `cleanupAudio()` action that the hook calls on unmount:
      audioCacheRef.current.forEach(url => URL.revokeObjectURL(url))
      audioCacheRef.current.clear()

FIX 3 — SPLIT useAppStore INTO FOCUSED STORES
Create separate store files:

  useChatStore.js:
    State: messages, sessionId, isStreaming, abortController, pendingChatMessage
    Actions: addMessage, updateLastMessage, clearMessages, setStreaming,
             setAbortController, setPendingChatMessage

  useMaterialStore.js:
    State: materials, currentMaterial, selectedSources (array)
    Actions: setMaterials, addMaterial, updateMaterial, removeMaterial,
             setCurrentMaterial, toggleSourceSelection, selectAllSources,
             deselectAllSources, isSourceSelected

  useNotebookStore.js:
    State: currentNotebook, draftMode
    Actions: setCurrentNotebook, setDraftMode, resetNotebook

  useUIStore.js:
    State: loading (map), activePanel
    Actions: setLoadingState, setActivePanel

  Keep useAppStore.js as a re-export barrel ONLY during migration:
    export { useChatStore, useMaterialStore, useNotebookStore, useUIStore }
  Update all components to import from the correct focused store.

FIX 4 — REQUEST CANCELLATION ON UNMOUNT
Add AbortSignal support to in `lib/api/generation.js`:
  generateFlashcards(notebookId, materialIds, count, language, signal)
  generateQuiz(notebookId, materialIds, count, difficulty, language, signal)
  generatePresentation(notebookId, materialIds, options, signal)
  generateMindMap(notebookId, materialIds, signal)
In each component that calls these, add useEffect cleanup:
  useEffect(() => {
    const controller = new AbortController()
    // pass controller.signal to API call
    return () => controller.abort()
  }, [deps])

FIX 5 — WEBSOCKET TIMER STACKING
In `useMaterialUpdates.js`:
  Store reconnect timer in: const reconnectTimerRef = useRef(null)
  Before setting new timer: clearTimeout(reconnectTimerRef.current)
  On unmount: clearTimeout(reconnectTimerRef.current) + ws.close()
  Use a mountedRef = useRef(true) guard — set false on unmount,
  check before any setState or reconnect attempt

FIX 6 — AUTH API THROUGH apiFetch
Rewrite `lib/api/auth.js`:
  login(), signup(), logout() → use apiFetch from config.js
  refreshToken() → keep using raw fetch() with credentials:'include'
  (refresh intentionally bypasses apiFetch to avoid circular retry loop)
  getCurrentUser() → use apiFetch

FIX 7 — CONSOLIDATE API_BASE
Remove inline `const API_BASE = process.env...` from:
  lib/api/podcast.js
  lib/api/agent.js
  components/viewer/FileViewerContent.jsx
All three must import `apiConfig.baseUrl` from `lib/api/config.js`

FIX 8 — NEXT.CONFIG IMAGE PATTERNS
Replace hardcoded localhost in remotePatterns:
  {
    protocol: process.env.NEXT_PUBLIC_API_PROTOCOL || 'http',
    hostname: process.env.NEXT_PUBLIC_API_HOST || 'localhost',
    port:     process.env.NEXT_PUBLIC_API_PORT || '8000',
  }
Add same pattern with https for production hostname.

FIX 9 — REACT STRICT MODE
Set `reactStrictMode: true` in next.config.mjs.
Fix all effects that break under StrictMode double-invoke:
  - WebSocket connections: use mountedRef guard, skip reconnect if unmounted
  - addEventListener calls: always paired with removeEventListener in cleanup
  - Any initialization that must run once: use ref guard `if (initializedRef.current) return`

FIX 10 — PAGE METADATA
Add to `app/auth/page.jsx`:
  export const metadata = { title: 'Sign In — KeplerLab', description: 'Login or create your KeplerLab account' }
Add to `app/notebook/[id]/layout.jsx`:
  export async function generateMetadata({ params }) {
    return { title: `Notebook — KeplerLab` }
  }

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 3 — PERFORMANCE FIXES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PERF 1 — REACT.MEMO ON ALL LIST ITEMS
Wrap with React.memo():
  ChatMessage, SourceItem, FeatureCard, notebook grid card
Add useCallback() to all handler props passed into these components.
Add useMemo() to derived values computed inside list-rendering parents.

PERF 2 — VIRTUALIZE LONG LISTS
Install react-window.
  ChatMessageList: use VariableSizeList (variable height messages)
    - Use a rowHeightCache ref to store measured heights
    - Implement getItemSize(index) from cache, default 80px
    - Auto-scroll to bottom on new message: listRef.current.scrollToItem(messages.length - 1)
  Sidebar material list: use FixedSizeList (itemSize=64)
  Notebook grid on dashboard: use react-window Grid for 20+ notebooks

PERF 3 — REMOVE useSearchParams FROM ChatPanel
  Move the single useSearchParams() usage to a tiny wrapper:
    function ChatPanelWithParams() {
      const params = useSearchParams()
      return <ChatPanel initialQuery={params.get('q')} />
    }
  ChatPanel itself never calls useSearchParams — no URL change re-renders

PERF 4 — REMOVE CHAKRA UI ENTIRELY
  Remove from package.json: @chakra-ui/react, @emotion/react, @emotion/styled, framer-motion
  Delete: src/lib/chakra/provider.jsx
  Remove ChakraProvider wrapper from src/app/providers.jsx
  Audit every import for any Chakra component — replace with Tailwind equivalent
  Remove manual FOUC script in layout.jsx (next-themes handles it)
  Run `next build` and confirm bundle reduction

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 4 — CHATPANEL REFACTOR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Break ChatPanel.jsx (1,212 lines, 30+ state vars) into focused components:

  ChatInputArea.jsx (new)
    Owns: text input, slash command dropdown, active command pill,
          mic button, send button, quick action buttons
    Props: onSend(message, intentOverride), disabled, isStreaming
    Shows active slash command as removable pill above input:
      [🤖 /agent ✕]  with command.description as tooltip
    Input placeholder changes to command.placeholder when active
    Pressing Escape or clicking ✕ clears active slash command

  ChatMessageList.jsx (new)
    Owns: virtualized message list (react-window VariableSizeList)
    Props: messages, onBlockFollowUp
    Renders correct component per message type (see Section 5)
    Handles auto-scroll-to-bottom on new messages
    Handles scroll-up-to-read without fighting auto-scroll

  useChatStream.js (new hook)
    Owns: all SSE event processing logic extracted from ChatPanel
    Handles all event types: token, agent_step, agent_start, agent_reflection,
                             artifact, research_phase, research_source,
                             citations, done
    Returns: { startStream, cancelStream, isStreaming }
    Uses AbortController internally, exposes cancelStream()

  ChatPanel.jsx (orchestrator only, target <200 lines)
    Composes: ChatInputArea + ChatMessageList + ArtifactPanel
    Reads from: useChatStore, useMaterialStore, useNotebookStore
    Calls: useChatStream hook
    No SSE parsing logic, no input state, no list rendering

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 5 — AGENTIC TASK UI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Redesign all agent-related UI components to match Claude/ChatGPT tool-use quality.

─── AgentThinkingBar.jsx ───
Replace simple "Thinking..." text with animated status pill:

  Layout:
    [tool-icon]  [tool name]  ·  [status]  ·  [elapsed time counter]  [pulsing dot]

  Tool icons (lucide-react):
    rag_search      → Search icon
    python_executor → Code2 icon
    web_search      → Globe icon
    file_generator  → FileDown icon
    flashcard_gen   → Layers icon
    quiz_gen        → HelpCircle icon
    mindmap_gen     → GitFork icon
    ppt_gen         → Presentation icon
    code_repair     → Wrench icon

  Elapsed time: live counter updating every 100ms using useInterval
  Pulse animation: CSS keyframes @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
  No Framer Motion (removed)

─── AgentActionBlock.jsx (redesign) ───
Render each completed agent step as a collapsible card:

  Card structure:
  ┌────────────────────────────────────────────────────────┐
  │ [icon] Step N: [description]              [duration] ▼ │
  │        Tool: [tool_name]  ·  [status badge]            │
  │ ─────────────────────────────────────────────────────  │
  │ [collapsible content — result_summary or output]       │
  └────────────────────────────────────────────────────────┘

  Status badge colors (Tailwind):
    running → bg-blue-500/20  text-blue-400  border-blue-500/30
    done    → bg-green-500/20 text-green-400 border-green-500/30
    failed  → bg-red-500/20   text-red-400   border-red-500/30

  If tool produced a chart artifact → show thumbnail (64x64) in collapsed view
  Click thumbnail → open ArtifactPanel to that artifact
  Failed steps → red left border, show error message in content area
  Collapse/expand: CSS max-height transition (no Framer Motion)
  All steps from one agent run are grouped under a single collapsible
  "Agent Run" parent block — expand to see individual steps

─── AgentReflectionChip.jsx (new) ───
When `agent_reflection` SSE event received, show a small chip between steps:
  Appearance: italic, muted text, small — not visually dominant
  Example: "✦ Goal achieved — composing response"
  Fades in with CSS opacity transition

─── ArtifactPanel.jsx (new) ───
Sliding right panel that appears when agent produces any artifact.
Triggered by `artifact` SSE event or clicking any artifact in chat.

  Layout:
  ┌──────────────────────────────┐
  │  Artifacts          [pin] [✕]│
  │  ──────────────────────────  │
  │  [Charts] [Files] [Tables]   │  ← tab bar
  │  ──────────────────────────  │
  │  [artifact content]          │
  └──────────────────────────────┘

  Behavior:
    - Slides in from right, overlays studio panel on mobile
    - Pin button keeps it open; unpinned closes after user interaction
    - Tab: Charts → full-width image with [Download PNG] button
    - Tab: Files  → list of files: [icon] filename  [size]  [↓ Download]
    - Tab: Tables → rendered <table> with sticky header + [Copy as CSV] button
    - Tab: Code   → syntax-highlighted code block with [Copy] button
    - Badge on tab label shows count: Charts (3)
    - If only one artifact type → skip tabs, show directly

  Inline in chat:
    Charts → render as img with rounded-lg, max-h-80, cursor-pointer → opens ArtifactPanel
    Files  → render as GeneratedFileCard (existing component, update download URL)
    Tables → render first 5 rows inline with "View all N rows →" link → opens ArtifactPanel

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 6 — DEEP RESEARCH UI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Replace ResearchProgress.jsx with a full ResearchReport.jsx component.

─── ResearchReport.jsx ───

PHASE PROGRESS BAR (top of component while streaming):

  ○──●──○──○──○
  Decomposing → Searching → Fetching → Synthesizing → Formatting

  Each phase node:
    - Pending:    hollow circle, muted text
    - Active:     filled circle with pulsing ring, white text, animated
    - Completed:  filled circle with checkmark, green tint

  Below phase bar: one-line status detail from `research_phase.detail` field

SOURCE CARDS PANEL (appears during Searching/Fetching phases):

  Renders as a horizontal scroll row below phase bar.
  Each card from `research_source` SSE event:
  ┌──────────────────────┐
  │ [rating badge]       │
  │ Title (truncated)    │
  │ domain.com           │
  │ relevance: 0.91      │
  └──────────────────────┘

  Rating badge colors:
    high   → green  bg-green-500/20  text-green-400
    medium → yellow bg-yellow-500/20 text-yellow-400
    low    → red    bg-red-500/20    text-red-400

  Cards animate in one by one as sources are found (CSS slide-in)
  Clicking a card opens the URL in a new tab

REPORT BODY (streams in during Synthesizing/Formatting):

  Render streaming markdown using existing MarkdownRenderer
  Sections appear progressively as tokens arrive
  Citation chips `[1]` render as:
    <span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs
                 bg-blue-500/20 text-blue-400 cursor-pointer font-mono">[1]</span>
  Hovering a citation chip shows a popover:
    - Source title
    - Domain with rating badge
    - Short snippet
    - "Open source →" link

EXPORT BUTTON (appears after `done` event):
  "Export Report" button → generates PDF via existing jspdf dependency
  PDF includes: report markdown rendered as text, bibliography table, accessed timestamps

SSE EVENT HANDLING in useChatStream.js:
  research_phase   → update phase progress bar state
  research_source  → append source card to sources array
  token            → stream into report body (same as regular chat)
  citations        → store citations array for chip interactivity
  done             → hide phase bar, show export button, finalize

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SECTION 7 — GENERAL UI POLISH & ACCESSIBILITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ACCESSIBILITY:
  - Audit ALL icon-only buttons across ChatPanel, Sidebar, StudioPanel, Header
    Add aria-label="descriptive action" to every one
  - SourceItem status badges: add title="Processing..." / "Ready" etc.
    alongside color — never color-only indicators
  - All modals (UploadDialog, ConfigDialogs, ChatHistoryModal, ConfirmDialog):
    Verify focus trap on open, Escape key closes, focus returns to trigger on close
  - SlashCommandDropdown: add role="listbox", aria-activedescendant, keyboard navigation

DEAD CODE REMOVAL:
  - Delete `components/auth/` empty directory
  - Delete `QUICK_ACTIONS` and `API_FALLBACK_URL` from `lib/utils/constants.js`
  - Delete `getExplainerStatus` export from `lib/api/explainer.js`
  - Delete `parseSlashCommand` from `lib/utils/helpers.js`
    (canonical version is in slashCommands.js — update all imports)
  - Remove Chakra token definitions from lib/chakra/ after Chakra removal (Section 3 PERF 4)

CODE QUALITY:
  - useResizablePanel hook exists in hooks/ but Sidebar reimplements resize manually
    Refactor Sidebar to use useResizablePanel hook
  - Error display: standardize on toast.error() everywhere
    Remove local error state patterns that show errors inline inconsistently
  - All ConfigDialogs.jsx named exports: convert `export default {}` object
    pattern to individual named exports for tree-shaking
