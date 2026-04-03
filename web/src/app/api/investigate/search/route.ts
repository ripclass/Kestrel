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

  const response = await proxyEngineRequest(`/investigate/search${params.toString() ? `?${params.toString()}` : ""}`);
  const payload = await readResponsePayload<unknown[]>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to search shared entities.") },
      { status: response.status },
    );
  }

  return NextResponse.json(
    { results: ((payload as unknown[]) ?? []).map((item) => normalizeEntitySummary(item as never)) },
    { status: response.status },
  );
}
