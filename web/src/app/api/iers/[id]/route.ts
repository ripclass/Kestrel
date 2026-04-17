import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";
import { normalizeIERDetail } from "@/lib/iers";

type RouteContext = { params: Promise<{ id: string }> };

export async function GET(_request: NextRequest, context: RouteContext) {
  const { id } = await context.params;
  const response = await proxyEngineRequest(`/iers/${id}`);
  const payload = await readResponsePayload<unknown>(response);
  if (!response.ok) return NextResponse.json(payload, { status: response.status });
  return NextResponse.json(normalizeIERDetail(payload as never), { status: response.status });
}
