import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";
import { normalizeCaseWorkspace } from "@/lib/cases";

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function POST(request: NextRequest, context: RouteContext) {
  const { id } = await context.params;
  const body = await request.json();
  const response = await proxyEngineRequest(`/cases/${id}/decide`, {
    method: "POST",
    body: JSON.stringify({
      decision: body.decision,
      note: body.note ?? null,
    }),
  });
  const payload = await readResponsePayload<{ case: unknown }>(response);
  if (!response.ok) {
    return NextResponse.json(payload, { status: response.status });
  }
  const success = payload as { case: unknown };
  return NextResponse.json(
    { case: normalizeCaseWorkspace(success.case as never) },
    { status: response.status },
  );
}
