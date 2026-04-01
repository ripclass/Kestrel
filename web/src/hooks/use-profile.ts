"use client";

import { getViewerForPersona } from "@/lib/demo";

export function useProfile() {
  return {
    profile: getViewerForPersona(process.env.NEXT_PUBLIC_DEMO_PERSONA),
  };
}
