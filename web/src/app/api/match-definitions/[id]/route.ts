import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";
import { normalizeMatchDefinitionDetail } from "@/lib/intel";

type RouteContext = { params: Promise<{ id: string }> };

export async function GET(_request: NextRequest, context: RouteContext) {
  const { id } = await context.params;
  const response = await proxyEngineRequest(`/match-definitions/${id}`);
  const payload = await readResponsePayload<unknown>(response);
  if (!response.ok) return NextResponse.json(payload, { status: response.status });
  return NextResponse.json(normalizeMatchDefinitionDetail(payload as never), { status: response.status });
}

export async function PATCH(request: NextRequest, context: RouteContext) {
  const { id } = await context.params;
  const body = await request.json();
  const response = await proxyEngineRequest(`/match-definitions/${id}`, {
    method: "PATCH",
    body: JSON.stringify({
      name: body.name,
      description: body.description,
      definition: body.definition,
      is_active: body.isActive,
    }),
  });
  const payload = await readResponsePayload<{ match_definition: unknown }>(response);
  if (!response.ok) return NextResponse.json(payload, { status: response.status });
  const success = payload as { match_definition: unknown };
  return NextResponse.json(
    { matchDefinition: normalizeMatchDefinitionDetail(success.match_definition as never) },
    { status: response.status },
  );
}

export async function DELETE(_request: NextRequest, context: RouteContext) {
  const { id } = await context.params;
  const response = await proxyEngineRequest(`/match-definitions/${id}`, { method: "DELETE" });
  if (!response.ok) {
    const payload = await readResponsePayload<unknown>(response);
    return NextResponse.json(payload, { status: response.status });
  }
  return new NextResponse(null, { status: 204 });
}
