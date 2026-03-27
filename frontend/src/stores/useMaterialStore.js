import { create } from 'zustand';
import { generateResources, uploadGeneratedResources } from '@/lib/api/aiResource';

const useMaterialStore = create((set, get) => ({
  
  materials: [],
  currentMaterial: null,
  selectedSources: [],
  aiResourceResult: null,

  
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

  generateAIResources: async (query, notebookId = null) => {
    const result = await generateResources(query, notebookId);
    set({ aiResourceResult: result });
    return result;
  },

  uploadAIResources: async ({ result, notebookId = null, autoCreateNotebook = false, notesTitle } = {}) => {
    const payload = {
      resources: result?.resources || [],
      notes: result?.notes || '',
      notebookId,
      autoCreateNotebook,
      notesTitle,
    };
    return uploadGeneratedResources(payload);
  },
}));

export default useMaterialStore;
