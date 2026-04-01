import { create } from "zustand";

interface InvestigationStore {
  selectedEntityId: string | null;
  setSelectedEntityId: (entityId: string | null) => void;
}

export const useInvestigationStore = create<InvestigationStore>((set) => ({
  selectedEntityId: "ent-rizwana-account",
  setSelectedEntityId: (selectedEntityId) => set({ selectedEntityId }),
}));
