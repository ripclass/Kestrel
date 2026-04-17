import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";
import { normalizeDiagramDetail, normalizeDiagramList } from "@/lib/intel";

export async function GET(request: NextRequest) {
  const response = await proxyEngineRequest(`/diagrams${request.nextUrl.search}`);
  const payload = await readResponsePayload<{ diagrams?: unknown[] }>(response);
  if (!response.ok) return NextResponse.json(payload, { status: response.status });
  const success = payload as { diagrams?: unknown[] };
  return NextResponse.json(
    { diagrams: normalizeDiagramList((success.diagrams ?? []) as never) },
    { status: response.status },
  );
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const response = await proxyEngineRequest("/diagrams", {
    method: "POST",
    body: JSON.stringify({
      title: body.title,
      description: body.description ?? null,
      graph_definition: body.graphDefinition ?? {},
      linked_case_id: body.linkedCaseId ?? null,
      linked_str_id: body.linkedStrId ?? null,
    }),
  });
  const payload = await readResponsePayload<{ diagram: unknown }>(response);
  if (!response.ok) return NextResponse.json(payload, { status: response.status });
  const success = payload as { diagram: unknown };
  return NextResponse.json(
    { diagram: normalizeDiagramDetail(success.diagram as never) },
    { status: response.status },
  );
}
