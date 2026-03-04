import { create } from 'zustand';
import { generateId } from '@/lib/utils/helpers';

// Shared ref for routing podcast WS events
const _podcastWsHandlerRef = { current: null };

const useAppStore = create((set, get) => ({
  // ── Notebook state ──
  currentNotebook: null,
  draftMode: false,

  // ── Material state ──
  currentMaterial: null,
  materials: [],
  selectedSources: new Set(),

  // ── Chat state ──
  sessionId: null,
  messages: [],

  // ── Generated content ──
  flashcards: null,
  quiz: null,
  notes: [],

  // ── Mind map → chat bridge ──
  pendingChatMessage: null,

  // ── UI state ──
  loading: {},
  error: null,
  activePanel: 'chat',

  // ── Podcast WS bridge ──
  podcastWsHandlerRef: _podcastWsHandlerRef,

  // ── Notebook actions ──
  setCurrentNotebook: (notebook) => set({ currentNotebook: notebook }),
  setDraftMode: (mode) => set({ draftMode: mode }),

  // ── Material actions ──
  setCurrentMaterial: (material) => set({ currentMaterial: material }),
  setMaterials: (materialsOrUpdater) =>
    set((state) => ({
      materials:
        typeof materialsOrUpdater === 'function'
          ? materialsOrUpdater(state.materials)
          : Array.isArray(materialsOrUpdater)
            ? materialsOrUpdater
            : state.materials,
    })),
  addMaterial: (material) =>
    set((state) => ({
      materials: [...state.materials, material],
      currentMaterial: state.currentMaterial || material,
    })),

  // ── Source selection ──
  setSelectedSources: (sourcesOrUpdater) =>
    set((state) => ({
      selectedSources:
        typeof sourcesOrUpdater === 'function'
          ? sourcesOrUpdater(state.selectedSources)
          : sourcesOrUpdater,
    })),

  toggleSourceSelection: (id) =>
    set((state) => {
      const next = new Set(state.selectedSources);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return { selectedSources: next };
    }),

  selectAllSources: () =>
    set((state) => ({
      selectedSources: new Set(state.materials.map((m) => m.id)),
    })),

  deselectAllSources: () => set({ selectedSources: new Set() }),

  // ── Chat actions ──
  setSessionId: (id) => set({ sessionId: id }),
  setMessages: (messagesOrUpdater) =>
    set((state) => ({
      messages:
        typeof messagesOrUpdater === 'function'
          ? messagesOrUpdater(state.messages)
          : messagesOrUpdater,
    })),
  addMessage: (role, content, extra = null) => {
    const message = {
      id: generateId(),
      role,
      content,
      citations: extra?.citations || (Array.isArray(extra) ? extra : null),
      slashCommand: extra?.slashCommand || null,
      timestamp: new Date(),
    };
    set((state) => ({ messages: [...state.messages, message] }));
    return message;
  },
  clearMessages: () => set({ messages: [], sessionId: null }),

  // ── Generated content actions ──
  setFlashcards: (flashcards) => set({ flashcards }),
  setQuiz: (quiz) => set({ quiz }),
  setNotes: (notes) => set({ notes }),
  addNote: (content, source = null) => {
    const note = {
      id: generateId(),
      content,
      source,
      timestamp: new Date(),
    };
    set((state) => ({ notes: [...state.notes, note] }));
    return note;
  },

  // ── Mind map ──
  setPendingChatMessage: (msg) => set({ pendingChatMessage: msg }),

  // ── UI actions ──
  setLoadingState: (key, value) =>
    set((state) => ({
      loading: { ...state.loading, [key]: value },
    })),
  setError: (error) => set({ error }),
  setActivePanel: (panel) => set({ activePanel: panel }),

  // ── Notebook switch cleanup ──
  resetForNotebookSwitch: () => {
    set({
      selectedSources: new Set(),
      currentMaterial: null,
      materials: [],
      messages: [],
      sessionId: null,
      flashcards: null,
      quiz: null,
      notes: [],
      error: null,
      loading: {},
      activePanel: 'chat',
    });
  },

  // ── Full reset ──
  resetWorkspace: () => {
    set({
      currentNotebook: null,
      draftMode: false,
      currentMaterial: null,
      materials: [],
      selectedSources: new Set(),
      sessionId: null,
      messages: [],
      flashcards: null,
      quiz: null,
      notes: [],
      pendingChatMessage: null,
      loading: {},
      error: null,
      activePanel: 'chat',
    });
  },
}));

export default useAppStore;
