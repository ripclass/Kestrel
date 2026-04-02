import { NextRequest, NextResponse } from "next/server";

import { DEMO_PERSONA_COOKIE, isPersona } from "@/lib/auth";
import { isDemoModeConfigured } from "@/lib/runtime";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ persona: string }> },
) {
  const { persona } = await params;
  const nextPath = request.nextUrl.searchParams.get("next");
  const redirectTarget =
    nextPath && nextPath.startsWith("/") ? nextPath : "/overview";

  if (!isDemoModeConfigured() || !isPersona(persona)) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  const response = NextResponse.redirect(new URL(redirectTarget, request.url));
  response.cookies.set(DEMO_PERSONA_COOKIE, persona, {
    path: "/",
    sameSite: "lax",
    maxAge: 60 * 60 * 24 * 30,
  });

  return response;
}
