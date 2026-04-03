import { create } from "zustand";

interface GraphStore {
  selectedNodeId: string | null;
  showSuspiciousOnly: boolean;
  setSelectedNodeId: (nodeId: string | null) => void;
  toggleSuspiciousOnly: () => void;
}

export const useGraphStore = create<GraphStore>((set) => ({
  selectedNodeId: null,
  showSuspiciousOnly: false,
  setSelectedNodeId: (selectedNodeId) => set({ selectedNodeId }),
  toggleSuspiciousOnly: () =>
    set((state) => ({ showSuspiciousOnly: !state.showSuspiciousOnly })),
}));
