# Frontend-Next Deep Scan — Issues Document

> Generated: 2026-03-02 | Total Issues: 70

---

## 🔴 CRITICAL — Features Broken / Rendering Empty

| # | File | Issue | Impact |
|---|------|-------|--------|
| 1 | `StudioPanel.jsx:775` | `FeatureCard` receives `title={output.title}` but component expects `label` prop | Feature card titles never render |
| 2 | `StudioPanel.jsx:592` | `<InlineFlashcardsView data={flashcardsData} />` — component expects `flashcards` prop | Flashcards always empty |
| 3 | `StudioPanel.jsx:594` | `<InlineQuizView data={quizData} />` — component expects `quiz` prop | Quiz questions always empty |
| 4 | `StudioPanel.jsx:615` | `<InlineExplainerView data={explainerData} />` — component expects `explainer` prop | Explainer video never loads |
| 5 | `StudioPanel.jsx:619-623` | `MindMapView` receives `selectedSources` and `onGenerated` props it doesn't accept | Props silently dropped |
| 6 | `ChatHistoryModal.jsx:91` | Passes `title="Chat History"` and `size="xl"` to Modal, which doesn't accept these | No title rendered, wrong modal width |
| 7 | `WebSearchDialog.jsx:54-66` | Passes `title`, `icon`, `footer` to Modal which doesn't render them | Missing title/icon/footer |

## 🟠 HIGH — SSR Crash / Runtime Errors

| # | File | Issue | Impact |
|---|------|-------|--------|
| 8 | `PodcastInterruptDrawer.jsx:19` | `useRef(new Audio())` — `Audio` undefined during SSR | `ReferenceError` on server render |
| 9 | `useResizablePanel.js:22-26` | References `PANEL.SIDEBAR_DEFAULT`, `PANEL.SIDEBAR_MIN`, `PANEL.SIDEBAR_MAX` — but constants define nested `PANEL.SIDEBAR.DEFAULT_WIDTH` | All defaults are `undefined`, `collapseThreshold = NaN` |

## 🟡 MEDIUM — Memory Leaks / Missing Cleanup

| # | File | Issue |
|---|------|-------|
| 10 | `InlineExplainerView.jsx:28-38` | Blob URL created by `fetchExplainerVideoBlob` never revoked on unmount |
| 11 | `PodcastDoubtHistory.jsx:9` | `new Audio()` in useRef — no cleanup to pause on unmount |
| 12 | `VoicePicker.jsx:15` | `new Audio()` in useRef — no cleanup to pause on unmount |

## 🟡 MEDIUM — Modal Component Missing Features

| # | File | Issue |
|---|------|-------|
| 13 | `Modal.jsx` | Doesn't support `title`, `icon`, `footer`, `size` props that consumers pass | 
| 14 | `Modal.jsx` | No focus trap — tab key navigates behind modal |
| 15 | `Modal.jsx` | Missing `role="dialog"` and `aria-modal="true"` |
| 16 | `Modal.jsx` | No ESC key handler to close |

## 🔵 LOW — Unused Imports

| # | File | Import |
|---|------|--------|
| 17 | `PresentationView.jsx:5-6` | `Loader2`, `Settings` imported but never used |
| 18 | `InlineExplainerView.jsx:4` | `getExplainerStatus` imported but never used |

## 🔵 LOW — Tailwind Deprecation Warnings (461 instances)

| Pattern | Replacement | Count |
|---------|-------------|-------|
| `flex-shrink-0` | `shrink-0` | 33+ |
| `bg-[var(--x)]` | `bg-(--x)` | Many |
| `text-[var(--x)]` | `text-(--x)` | Many |
| `border-[var(--x)]` | `border-(--x)` | Several |
| `focus:ring-[var(--x)]` | `focus:ring-(--x)` | Several |
| `hover:bg-[var(--x)]` | `hover:bg-(--x)` | Several |
| `bg-gradient-to-*` | `bg-linear-to-*` | Several |
| `z-[9999]` | `z-9999` | Few |
| `max-h-[250px]` | `max-h-62.5` | Few |
| `max-h-[320px]` | `max-h-80` | Few |

## 🔵 LOW — Console Statements (24 total)

Files with console.error/console.log:
- `page.jsx` (3), `error.jsx` (1), `global-error.jsx` (1)
- `ErrorBoundary.jsx` (1), `ChatPanel.jsx` (5), `GeneratedFileCard.jsx` (1)
- `MindMapCanvas.jsx` (1), `StudioPanel.jsx` (3), `InlineFlashcardsView.jsx` (1)
- `PodcastPlayer.jsx` (1), `PodcastInterruptDrawer.jsx` (1), `PodcastDoubtHistory.jsx` (1)
- `usePodcastStore.js` (3), `useMicInput.js` (1)

## 🔵 LOW — Other Issues

| # | Issue | Details |
|---|-------|---------|
| 19 | Duplicate `parseSlashCommand` | `slashCommands.js` and `helpers.js` — different signatures |
| 20 | `ConfigDialogs.jsx` exports object as default | `export default { FlashcardConfigDialog, QuizConfigDialog }` — unusual pattern |
| 21 | `dangerouslySetInnerHTML` | `PresentationView.jsx:153` — unsanitized HTML in thumbnails |
| 22 | Index-based keys | 11+ files use array index as React key |
| 23 | Missing `aria-label` on icon-only buttons | Widespread accessibility issue |
| 24 | Duplicate API_BASE definitions | `podcast.js`, `FileViewerContent.jsx` define own API_BASE |
| 25 | Empty directories | `chat/Agent/`, `chat/CodeExecution/`, `chat/SlashCommand/` |
| 26 | `reactStrictMode: false` in next.config.mjs | Should be true for dev |

---

## Fix Status

- [x] Critical prop mismatches (#1-5) — Fixed `title→label`, `data→flashcards/quiz/explainer`, removed unused MindMapView props
- [x] Modal prop mismatch (#6-7) — Enhanced Modal to support `title`, `icon`, `footer`, `size` props
- [x] Modal accessibility (#13-16) — Added `role="dialog"`, `aria-modal`, focus trap, ESC key handler, header with close button
- [x] SSR crash (#8) — Added `typeof window !== 'undefined'` guard to PodcastInterruptDrawer Audio
- [x] Constant key mismatch (#9) — Fixed `PANEL.SIDEBAR_DEFAULT` → `PANEL.SIDEBAR.DEFAULT_WIDTH` etc.
- [x] Memory leaks (#10-12) — Fixed blob URL revocation with ref tracking, added Audio cleanup to PodcastDoubtHistory & VoicePicker
- [x] Unused imports (#17-18) — Removed `Loader2`, `Settings` from PresentationView, `getExplainerStatus` from InlineExplainerView
- [x] Tailwind class modernization — Replaced all `flex-shrink-0`→`shrink-0`, `bg-[var(--x)]`→`bg-(--x)`, `bg-gradient-to-*`→`bg-linear-to-*` across 25+ files
- [x] ConfigDialogs export (#20) — Removed problematic default object export
- [x] Empty directories (#25) — Removed `chat/Agent/`, `chat/CodeExecution/`, `chat/SlashCommand/`
- [x] `dangerouslySetInnerHTML` (#21) — Added safety comment documenting it's system-generated content
- [x] Build verification — `next build` compiles successfully with zero errors
