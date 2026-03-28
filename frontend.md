# KeplerLab Frontend Architecture - Complete Documentation

## Table of Contents
1. [Overview](#overview)
2. [Technology Stack](#technology-stack)
3. [Directory Structure](#directory-structure)
4. [Application Entry Points](#application-entry-points)
5. [State Management](#state-management)
6. [API Client Architecture](#api-client-architecture)
7. [Custom Hooks](#custom-hooks)
8. [Component Architecture](#component-architecture)
9. [Routing Structure](#routing-structure)
10. [Authentication Flow](#authentication-flow)
11. [Styling System](#styling-system)
12. [WebSocket Integration](#websocket-integration)
13. [Feature Modules](#feature-modules)
14. [Performance Optimizations](#performance-optimizations)
15. [Error Handling](#error-handling)
16. [Build Configuration](#build-configuration)

---

## Overview

KeplerLab Frontend is a Next.js 16 application with App Router, providing a modern AI-powered learning platform interface. The application features:

- **Dashboard**: Notebook management with thumbnails and quick actions
- **AI Chat**: Context-aware chat with streaming responses
- **Studio Panel**: Content generation (flashcards, quizzes, presentations, podcasts)
- **Material Management**: Upload and organize learning resources
- **Podcast Studio**: Generate and play AI podcasts
- **Presentation Viewer**: Interactive slide presentations
- **Mind Map Canvas**: Visual knowledge graphs

---

## Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| **Framework** | Next.js | 16.1.6 |
| **React** | React | 19.2.3 |
| **State Management** | Zustand | 5.0.11 |
| **Styling** | Tailwind CSS | 3.4.17 |
| **Markdown Rendering** | react-markdown | 10.1.0 |
| **Code Highlighting** | react-syntax-highlighter | 16.1.1 |
| **Flow Diagrams** | @xyflow/react | 12.10.1 |
| **PDF Generation** | jspdf | 4.2.0 |
| **Icons** | lucide-react | 0.576.0 |
| **Theme Management** | next-themes | 0.4.6 |
| **Math Rendering** | KaTeX | 0.16.33 |
| **Document Viewer** | @cyntler/react-doc-viewer | 1.17.1 |

---

## Directory Structure

```
frontend/
├── src/
│   ├── app/                          # Next.js App Router
│   │   ├── layout.jsx                # Root layout with providers
│   │   ├── page.jsx                  # Home page (Dashboard/Landing)
│   │   ├── providers.jsx             # Theme and auth providers
│   │   ├── loading.jsx               # Loading state
│   │   ├── error.jsx                 # Error boundary
│   │   ├── not-found.jsx             # 404 page
│   │   ├── global-error.jsx          # Global error handler
│   │   ├── auth/
│   │   │   ├── layout.jsx            # Auth layout
│   │   │   └── page.jsx              # Login/Signup page
│   │   ├── notebook/
│   │   │   └── [id]/
│   │   │       ├── layout.jsx        # Notebook layout
│   │   │       └── page.jsx          # Notebook workspace
│   │   └── view/
│   │       └── page.jsx              # File viewer
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Header.jsx            # Workspace header
│   │   │   └── Sidebar.jsx           # Source management sidebar
│   │   ├── chat/
│   │   │   ├── ChatPanel.jsx         # Main chat container
│   │   │   ├── ChatInput.jsx         # Message input with suggestions
│   │   │   ├── MessageList.jsx       # Message display list
│   │   │   ├── MessageItem.jsx       # Individual message
│   │   │   ├── MarkdownRenderer.jsx  # Markdown with syntax highlighting
│   │   │   ├── CodePanel.jsx         # Code execution panel
│   │   │   ├── ArtifactViewer.jsx    # Artifact display
│   │   │   ├── WebSources.jsx        # Web source citations
│   │   │   ├── AgentProgressPanel.jsx # Agent execution progress
│   │   │   └── ...                   # More chat components
│   │   ├── studio/
│   │   │   ├── StudioPanel.jsx       # Studio panel container
│   │   │   ├── FeatureCard.jsx       # Feature selection cards
│   │   │   ├── InlineFlashcardsView.jsx
│   │   │   ├── InlineQuizView.jsx
│   │   │   ├── InlineExplainerView.jsx
│   │   │   ├── ContentHistory.jsx    # Generated content history
│   │   │   └── ConfigDialogs.jsx     # Configuration modals
│   │   ├── podcast/
│   │   │   ├── PodcastStudio.jsx     # Podcast creation
│   │   │   ├── PodcastPlayer.jsx     # Audio player
│   │   │   ├── PodcastMiniPlayer.jsx # Mini player bar
│   │   │   ├── PodcastGenerating.jsx # Generation progress
│   │   │   ├── PodcastTranscript.jsx # Transcript display
│   │   │   ├── PodcastInterruptDrawer.jsx # Q&A drawer
│   │   │   ├── VoicePicker.jsx      # Voice selection
│   │   │   └── ...                   # More podcast components
│   │   ├── presentation/
│   │   │   ├── PresentationView.jsx  # Main presentation viewer
│   │   │   ├── PresentationEditor.jsx # Slide editor
│   │   │   ├── PresentationDialog.jsx # Creation dialog
│   │   │   ├── SlideCanvas.jsx       # Slide rendering
│   │   │   ├── SlideList.jsx         # Slide thumbnails
│   │   │   └── PresentationView.css  # Presentation styles
│   │   ├── mindmap/
│   │   │   ├── MindMapCanvas.jsx     # Mind map rendering
│   │   │   └── MindMapEdge.jsx       # Custom edge component
│   │   ├── notebook/
│   │   │   ├── UploadDialog.jsx      # File upload modal
│   │   │   ├── WebSearchDialog.jsx   # Web search modal
│   │   │   └── SourceItem.jsx        # Material list item
│   │   ├── viewer/
│   │   │   ├── FileViewerContent.jsx # File viewer
│   │   │   └── DocViewerRenderer.jsx # Document renderer
│   │   ├── ui/
│   │   │   ├── Modal.jsx             # Base modal component
│   │   │   ├── ToastContainer.jsx    # Toast notifications
│   │   │   ├── ConfirmDialog.jsx     # Confirmation dialogs
│   │   │   ├── ErrorBoundary.jsx     # Error boundaries
│   │   │   ├── Portal.jsx            # Portal for modals
│   │   │   └── SkeletonLoader.jsx    # Loading skeletons
│   │   ├── Dashboard.jsx             # Main dashboard
│   │   └── LandingPage.jsx           # Landing page
│   ├── stores/
│   │   ├── useAuthStore.js           # Authentication state
│   │   ├── useAppStore.js            # Global app state
│   │   ├── useNotebookStore.js       # Notebook state
│   │   ├── useMaterialStore.js       # Materials state
│   │   ├── useChatStore.js           # Chat messages state
│   │   ├── usePodcastStore.js        # Podcast state
│   │   ├── useMindMapStore.js        # Mind map state
│   │   ├── useUIStore.js             # UI state
│   │   ├── useToastStore.js          # Toast notifications
│   │   └── useConfirmStore.js        # Confirmation dialogs
│   ├── hooks/
│   │   ├── useChat.js                # Chat functionality
│   │   ├── usePodcastPlayer.js       # Podcast audio control
│   │   ├── useMaterialUpdates.js     # Material status updates
│   │   ├── useMicInput.js            # Microphone input
│   │   ├── useResizablePanel.js      # Panel resizing
│   │   └── useAutoScroll.js          # Auto-scroll behavior
│   ├── lib/
│   │   ├── api/
│   │   │   ├── config.js             # API configuration
│   │   │   ├── auth.js               # Auth API calls
│   │   │   ├── notebooks.js          # Notebook API
│   │   │   ├── materials.js          # Materials API
│   │   │   ├── chat.js               # Chat API
│   │   │   ├── podcast.js            # Podcast API
│   │   │   ├── presentation.js       # Presentation API
│   │   │   ├── generation.js         # Content generation
│   │   │   ├── explainer.js          # Explainer API
│   │   │   ├── mindmap.js            # Mind map API
│   │   │   ├── agent.js              # Agent API
│   │   │   └── aiResource.js         # AI resource builder
│   │   ├── stream/
│   │   │   └── streamClient.js       # SSE stream handling
│   │   ├── config/
│   │   │   └── slashCommands.js      # Slash command definitions
│   │   └── utils/
│   │       ├── constants.js          # Constants
│   │       ├── helpers.js            # Utility functions
│   │       └── parseSlashCommand.js  # Command parser
│   ├── styles/
│   │   └── globals.css               # Global styles and CSS variables
│   └── middleware.js                 # Next.js middleware
├── tailwind.config.js                # Tailwind configuration
├── jsconfig.json                     # JavaScript configuration
└── package.json                      # Dependencies
```

---

## Application Entry Points

### Root Layout (`src/app/layout.jsx`)

```jsx
import { Inter, JetBrains_Mono, Plus_Jakarta_Sans } from 'next/font/google';
import Providers from './providers';
import '@/styles/globals.css';

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' });
const jetbrainsMono = JetBrains_Mono({ subsets: ['latin'], variable: '--font-jetbrains' });
const plusJakartaSans = Plus_Jakarta_Sans({ subsets: ['latin'], variable: '--font-headline' });

export const metadata = {
  title: 'KeplerLab — AI Learning Platform',
  description: 'AI-powered learning platform',
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link href="Material+Symbols+Outlined" rel="stylesheet" />
      </head>
      <body className={`${inter.variable} ${jetbrainsMono.variable} ${plusJakartaSans.variable}`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

### Providers (`src/app/providers.jsx`)

```jsx
'use client';

import { useEffect } from 'react';
import { ThemeProvider } from 'next-themes';
import useAuthStore from '@/stores/useAuthStore';
import ToastContainer from '@/components/ui/ToastContainer';
import ConfirmDialog from '@/components/ui/ConfirmDialog';

function AuthInitializer({ children }) {
  const initAuth = useAuthStore((s) => s.initAuth);
  
  useEffect(() => {
    initAuth();  // Initialize auth on app load
  }, [initAuth]);
  
  return children;
}

export default function Providers({ children }) {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="system"
      enableSystem
      storageKey="kepler-theme"
    >
      <AuthInitializer>
        {children}
        <ToastContainer />
        <ConfirmDialog />
      </AuthInitializer>
    </ThemeProvider>
  );
}
```

### Home Page (`src/app/page.jsx`)

```jsx
'use client';

import useAuthStore from '@/stores/useAuthStore';
import Dashboard from '@/components/Dashboard';
import LandingPage from '@/components/LandingPage';

export default function RootPage() {
  const { isAuthenticated, isLoading } = useAuthStore();
  
  if (isLoading) {
    return <LoadingSpinner />;
  }
  
  if (!isAuthenticated) {
    return <LandingPage />;
  }
  
  return <Dashboard />;
}
```

---

## State Management

### Zustand Stores Overview

| Store | Purpose | Key State |
|-------|---------|-----------|
| `useAuthStore` | Authentication | user, isAuthenticated, isLoading |
| `useAppStore` | Global state | currentNotebook, materials, messages |
| `useNotebookStore` | Notebook state | currentNotebook, draftMode |
| `useMaterialStore` | Materials | materials, selectedSources |
| `useChatStore` | Chat messages | messages, sessionId, isStreaming |
| `usePodcastStore` | Podcast | session, segments, isPlaying |
| `useMindMapStore` | Mind map | activeMindMapData, expandedNodeIds |
| `useUIStore` | UI state | activePanel, loading |
| `useToastStore` | Notifications | toasts |
| `useConfirmStore` | Dialogs | confirmState |

### useAuthStore

```javascript
const useAuthStore = create((set, get) => ({
  user: null,
  isLoading: true,
  isAuthenticated: false,
  error: null,
  
  // Internal refs
  _accessTokenRef: null,
  _refreshTimer: null,
  
  // Token sync
  _syncToken: (token) => {
    _accessTokenRef = token;
    syncTokenToApi(token);
  },
  
  // Token refresh scheduling
  scheduleRefresh: () => {
    if (_refreshTimer) clearTimeout(_refreshTimer);
    _refreshTimer = setTimeout(async () => {
      // Retry logic with exponential backoff
      for (let attempt = 0; attempt < 3; attempt++) {
        try {
          const tokens = await refreshToken();
          get()._syncToken(tokens.access_token);
          get().scheduleRefresh();
          return;
        } catch {
          await sleep(2000 * 2 ** attempt);
        }
      }
      // Refresh failed - logout
      set({ user: null, isAuthenticated: false });
      window.location.href = '/auth?reason=expired';
    }, TOKEN_REFRESH_INTERVAL);
  },
  
  // Auth initialization
  initAuth: async () => {
    try {
      const tokens = await refreshToken();
      get()._syncToken(tokens.access_token);
      const userData = await getCurrentUser(tokens.access_token);
      set({ user: userData, isAuthenticated: true });
      get().scheduleRefresh();
    } catch {
      set({ user: null, isAuthenticated: false });
    } finally {
      set({ isLoading: false });
    }
  },
  
  // Login
  login: async (email, password) => {
    const tokens = await apiLogin(email, password);
    get()._syncToken(tokens.access_token);
    const userData = await getCurrentUser(tokens.access_token);
    set({ user: userData, isAuthenticated: true });
    get().scheduleRefresh();
  },
  
  // Logout
  logout: async () => {
    await apiLogout(_accessTokenRef);
    clearTimeout(_refreshTimer);
    set({ user: null, isAuthenticated: false });
    get()._syncToken(null);
  },
}));
```

### useAppStore

```javascript
const useAppStore = create((set, get) => ({
  // Notebook state
  currentNotebook: null,
  draftMode: false,
  newlyCreatedNotebookId: null,
  
  // Material state
  materials: [],
  selectedSources: [],
  currentMaterial: null,
  
  // Chat state
  sessionId: null,
  messages: [],
  
  // Generated content
  flashcards: null,
  quiz: null,
  presentation: null,
  notes: [],
  
  // UI state
  pendingChatMessage: null,
  chatInputValue: '',
  loading: {},
  error: null,
  activePanel: 'chat',
  
  // Actions
  setCurrentNotebook: (notebook) => set({ currentNotebook: notebook }),
  setMaterials: (materials) => set({ materials }),
  addMaterial: (material) => set((s) => ({ 
    materials: [...s.materials, material] 
  })),
  toggleSourceSelection: (id) => set((s) => ({
    selectedSources: s.selectedSources.includes(id)
      ? s.selectedSources.filter((sid) => sid !== id)
      : [...s.selectedSources, id]
  })),
  resetForNotebookSwitch: () => set({
    selectedSources: [],
    materials: [],
    messages: [],
    sessionId: null,
    flashcards: null,
    quiz: null,
    presentation: null,
  }),
  // ... more actions
}));
```

### useChatStore

```javascript
const useChatStore = create((set, get) => ({
  messages: [],
  sessionId: null,
  isStreaming: false,
  error: null,
  
  addMessage: (message) => set((s) => ({ 
    messages: [...s.messages, message] 
  })),
  
  updateLastMessage: (updater) => set((s) => {
    if (s.messages.length === 0) return s;
    const updated = [...s.messages];
    const last = updated[updated.length - 1];
    updated[updated.length - 1] = 
      typeof updater === 'function' ? updater(last) : { ...last, ...updater };
    return { messages: updated };
  }),
  
  setStreaming: (isStreaming) => set({ isStreaming }),
  clearMessages: () => set({ messages: [], sessionId: null }),
  setSessionId: (id) => set({ sessionId: id }),
}));
```

### usePodcastStore

```javascript
const usePodcastStore = create((set, get) => ({
  session: null,
  sessions: [],
  segments: [],
  chapters: [],
  doubts: [],
  bookmarks: [],
  annotations: [],
  
  currentSegmentIndex: 0,
  isPlaying: false,
  playbackSpeed: 1,
  currentTime: 0,
  
  phase: 'idle',  // 'idle', 'generating', 'player'
  generationProgress: null,
  error: null,
  loading: false,
  
  // Audio refs
  _audioElRef: { current: null },
  _audioCacheRef: { current: new Map() },
  
  // Actions
  loadSession: async (sessionId) => {
    const data = await getPodcastSession(sessionId);
    const phase = ['ready', 'playing', 'paused'].includes(data.status) 
      ? 'player' 
      : 'generating';
    set({ session: data, segments: data.segments, phase });
  },
  
  playSegment: async (index) => {
    const seg = get().segments[index];
    let blobUrl = get()._audioCacheRef.current.get(seg.audioPath);
    if (!blobUrl) {
      blobUrl = await fetchAudioObjectUrl(seg.audioPath);
      get()._audioCacheRef.current.set(seg.audioPath, blobUrl);
    }
    get()._audioElRef.current.src = blobUrl;
    await get()._audioElRef.current.play();
    set({ isPlaying: true, currentSegmentIndex: index });
  },
  
  togglePlayPause: () => {
    if (get().isPlaying) get().pause();
    else get().resume();
  },
  
  // WebSocket event handler
  handleWsEvent: (event) => {
    switch (event.type) {
      case 'podcast_progress':
        set({ generationProgress: { stage: event.phase, pct: event.progress * 100 } });
        break;
      case 'podcast_ready':
        get().loadSession(event.session_id);
        break;
      case 'podcast_segment_ready':
        set((s) => ({ segments: [...s.segments, event.segment].sort((a, b) => a.index - b.index) }));
        break;
    }
  },
}));
```

---

## API Client Architecture

### Configuration (`src/lib/api/config.js`)

```javascript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

let _accessToken = null;
let _refreshPromise = null;

export function setAccessToken(token) {
  _accessToken = token;
}

export function getAccessToken() {
  return _accessToken;
}

function getAuthHeaders() {
  return _accessToken ? { Authorization: `Bearer ${_accessToken}` } : {};
}

// Automatic token refresh on 401
async function _refreshTokenOnce() {
  if (!_refreshPromise) {
    _refreshPromise = fetch(`${API_BASE_URL}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    }).then(r => r.json()).then(tokens => {
      _accessToken = tokens.access_token;
      return tokens.access_token;
    }).finally(() => {
      _refreshPromise = null;
    });
  }
  return _refreshPromise;
}

// Main API fetch function
export async function apiFetch(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const config = {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...options.headers,
    },
  };
  
  let response = await fetch(url, config);
  
  // Auto-refresh on 401
  if (response.status === 401) {
    const newToken = await _refreshTokenOnce();
    config.headers.Authorization = `Bearer ${newToken}`;
    response = await fetch(url, config);
  }
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  
  return response;
}

export async function apiJson(endpoint, options = {}) {
  const response = await apiFetch(endpoint, options);
  if (response.status === 204) return null;
  return response.json();
}
```

### Auth API (`src/lib/api/auth.js`)

```javascript
export async function login(email, password) {
  return apiJson('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export async function signup(email, username, password) {
  return apiJson('/auth/signup', {
    method: 'POST',
    body: JSON.stringify({ email, username, password }),
  });
}

export async function refreshToken() {
  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: 'POST',
    credentials: 'include',
  });
  return response.json();
}

export async function getCurrentUser() {
  return apiJson('/auth/me');
}
```

### Chat API (`src/lib/api/chat.js`)

```javascript
export async function streamChat(materialId, message, notebookId, materialIds, sessionId, signal, intentOverride) {
  const body = {
    message,
    notebook_id: notebookId,
    stream: true,
    session_id: sessionId,
  };
  if (materialIds?.length > 0) body.material_ids = materialIds;
  if (intentOverride) body.intent_override = intentOverride;
  
  return apiFetch('/chat', {
    method: 'POST',
    body: JSON.stringify(body),
    signal,
  });
}

export async function getChatHistory(notebookId, sessionId) {
  return apiJson(`/chat/history/${notebookId}?session_id=${sessionId}`);
}

export async function getSuggestions(partialInput, notebookId) {
  return apiJson('/chat/suggestions', {
    method: 'POST',
    body: JSON.stringify({ partial_input: partialInput, notebook_id: notebookId }),
  });
}
```

### Materials API (`src/lib/api/materials.js`)

```javascript
export async function uploadMaterial(file, notebookId) {
  const formData = new FormData();
  formData.append('file', file);
  if (notebookId) formData.append('notebook_id', notebookId);
  
  const response = await apiFetchFormData('/upload', formData);
  return response.json();
}

export async function uploadBatch(files, notebookId) {
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  if (notebookId) formData.append('notebook_id', notebookId);
  
  const response = await apiFetchFormData('/upload/batch', formData);
  return response.json();
}

export async function uploadUrl(url, notebookId, autoCreateNotebook) {
  return apiJson('/upload/url', {
    method: 'POST',
    body: JSON.stringify({ url, notebook_id: notebookId, auto_create_notebook: autoCreateNotebook }),
  });
}

export async function getMaterials(notebookId) {
  return apiJson(`/materials?notebook_id=${notebookId}`);
}

export async function deleteMaterial(materialId) {
  return apiJson(`/materials/${materialId}`, { method: 'DELETE' });
}
```

### Podcast API (`src/lib/api/podcast.js`)

```javascript
export async function createPodcastSession(data) {
  return apiJson('/podcast/session', { method: 'POST', body: JSON.stringify(data) });
}

export async function startPodcastGeneration(sessionId) {
  return apiJson(`/podcast/session/${sessionId}/start`, { method: 'POST' });
}

export async function submitPodcastQuestion(sessionId, data) {
  return apiJson(`/podcast/session/${sessionId}/question`, {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getVoicesForLanguage(language) {
  return apiJson(`/podcast/voices?language=${language}`);
}
```

---

## Custom Hooks

### useChat (`src/hooks/useChat.js`)

```javascript
export default function useChat({ notebookId, materialIds }) {
  const messages = useChatStore((s) => s.messages);
  const sessionId = useChatStore((s) => s.sessionId);
  const isStreaming = useChatStore((s) => s.isStreaming);
  
  const abortControllerRef = useRef(null);
  
  const sendMessage = useCallback(async (content, nbId, intentOverride) => {
    abortControllerRef.current = new AbortController();
    useChatStore.getState().setStreaming(true);
    useChatStore.getState().addMessage({ id: generateId(), role: 'user', content });
    
    try {
      const response = await streamChat(
        null, content, nbId || notebookId, materialIds, sessionId,
        abortControllerRef.current.signal, intentOverride
      );
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      
      // Add placeholder assistant message
      const assistantId = generateId();
      useChatStore.getState().addMessage({ id: assistantId, role: 'assistant', content: '' });
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));
            if (data.token) {
              useChatStore.getState().updateLastMessage((msg) => ({
                ...msg,
                content: msg.content + data.token,
              }));
            }
            if (data.meta) {
              useChatStore.getState().updateLastMessage({ agentMeta: data.meta });
            }
          }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        useChatStore.getState().setError(err.message);
      }
    } finally {
      useChatStore.getState().setStreaming(false);
    }
  }, [notebookId, materialIds, sessionId]);
  
  const abort = useCallback(() => {
    abortControllerRef.current?.abort();
  }, []);
  
  return { messages, sessionId, isStreaming, sendMessage, abort };
}
```

### usePodcastPlayer (`src/hooks/usePodcastPlayer.js`)

```javascript
export default function usePodcastPlayer() {
  const audioRef = useRef(null);
  const cacheRef = useRef(new Map());
  
  useEffect(() => {
    usePodcastStore.getState().setAudioRefs(audioRef, cacheRef);
  }, []);
  
  return {
    audioRef,
    currentTime: usePodcastStore((s) => s.currentTime),
    isPlaying: usePodcastStore((s) => s.isPlaying),
    playbackSpeed: usePodcastStore((s) => s.playbackSpeed),
    
    play: () => usePodcastStore.getState().resume(),
    pause: () => usePodcastStore.getState().pause(),
    seek: (segmentIndex) => usePodcastStore.getState().playSegment(segmentIndex),
    setSpeed: (speed) => usePodcastStore.getState().changeSpeed(speed),
  };
}
```

### useMaterialUpdates (`src/hooks/useMaterialUpdates.js`)

```javascript
export default function useMaterialUpdates(notebookId) {
  useEffect(() => {
    if (!notebookId) return;
    
    const ws = new WebSocket(`${WS_BASE_URL}/ws/jobs/${userId}`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'material_status') {
        useMaterialStore.getState().updateMaterial(data.material_id, {
          status: data.status,
          chunk_count: data.chunk_count,
        });
      }
    };
    
    return () => ws.close();
  }, [notebookId]);
}
```

---

## Component Architecture

### ChatPanel Component

```jsx
export default function ChatPanel({ currentSessionId, setCurrentSessionId }) {
  const currentNotebook = useAppStore((s) => s.currentNotebook);
  const selectedSources = useAppStore((s) => s.selectedSources);
  const materials = useAppStore((s) => s.materials);
  
  const effectiveIds = useMemo(() => 
    selectedSources.filter(id => {
      const mat = materials.find(m => m.id === id);
      return mat?.status === 'completed';
    }),
    [selectedSources, materials]
  );
  
  const { messages, isStreaming, sendMessage, abort } = useChat({
    notebookId: currentNotebook?.id,
    materialIds: effectiveIds,
  });
  
  const handleSend = async (content, intentOverride) => {
    if (!currentNotebook?.id) {
      // Create new notebook if needed
      const newNb = await createNotebook(content.slice(0, 30), 'Created from chat');
      router.replace(`/notebook/${newNb.id}`);
    }
    await sendMessage(content, currentNotebook?.id, intentOverride);
  };
  
  return (
    <main className="workspace-chat-shell">
      <ChatHistorySidebar
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelectSession={setCurrentSessionId}
      />
      
      <div className="workspace-chat-column">
        {messages.length === 0 ? (
          <EmptyState onSend={handleSend} />
        ) : (
          <MessageList messages={messages} isStreaming={isStreaming} />
        )}
        
        <ChatInput
          onSend={handleSend}
          onStop={abort}
          isStreaming={isStreaming}
          materialIds={effectiveIds}
        />
      </div>
    </main>
  );
}
```

### StudioPanel Component

```jsx
export default function StudioPanel() {
  const [activeFeature, setActiveFeature] = useState(null);
  const selectedSources = useAppStore((s) => s.selectedSources);
  
  const features = [
    { id: 'flashcards', icon: Layers, label: 'Flashcards' },
    { id: 'quiz', icon: HelpCircle, label: 'Quiz' },
    { id: 'presentation', icon: Presentation, label: 'Presentation' },
    { id: 'podcast', icon: Mic, label: 'Podcast' },
    { id: 'mindmap', icon: GitBranch, label: 'Mind Map' },
  ];
  
  return (
    <aside className="studio-panel">
      <div className="studio-features-grid">
        {features.map(feature => (
          <FeatureCard
            key={feature.id}
            feature={feature}
            onClick={() => setActiveFeature(feature.id)}
            disabled={selectedSources.length === 0}
          />
        ))}
      </div>
      
      {activeFeature === 'flashcards' && <InlineFlashcardsView />}
      {activeFeature === 'quiz' && <InlineQuizView />}
      {activeFeature === 'presentation' && <PresentationDialog />}
      {activeFeature === 'podcast' && <PodcastStudio />}
      {activeFeature === 'mindmap' && <MindMapCanvas />}
    </aside>
  );
}
```

---

## Routing Structure

### App Router Routes

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | `RootPage` | Dashboard or Landing based on auth |
| `/auth` | `AuthPage` | Login/Signup |
| `/notebook/[id]` | `NotebookPage` | Workspace (id can be UUID or 'draft') |
| `/view` | `ViewPage` | Standalone file viewer |

### Route Guards

```javascript
// middleware.js
export function middleware(request) {
  const token = request.cookies.get('refresh_token');
  const { pathname } = request.nextUrl;
  
  // Protected routes
  if (pathname.startsWith('/notebook') && !token) {
    return NextResponse.redirect(new URL('/auth', request.url));
  }
  
  // Auth page redirect if authenticated
  if (pathname === '/auth' && token) {
    return NextResponse.redirect(new URL('/', request.url));
  }
  
  return NextResponse.next();
}
```

---

## Authentication Flow

### Login Flow

```
1. User enters credentials
      ↓
2. POST /auth/login
      ↓
3. Server validates credentials
      ↓
4. Server sets refresh_token cookie (HTTP-only)
      ↓
5. Server returns access_token in response
      ↓
6. Frontend stores access_token in memory (not localStorage)
      ↓
7. Fetch user profile with access_token
      ↓
8. Set isAuthenticated = true
      ↓
9. Schedule automatic token refresh
```

### Token Refresh Flow

```
1. Before access token expires (15 min)
      ↓
2. Frontend calls POST /auth/refresh
      ↓
3. Server validates refresh_token cookie
      ↓
4. Server issues new access_token
      ↓
5. Server rotates refresh_token (old marked used)
      ↓
6. Frontend updates in-memory access_token
      ↓
7. Schedule next refresh
```

### Logout Flow

```
1. User clicks logout
      ↓
2. POST /auth/logout (revokes all user tokens)
      ↓
3. Clear access_token from memory
      ↓
4. Clear refresh timer
      ↓
5. Reset auth store
      ↓
6. Redirect to /auth
```

---

## Styling System

### CSS Variables (`globals.css`)

```css
:root {
  /* Surfaces */
  --surface: #f8fafc;
  --surface-raised: #ffffff;
  --surface-overlay: #f1f5f9;
  --surface-sunken: #e2e8f0;
  
  /* Borders */
  --border: rgba(0, 0, 0, 0.08);
  --border-light: rgba(0, 0, 0, 0.04);
  --border-strong: rgba(0, 0, 0, 0.12);
  
  /* Text */
  --text-primary: #0f172a;
  --text-secondary: #475569;
  --text-muted: #94a3b8;
  --text-inverse: #ffffff;
  
  /* Accent (green) */
  --accent-rgb: 16, 185, 129;
  --accent: rgb(var(--accent-rgb));
  --accent-light: rgba(16, 185, 129, 0.1);
  --accent-subtle: rgba(16, 185, 129, 0.06);
  --accent-border: rgba(16, 185, 129, 0.2);
  
  /* Status colors */
  --success-rgb: 34, 197, 94;
  --danger-rgb: 239, 68, 68;
  --warning-rgb: 245, 158, 11;
  --info-rgb: 59, 130, 246;
}

.dark {
  --surface: #0b0e13;
  --surface-raised: #131820;
  --surface-overlay: #1a1f2a;
  --text-primary: #f1f5f9;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
  --border: rgba(255, 255, 255, 0.08);
}
```

### Tailwind Configuration

```javascript
module.exports = {
  darkMode: 'class',
  content: ['./src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: 'var(--surface)',
        'surface-raised': 'var(--surface-raised)',
        accent: 'rgb(var(--accent-rgb) / <alpha-value>)',
        // ... more colors
      },
      fontFamily: {
        sans: ['var(--font-inter)'],
        mono: ['var(--font-jetbrains)'],
        headline: ['var(--font-headline)'],
      },
      animation: {
        'fade-in': 'fade-in 0.2s ease-out',
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
      },
    },
  },
};
```

---

## WebSocket Integration

### WebSocket Connection

```javascript
// In component
useEffect(() => {
  const ws = new WebSocket(`${WS_BASE_URL}/ws/jobs/${userId}`);
  
  ws.onopen = () => console.log('WebSocket connected');
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch (data.type) {
      case 'material_status':
        handleMaterialStatus(data);
        break;
      case 'podcast_progress':
        usePodcastStore.getState().handleWsEvent(data);
        break;
      case 'job_complete':
        handleJobComplete(data);
        break;
    }
  };
  
  ws.onerror = (err) => console.error('WebSocket error:', err);
  
  return () => ws.close();
}, [userId]);
```

### Event Types

| Event | Payload | Handler |
|-------|---------|---------|
| `material_status` | `{ material_id, status, chunk_count }` | Update material in store |
| `job_complete` | `{ job_id, result }` | Show notification |
| `podcast_progress` | `{ session_id, phase, progress, message }` | Update podcast generation UI |
| `podcast_ready` | `{ session_id }` | Load podcast session |
| `podcast_segment_ready` | `{ segment }` | Add segment to playlist |

---

## Feature Modules

### Flashcards

```jsx
function InlineFlashcardsView() {
  const [flashcards, setFlashcards] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showAnswer, setShowAnswer] = useState(false);
  
  const generateFlashcards = async () => {
    const result = await createFlashcards({
      notebook_id: notebookId,
      material_ids: selectedSources,
      count: 10,
      difficulty: 'medium',
    });
    setFlashcards(result.cards);
  };
  
  return (
    <div className="flashcards-container">
      {flashcards ? (
        <FlashcardCard
          card={flashcards[currentIndex]}
          showAnswer={showAnswer}
          onFlip={() => setShowAnswer(!showAnswer)}
          onNext={() => { setCurrentIndex(i => i + 1); setShowAnswer(false); }}
        />
      ) : (
        <button onClick={generateFlashcards}>Generate Flashcards</button>
      )}
    </div>
  );
}
```

### Quiz

```jsx
function InlineQuizView() {
  const [quiz, setQuiz] = useState(null);
  const [answers, setAnswers] = useState({});
  const [submitted, setSubmitted] = useState(false);
  
  const submitQuiz = () => {
    // Calculate score
    const correct = quiz.questions.filter((q, i) => q.correct === answers[i]).length;
    setSubmitted(true);
  };
  
  return (
    <div className="quiz-container">
      {quiz?.questions.map((q, i) => (
        <QuizQuestion
          key={i}
          question={q}
          selectedAnswer={answers[i]}
          onSelect={(a) => setAnswers({ ...answers, [i]: a })}
          showResult={submitted}
        />
      ))}
    </div>
  );
}
```

### Presentation

```jsx
function PresentationView({ presentationId }) {
  const [html, setHtml] = useState('');
  const [currentSlide, setCurrentSlide] = useState(0);
  
  useEffect(() => {
    fetchPresentationHtml(presentationId).then(setHtml);
  }, [presentationId]);
  
  return (
    <div className="presentation-container">
      <iframe srcDoc={html} className="presentation-iframe" />
      <SlideList 
        slides={slides} 
        currentSlide={currentSlide}
        onSelect={setCurrentSlide}
      />
      <PresentationControls
        onPrev={() => setCurrentSlide(i => Math.max(0, i - 1))}
        onNext={() => setCurrentSlide(i => Math.min(slides.length - 1, i + 1))}
      />
    </div>
  );
}
```

### Podcast

```jsx
function PodcastStudio() {
  const session = usePodcastStore((s) => s.session);
  const phase = usePodcastStore((s) => s.phase);
  const isPlaying = usePodcastStore((s) => s.isPlaying);
  
  const handleCreate = async () => {
    const session = await createPodcastSession({
      notebook_id: notebookId,
      material_ids: selectedSources,
      mode: 'full',
      language: 'en',
    });
    usePodcastStore.getState().setSession(session);
  };
  
  const handleGenerate = async () => {
    await startPodcastGeneration(session.id);
    usePodcastStore.getState().setPhase('generating');
  };
  
  return (
    <div className="podcast-studio">
      {phase === 'idle' && (
        <PodcastConfigDialog onCreate={handleCreate} />
      )}
      {phase === 'generating' && (
        <PodcastGenerating />
      )}
      {phase === 'player' && (
        <PodcastPlayer />
      )}
    </div>
  );
}
```

---

## Performance Optimizations

### Dynamic Imports

```jsx
// Heavy components loaded on demand
const Sidebar = dynamic(() => import('@/components/layout/Sidebar'), { ssr: false });
const ChatPanel = dynamic(() => import('@/components/chat/ChatPanel'), { ssr: false });
const StudioPanel = dynamic(() => import('@/components/studio/StudioPanel'), { ssr: false });
```

### Virtual Lists

```jsx
import { FixedSizeList } from 'react-window';

function MessageList({ messages }) {
  return (
    <FixedSizeList
      height={600}
      itemCount={messages.length}
      itemSize={100}
    >
      {({ index, style }) => (
        <div style={style}>
          <MessageItem message={messages[index]} />
        </div>
      )}
    </FixedSizeList>
  );
}
```

### Memoization

```jsx
const effectiveIds = useMemo(() => 
  selectedSources.filter(id => {
    const mat = materials.find(m => m.id === id);
    return mat?.status === 'completed';
  }),
  [selectedSources, materials]
);

const handleSend = useCallback(async (content) => {
  await sendMessage(content, notebookId);
}, [notebookId, sendMessage]);
```

### Image Lazy Loading

```jsx
<img
  src={notebook.thumbnail_url}
  loading="lazy"
  onError={() => handleThumbnailError(notebook.id)}
/>
```

---

## Error Handling

### Error Boundary

```jsx
class ErrorBoundary extends React.Component {
  state = { hasError: false };
  
  static getDerivedStateFromError(error) {
    return { hasError: true };
  }
  
  componentDidCatch(error, info) {
    console.error('Error caught:', error, info);
  }
  
  render() {
    if (this.state.hasError) {
      return <ErrorFallback onRetry={() => this.setState({ hasError: false })} />;
    }
    return this.props.children;
  }
}
```

### Panel Error Boundaries

```jsx
<PanelErrorBoundary panelName="Chat">
  <ChatPanel />
</PanelErrorBoundary>

<PanelErrorBoundary panelName="Studio">
  <StudioPanel />
</PanelErrorBoundary>
```

### Toast Notifications

```jsx
function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts);
  
  return (
    <div className="toast-container">
      {toasts.map(toast => (
        <Toast key={toast.id} {...toast} />
      ))}
    </div>
  );
}

// Usage
useToastStore.getState().success('Flashcards generated!');
useToastStore.getState().error('Failed to upload file');
```

---

## Build Configuration

### package.json Scripts

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "eslint"
  }
}
```

### Environment Variables

```bash
# Required
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Optional (set in production)
NEXT_PUBLIC_WS_BASE_URL=ws://localhost:8000
```

### Next.js Configuration

```javascript
// next.config.mjs
const config = {
  reactStrictMode: true,
  images: {
    domains: ['lh3.googleusercontent.com'],
  },
};

export default config;
```

---

## Key User Flows

### 1. Create Notebook and Upload Materials

```
Dashboard → Click "New notebook" → Enter draft mode
      ↓
Upload Dialog → Select files → Files upload
      ↓
Background processing (WebSocket updates)
      ↓
Materials appear in sidebar with status indicators
      ↓
Select materials → Ready for chat/generation
```

### 2. Chat with Materials

```
Select materials in sidebar
      ↓
Type message in ChatInput
      ↓
Message sent with material_ids
      ↓
SSE stream received
      ↓
Response rendered with citations
      ↓
Citations link to source materials
```

### 3. Generate Flashcards

```
Select materials
      ↓
Open Studio Panel → Click Flashcards
      ↓
Configure (count, difficulty)
      ↓
Generation request sent
      ↓
Flashcards rendered
      ↓
Study mode: flip cards, track progress
```

### 4. Create Podcast

```
Select materials
      ↓
Open Studio Panel → Click Podcast
      ↓
Configure (mode, topic, voices)
      ↓
Click Generate
      ↓
WebSocket progress updates
      ↓
Audio player appears
      ↓
Play, pause, seek, ask questions
```

---

This completes the comprehensive frontend architecture documentation for KeplerLab.
