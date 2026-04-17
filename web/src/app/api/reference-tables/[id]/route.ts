import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";
import { normalizeReferenceEntry } from "@/lib/admin-intel";

type RouteContext = { params: Promise<{ id: string }> };

export async function PATCH(request: NextRequest, context: RouteContext) {
  const { id } = await context.params;
  const body = await request.json();
  const response = await proxyEngineRequest(`/reference-tables/${id}`, {
    method: "PATCH",
    body: JSON.stringify({
      value: body.value,
      description: body.description,
      parent_code: body.parentCode,
      metadata: body.metadata,
      is_active: body.isActive,
    }),
  });
  const payload = await readResponsePayload<{ entry: unknown }>(response);
  if (!response.ok) return NextResponse.json(payload, { status: response.status });
  const success = payload as { entry: unknown };
  return NextResponse.json(
    { entry: normalizeReferenceEntry(success.entry as never) },
    { status: response.status },
  );
}

export async function DELETE(_request: NextRequest, context: RouteContext) {
  const { id } = await context.params;
  const response = await proxyEngineRequest(`/reference-tables/${id}`, { method: "DELETE" });
  if (!response.ok) {
    const payload = await readResponsePayload<unknown>(response);
    return NextResponse.json(payload, { status: response.status });
  }
  return new NextResponse(null, { status: 204 });
}
