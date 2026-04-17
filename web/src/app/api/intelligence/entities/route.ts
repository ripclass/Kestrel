import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import { normalizeEntitySummary } from "@/lib/investigation";

export async function GET(request: NextRequest) {
  const params = new URLSearchParams();
  const query = request.nextUrl.searchParams.get("query");
  if (query) {
    params.set("query", query);
  }

  const response = await proxyEngineRequest(`/intelligence/entities${params.toString() ? `?${params.toString()}` : ""}`);
  const payload = await readResponsePayload<unknown[]>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load shared intelligence entities.") },
      { status: response.status },
    );
  }

  return NextResponse.json(
    { results: ((payload as unknown[]) ?? []).map((item) => normalizeEntitySummary(item as never)) },
    { status: response.status },
  );
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const response = await proxyEngineRequest("/intelligence/entities", {
    method: "POST",
    body: JSON.stringify({
      primary_kind: body.primaryKind ?? "account",
      identifiers: (body.identifiers ?? []).map((ident: { entityType: string; value: string; displayName?: string | null }) => ({
        entity_type: ident.entityType,
        value: ident.value,
        display_name: ident.displayName ?? null,
      })),
      metadata: body.metadata ?? {},
    }),
  });
  const payload = await readResponsePayload<unknown>(response);
  if (!response.ok) return NextResponse.json(payload, { status: response.status });
  return NextResponse.json(payload, { status: response.status });
}
