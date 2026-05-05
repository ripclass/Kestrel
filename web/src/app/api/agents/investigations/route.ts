import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const params = new URLSearchParams();
  const entityId = url.searchParams.get("entity_id");
  const limit = url.searchParams.get("limit");
  if (entityId) params.set("entity_id", entityId);
  if (limit) params.set("limit", limit);
  const qs = params.toString() ? `?${params.toString()}` : "";

  const response = await proxyEngineRequest(`/agents/investigations${qs}`);
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load investigations.") },
      { status: response.status },
    );
  }
  return NextResponse.json({ rows: payload }, { status: response.status });
}
