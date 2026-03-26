import { create } from 'zustand';

const useMindMapStore = create((set) => ({
  expandedNodeIds: new Set(),
  activeMindMapData: null,

  toggleExpand: (nodeId) => {
    set((state) => {
      const newSet = new Set(state.expandedNodeIds);
      if (newSet.has(nodeId)) {
        const prefix = `${nodeId}-`;
        for (const id of newSet) {
          if (id.startsWith(prefix)) newSet.delete(id);
        }
        newSet.delete(nodeId);
      } else {
        newSet.add(nodeId);
      }
      return { expandedNodeIds: newSet };
    });
  },

  setExpandedNodeIds: (nodeIds = []) => set({ expandedNodeIds: new Set(nodeIds) }),

  setActiveMindMap: (data) => set({ activeMindMapData: data }),

  clearMindMap: () => set({ 
    activeMindMapData: null, 
    expandedNodeIds: new Set() 
  }),
}));

export default useMindMapStore;
