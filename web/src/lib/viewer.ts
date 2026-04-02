import type { User } from "@supabase/supabase-js";

import { getViewerForPersona } from "@/lib/demo";
import type {
  DatabaseOrganizationRow,
  DatabaseProfileWithOrganizationRow,
} from "@/types/database";
import type { Persona, Viewer } from "@/types/domain";

export interface ProfileLookupClient {
  from: (table: string) => {
    select: (columns: string) => {
      eq: (column: string, value: string) => {
        maybeSingle: () => Promise<{ data: DatabaseProfileWithOrganizationRow | null }>;
      };
    };
  };
}

function isPersona(rawPersona: unknown): rawPersona is Persona {
  return rawPersona === "bfiu_analyst" || rawPersona === "bfiu_director" || rawPersona === "bank_camlco";
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

function normalizeOrganization(
  organization: DatabaseProfileWithOrganizationRow["organizations"],
): DatabaseOrganizationRow | null {
  if (Array.isArray(organization)) {
    return organization[0] ?? null;
  }

  return organization ?? null;
}

export function buildViewerFromSupabaseUser(
  user: User,
  profile: DatabaseProfileWithOrganizationRow | null,
): Viewer {
  const fallback = getViewerForPersona(inferPersona(user.user_metadata.persona));
  const organization = normalizeOrganization(profile?.organizations ?? null);

  return {
    id: user.id,
    email: user.email ?? fallback.email,
    fullName: String(profile?.full_name ?? user.user_metadata.full_name ?? fallback.fullName),
    designation: String(profile?.designation ?? user.user_metadata.designation ?? fallback.designation),
    role: profile?.role ?? fallback.role,
    persona: profile?.persona ?? fallback.persona,
    orgId: String(profile?.org_id ?? user.user_metadata.org_id ?? fallback.orgId),
    orgName: organization?.name ?? String(user.user_metadata.org_name ?? fallback.orgName),
    orgType: organization?.org_type ?? fallback.orgType,
  };
}

export async function fetchViewerFromSupabaseClient(
  supabase: ProfileLookupClient,
  user: User,
): Promise<Viewer> {
  const { data } = await supabase
    .from("profiles")
    .select("id, org_id, full_name, role, persona, designation, organizations(name, org_type)")
    .eq("id", user.id)
    .maybeSingle();

  return buildViewerFromSupabaseUser(user, data);
}
