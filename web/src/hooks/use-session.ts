"use client";

import { useEffect, useState } from "react";

import { createSupabaseBrowserClient } from "@/lib/supabase/client";

export function useSession() {
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    const supabase = createSupabaseBrowserClient();
    if (!supabase) {
      return;
    }

    supabase.auth.getUser().then((result: { data: { user: { email?: string | null } | null } }) => {
      setEmail(result.data.user?.email ?? null);
    });
  }, []);

  return { email };
}
