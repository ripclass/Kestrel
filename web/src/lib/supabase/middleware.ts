import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

// Authenticated platform routes. Anything starting with these prefixes is
// behind requireViewer() at the page level; middleware uses the same list
// to decide whether to apply persona-based access control.
const PLATFORM_PREFIXES: ReadonlyArray<string> = [
  "/overview",
  "/strs",
  "/alerts",
  "/cases",
  "/iers",
  "/intelligence",
  "/investigate",
  "/monitoring",
  "/reports",
  "/screen",
  "/scan",
  "/customers",
  "/admin",
];

// Bank-filer allowlist. Filers landing on anything outside this set get
// redirected to /strs. Matches FILER_ALLOWED_HREFS in nav-config.ts; keep
// the two in sync.
const FILER_ALLOWED_PREFIXES: ReadonlyArray<string> = [
  "/strs",
  "/iers",
  "/reports/export",
];

function isPlatformPath(pathname: string): boolean {
  return PLATFORM_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

function isFilerAllowed(pathname: string): boolean {
  return FILER_ALLOWED_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

export async function updateSession(request: NextRequest) {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseAnonKey) {
    return NextResponse.next({ request });
  }

  let response = NextResponse.next({ request });

  const supabase = createServerClient(supabaseUrl, supabaseAnonKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) => response.cookies.set(name, value, options));
      },
    },
  });

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (user && isPlatformPath(request.nextUrl.pathname)) {
    const persona =
      (user.app_metadata?.persona as string | undefined) ??
      (user.user_metadata?.persona as string | undefined);
    if (persona === "bank_filer" && !isFilerAllowed(request.nextUrl.pathname)) {
      const redirectUrl = request.nextUrl.clone();
      redirectUrl.pathname = "/strs";
      redirectUrl.search = "";
      return NextResponse.redirect(redirectUrl);
    }
  }

  return response;
}
