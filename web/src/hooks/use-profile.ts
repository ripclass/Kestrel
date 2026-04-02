"use client";

import { useEffect, useState } from "react";
import type { AuthChangeEvent, Session, User } from "@supabase/supabase-js";

import { getViewerForPersona } from "@/lib/demo";
import { isDemoModeConfigured } from "@/lib/runtime";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import { fetchViewerFromSupabaseClient, type ProfileLookupClient } from "@/lib/viewer";
import type { Viewer } from "@/types/domain";

export function useProfile() {
  const [profile, setProfile] = useState<Viewer | null>(
    isDemoModeConfigured() ? getViewerForPersona(process.env.NEXT_PUBLIC_DEMO_PERSONA) : null,
  );

  useEffect(() => {
    if (isDemoModeConfigured()) {
      return;
    }

    const supabase = createSupabaseBrowserClient();
    if (!supabase) {
      return;
    }

    let active = true;

    supabase.auth.getUser().then(async (result: { data: { user: User | null } }) => {
      const { data } = result;
      if (!active || !data.user) {
        if (active) {
          setProfile(null);
        }
        return;
      }

      const viewer = await fetchViewerFromSupabaseClient(
        supabase as unknown as ProfileLookupClient,
        data.user,
      );
      if (active) {
        setProfile(viewer);
      }
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event: AuthChangeEvent, session: Session | null) => {
      if (!session?.user) {
        setProfile(null);
        return;
      }

      void fetchViewerFromSupabaseClient(
        supabase as unknown as ProfileLookupClient,
        session.user,
      ).then((viewer) => {
        if (active) {
          setProfile(viewer);
        }
      });
    });

    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, []);

  return { profile };
}
