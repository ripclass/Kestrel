import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";
import { normalizeIERList } from "@/lib/iers";

export async function GET(request: NextRequest) {
  const response = await proxyEngineRequest(`/iers${request.nextUrl.search}`);
  const payload = await readResponsePayload<{ iers?: unknown[] }>(response);
  if (!response.ok) return NextResponse.json(payload, { status: response.status });
  const success = payload as { iers?: unknown[] };
  return NextResponse.json(
    { iers: normalizeIERList((success.iers ?? []) as never) },
    { status: response.status },
  );
}
