import { create } from 'zustand';

const useNotebookStore = create((set) => ({
  // ── State ──
  currentNotebook: null,
  draftMode: false,

  // ── Actions ──
  setCurrentNotebook: (notebook) => set({ currentNotebook: notebook }),
  setDraftMode: (mode) => set({ draftMode: mode }),
  resetNotebook: () => set({ currentNotebook: null, draftMode: false }),
}));

export default useNotebookStore;
