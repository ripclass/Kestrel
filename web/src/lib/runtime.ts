function parseEnvBoolean(value: string | undefined): boolean | null {
  if (!value) {
    return null;
  }

  const normalized = value.trim().toLowerCase();
  if (["1", "true", "yes", "on"].includes(normalized)) {
    return true;
  }
  if (["0", "false", "no", "off"].includes(normalized)) {
    return false;
  }
  return null;
}

export function hasAnySupabasePublicEnv() {
  return Boolean(
    process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  );
}

export function isDemoModeConfigured() {
  const explicit = parseEnvBoolean(process.env.NEXT_PUBLIC_ENABLE_DEMO_MODE);
  if (explicit !== null) {
    return explicit;
  }

  return !hasAnySupabasePublicEnv();
}

export function isBankDirectSignupEnabled() {
  // /signup/bank is a vetted request queue — nothing is provisioned until a
  // platform operator approves in /platform/signups — so default-on is safe.
  // The flag remains a kill switch: ENABLE_BANK_DIRECT_SIGNUP=false redirects
  // the page to the briefing intake.
  const explicit = parseEnvBoolean(process.env.ENABLE_BANK_DIRECT_SIGNUP);
  return explicit ?? true;
}
