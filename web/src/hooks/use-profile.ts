"use client";

import { getViewerForPersona } from "@/lib/demo";
import { isDemoModeConfigured } from "@/lib/runtime";

export function useProfile() {
  return {
    profile: isDemoModeConfigured()
      ? getViewerForPersona(process.env.NEXT_PUBLIC_DEMO_PERSONA)
      : null,
  };
}
