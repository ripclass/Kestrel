import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";
import { normalizeSavedQueryDetail, normalizeSavedQueryList } from "@/lib/intel";

export async function GET(request: NextRequest) {
  const response = await proxyEngineRequest(`/saved-queries${request.nextUrl.search}`);
  const payload = await readResponsePayload<{ saved_queries?: unknown[] }>(response);
  if (!response.ok) {
    return NextResponse.json(payload, { status: response.status });
  }
  const success = payload as { saved_queries?: unknown[] };
  return NextResponse.json(
    { savedQueries: normalizeSavedQueryList((success.saved_queries ?? []) as never) },
    { status: response.status },
  );
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const response = await proxyEngineRequest("/saved-queries", {
    method: "POST",
    body: JSON.stringify({
      name: body.name,
      description: body.description ?? null,
      query_type: body.queryType,
      query_definition: body.queryDefinition ?? {},
      is_shared: body.isShared ?? false,
    }),
  });
  const payload = await readResponsePayload<{ saved_query: unknown }>(response);
  if (!response.ok) {
    return NextResponse.json(payload, { status: response.status });
  }
  const success = payload as { saved_query: unknown };
  return NextResponse.json(
    { savedQuery: normalizeSavedQueryDetail(success.saved_query as never) },
    { status: response.status },
  );
}
