import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";
import { normalizeSavedQueryDetail } from "@/lib/intel";

type RouteContext = { params: Promise<{ id: string }> };

export async function GET(_request: NextRequest, context: RouteContext) {
  const { id } = await context.params;
  const response = await proxyEngineRequest(`/saved-queries/${id}`);
  const payload = await readResponsePayload<unknown>(response);
  if (!response.ok) return NextResponse.json(payload, { status: response.status });
  return NextResponse.json(normalizeSavedQueryDetail(payload as never), { status: response.status });
}

export async function PATCH(request: NextRequest, context: RouteContext) {
  const { id } = await context.params;
  const body = await request.json();
  const response = await proxyEngineRequest(`/saved-queries/${id}`, {
    method: "PATCH",
    body: JSON.stringify({
      name: body.name,
      description: body.description,
      query_definition: body.queryDefinition,
      is_shared: body.isShared,
    }),
  });
  const payload = await readResponsePayload<{ saved_query: unknown }>(response);
  if (!response.ok) return NextResponse.json(payload, { status: response.status });
  const success = payload as { saved_query: unknown };
  return NextResponse.json(
    { savedQuery: normalizeSavedQueryDetail(success.saved_query as never) },
    { status: response.status },
  );
}

export async function DELETE(_request: NextRequest, context: RouteContext) {
  const { id } = await context.params;
  const response = await proxyEngineRequest(`/saved-queries/${id}`, { method: "DELETE" });
  if (!response.ok) {
    const payload = await readResponsePayload<unknown>(response);
    return NextResponse.json(payload, { status: response.status });
  }
  return new NextResponse(null, { status: 204 });
}
