import { create } from 'zustand';

const useUIStore = create((set) => ({
  // ── State ──
  loading: {},
  activePanel: 'chat',

  // ── Actions ──
  setLoadingState: (key, value) =>
    set((state) => ({
      loading: { ...state.loading, [key]: value },
    })),

  setActivePanel: (panel) => set({ activePanel: panel }),
}));

export default useUIStore;
