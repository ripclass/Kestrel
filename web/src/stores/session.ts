import { create } from "zustand";

import type { Viewer } from "@/types/domain";

interface SessionStore {
  viewer: Viewer | null;
  setViewer: (viewer: Viewer | null) => void;
}

export const useSessionStore = create<SessionStore>((set) => ({
  viewer: null,
  setViewer: (viewer) => set({ viewer }),
}));
