import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";
import { normalizeDiagramDetail } from "@/lib/intel";

type RouteContext = { params: Promise<{ id: string }> };

export async function GET(_request: NextRequest, context: RouteContext) {
  const { id } = await context.params;
  const response = await proxyEngineRequest(`/diagrams/${id}`);
  const payload = await readResponsePayload<unknown>(response);
  if (!response.ok) return NextResponse.json(payload, { status: response.status });
  return NextResponse.json(normalizeDiagramDetail(payload as never), { status: response.status });
}

export async function PATCH(request: NextRequest, context: RouteContext) {
  const { id } = await context.params;
  const body = await request.json();
  const response = await proxyEngineRequest(`/diagrams/${id}`, {
    method: "PATCH",
    body: JSON.stringify({
      title: body.title,
      description: body.description,
      graph_definition: body.graphDefinition,
      linked_case_id: body.linkedCaseId,
      linked_str_id: body.linkedStrId,
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

export async function DELETE(_request: NextRequest, context: RouteContext) {
  const { id } = await context.params;
  const response = await proxyEngineRequest(`/diagrams/${id}`, { method: "DELETE" });
  if (!response.ok) {
    const payload = await readResponsePayload<unknown>(response);
    return NextResponse.json(payload, { status: response.status });
  }
  return new NextResponse(null, { status: 204 });
}
