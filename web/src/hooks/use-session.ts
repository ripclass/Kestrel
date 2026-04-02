"use client";

import { useEffect, useState } from "react";

import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import { isDemoModeConfigured } from "@/lib/runtime";

export function useSession() {
  const [email, setEmail] = useState<string | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(isDemoModeConfigured());

  useEffect(() => {
    if (isDemoModeConfigured()) {
      return;
    }

    const supabase = createSupabaseBrowserClient();
    if (!supabase) {
      return;
    }

    supabase.auth.getUser().then((result: { data: { user: { email?: string | null } | null } }) => {
      setEmail(result.data.user?.email ?? null);
      setIsAuthenticated(Boolean(result.data.user));
    });
  }, []);

  return { email, isAuthenticated };
}
