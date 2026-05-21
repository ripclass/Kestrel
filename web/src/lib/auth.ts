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
    rawPersona === "bfiu_director" ||
    rawPersona === "bank_filer"
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

/**
 * Platform-operator gate. Access to the cross-tenant pilot-health console is
 * an Enso-internal email allow-list (`KESTREL_PLATFORM_OPERATORS`), not the
 * per-tenant role model — a bank or BFIU customer must never see pilot
 * telemetry across other tenants. This is a UX gate; the engine route
 * (`/platform/*`) enforces the same allow-list authoritatively.
 */
export function isPlatformOperatorEmail(email: string | null | undefined): boolean {
  if (!email) {
    return false;
  }
  const allow = new Set(
    (process.env.KESTREL_PLATFORM_OPERATORS ?? "")
      .split(",")
      .map((entry) => entry.trim().toLowerCase())
      .filter(Boolean),
  );
  return allow.has(email.trim().toLowerCase());
}

export async function requirePlatformOperator() {
  const viewer = await requireViewer();

  if (!isPlatformOperatorEmail(viewer.email)) {
    // Don't reveal the console exists — bounce non-operators to Overview.
    redirect("/overview");
  }

  return viewer;
}

/**
 * Bank filer surface allowlist (path prefixes). Anything outside these prefixes
 * redirects a filer back to /strs. The full feature set — cross-bank,
 * AI, KYC, screening, real-time, cases, admin — stays hidden by route as
 * defense-in-depth on top of the nav-config gating.
 */
const FILER_ALLOWED_PREFIXES: ReadonlyArray<string> = [
  "/strs",
  "/iers",
  "/reports/export",
];

export function isFilerAllowedPath(pathname: string): boolean {
  return FILER_ALLOWED_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

export async function requireViewerForPath(pathname: string) {
  const viewer = await requireViewer();

  if (viewer.persona === "bank_filer" && !isFilerAllowedPath(pathname)) {
    redirect("/strs");
  }

  return viewer;
}
