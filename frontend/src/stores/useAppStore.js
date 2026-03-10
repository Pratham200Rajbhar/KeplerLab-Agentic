import { create } from 'zustand';
import { generateId } from '@/lib/utils/helpers';


export { default as useChatStore } from './useChatStore';
export { default as useMaterialStore } from './useMaterialStore';
export { default as useNotebookStore } from './useNotebookStore';
export { default as useUIStore } from './useUIStore';


const _podcastWsHandlerRef = { current: null };

const useAppStore = create((set, get) => ({
  
  currentNotebook: null,
  draftMode: false,
  newlyCreatedNotebookId: null,

  
  currentMaterial: null,
  materials: [],
  selectedSources: [],

  
  sessionId: null,
  messages: [],

  
  flashcards: null,
  quiz: null,
  notes: [],

  
  pendingChatMessage: null,

  
  loading: {},
  error: null,
  activePanel: 'chat',

  
  podcastWsHandlerRef: _podcastWsHandlerRef,

  
  setCurrentNotebook: (notebook) => set({ currentNotebook: notebook }),
  setDraftMode: (mode) => set({ draftMode: mode }),
  setNewlyCreatedNotebookId: (id) => set({ newlyCreatedNotebookId: id }),

  
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

  
  setSelectedSources: (sourcesOrUpdater) =>
    set((state) => ({
      selectedSources:
        typeof sourcesOrUpdater === 'function'
          ? sourcesOrUpdater(state.selectedSources)
          : sourcesOrUpdater,
    })),

  toggleSourceSelection: (id) =>
    set((state) => ({
      selectedSources: state.selectedSources.includes(id)
        ? state.selectedSources.filter((sid) => sid !== id)
        : [...state.selectedSources, id],
    })),

  selectAllSources: () =>
    set((state) => ({
      selectedSources: state.materials.map((m) => m.id),
    })),

  deselectAllSources: () => set({ selectedSources: [] }),

  isSourceSelected: (id) => {
    const state = useAppStore.getState();
    return state.selectedSources.includes(id);
  },

  
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

  
  setPendingChatMessage: (msg) => set({ pendingChatMessage: msg }),

  
  setLoadingState: (key, value) =>
    set((state) => ({
      loading: { ...state.loading, [key]: value },
    })),
  setError: (error) => set({ error }),
  setActivePanel: (panel) => set({ activePanel: panel }),

  
  resetForNotebookSwitch: () => {
    set({
      selectedSources: [],
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

  
  resetWorkspace: () => {
    set({
      currentNotebook: null,
      draftMode: false,
      currentMaterial: null,
      materials: [],
      selectedSources: [],
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
