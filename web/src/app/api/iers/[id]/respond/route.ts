import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";
import { normalizeIERDetail } from "@/lib/iers";

type RouteContext = { params: Promise<{ id: string }> };

export async function POST(request: NextRequest, context: RouteContext) {
  const { id } = await context.params;
  const body = await request.json();
  const response = await proxyEngineRequest(`/iers/${id}/respond`, {
    method: "POST",
    body: JSON.stringify({
      response_narrative: body.responseNarrative,
      linked_str_ids: body.linkedStrIds ?? [],
    }),
  });
  const payload = await readResponsePayload<{ ier: unknown }>(response);
  if (!response.ok) return NextResponse.json(payload, { status: response.status });
  const success = payload as { ier: unknown };
  return NextResponse.json(
    { ier: normalizeIERDetail(success.ier as never) },
    { status: response.status },
  );
}
