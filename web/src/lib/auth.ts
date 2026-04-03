import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { getViewerForPersona } from "@/lib/demo";
import { isDemoModeConfigured } from "@/lib/runtime";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { fetchViewerFromSupabaseClient, type ProfileLookupClient } from "@/lib/viewer";
import type { Persona, Role, Viewer } from "@/types/domain";

export const DEMO_PERSONA_COOKIE = "kestrel_demo_persona";

export function isPersona(rawPersona: unknown): rawPersona is Persona {
  if (
    rawPersona === "bfiu_analyst" ||
    rawPersona === "bank_camlco" ||
    rawPersona === "bfiu_director"
  ) {
    return true;
  }

  return false;
}

function inferPersona(rawPersona: unknown): Persona {
  if (isPersona(rawPersona)) {
    return rawPersona;
  }

  if (isPersona(process.env.KESTREL_DEMO_PERSONA)) {
    return process.env.KESTREL_DEMO_PERSONA;
  }

  if (isPersona(process.env.NEXT_PUBLIC_DEMO_PERSONA)) {
    return process.env.NEXT_PUBLIC_DEMO_PERSONA;
  }

  return "bfiu_analyst";
}

export function isDemoModeEnabled() {
  return isDemoModeConfigured();
}

export async function getActiveDemoPersona(): Promise<Persona> {
  const cookieStore = await cookies();
  const cookiePersona = cookieStore.get(DEMO_PERSONA_COOKIE)?.value;

  return inferPersona(cookiePersona);
}

export async function getCurrentViewer(): Promise<Viewer | null> {
  const supabase = await createSupabaseServerClient();

  if (!supabase) {
    if (!isDemoModeEnabled()) {
      return null;
    }
    return getViewerForPersona(await getActiveDemoPersona());
  }

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return null;
  }

  return fetchViewerFromSupabaseClient(supabase as unknown as ProfileLookupClient, user);
}

export async function requireViewer() {
  const viewer = await getCurrentViewer();

  if (!viewer) {
    redirect("/login");
  }

  return viewer;
}

export async function requireRole(...roles: Role[]) {
  const viewer = await requireViewer();

  if (!roles.includes(viewer.role)) {
    redirect("/overview");
  }

  return viewer;
}
