import { create } from 'zustand';

const useNotebookStore = create((set) => ({
  
  currentNotebook: null,
  draftMode: false,

  
  setCurrentNotebook: (notebook) => set({ currentNotebook: notebook }),
  setDraftMode: (mode) => set({ draftMode: mode }),
  resetNotebook: () => set({ currentNotebook: null, draftMode: false }),
}));

export default useNotebookStore;
