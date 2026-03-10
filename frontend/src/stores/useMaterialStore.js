import { create } from 'zustand';

const useMaterialStore = create((set, get) => ({
  
  materials: [],
  currentMaterial: null,
  selectedSources: [],

  
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

  updateMaterial: (id, updates) =>
    set((state) => ({
      materials: state.materials.map((m) => (m.id === id ? { ...m, ...updates } : m)),
    })),

  removeMaterial: (id) =>
    set((state) => ({
      materials: state.materials.filter((m) => m.id !== id),
      currentMaterial: state.currentMaterial?.id === id
        ? (state.materials.filter((m) => m.id !== id)[0] || null)
        : state.currentMaterial,
      selectedSources: state.selectedSources.filter((sid) => sid !== id),
    })),

  setCurrentMaterial: (material) => set({ currentMaterial: material }),

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

  
  isSourceSelected: (id) => get().selectedSources.includes(id),

  setSelectedSources: (sourcesOrUpdater) =>
    set((state) => ({
      selectedSources:
        typeof sourcesOrUpdater === 'function'
          ? sourcesOrUpdater(state.selectedSources)
          : sourcesOrUpdater,
    })),
}));

export default useMaterialStore;
