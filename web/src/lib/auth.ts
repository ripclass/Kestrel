import { redirect } from "next/navigation";

import { getViewerForPersona } from "@/lib/demo";
import { createSupabaseBrowserClient } from "@/lib/supabase/client";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import type { Persona, Viewer } from "@/types/domain";

function inferPersona(rawPersona: unknown): Persona {
  if (
    rawPersona === "bfiu_analyst" ||
    rawPersona === "bank_camlco" ||
    rawPersona === "bfiu_director"
  ) {
    return rawPersona;
  }

  return (process.env.KESTREL_DEMO_PERSONA as Persona | undefined) ?? "bfiu_analyst";
}

export async function getCurrentViewer(): Promise<Viewer | null> {
  const supabase = await createSupabaseServerClient();

  if (!supabase) {
    const demoPersona = process.env.KESTREL_DEMO_PERSONA as Persona | undefined;
    return demoPersona ? getViewerForPersona(demoPersona) : null;
  }

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    return null;
  }

  const persona = inferPersona(user.user_metadata.persona);
  const fallback = getViewerForPersona(persona);

  return {
    ...fallback,
    id: user.id,
    email: user.email ?? fallback.email,
    fullName: String(user.user_metadata.full_name ?? fallback.fullName),
    orgId: String(user.user_metadata.org_id ?? fallback.orgId),
    designation: String(user.user_metadata.designation ?? fallback.designation),
  };
}

export async function requireViewer() {
  const viewer = await getCurrentViewer();

  if (!viewer) {
    redirect("/login");
  }

  return viewer;
}

export async function signOutBrowser() {
  const supabase = createSupabaseBrowserClient();

  if (!supabase) {
    return;
  }

  await supabase.auth.signOut();
}
