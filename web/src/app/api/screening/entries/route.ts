import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const params = new URLSearchParams();
  const listSource = url.searchParams.get("list_source");
  const limit = url.searchParams.get("limit");
  const includeRemoved = url.searchParams.get("include_removed");
  if (listSource) params.set("list_source", listSource);
  if (limit) params.set("limit", limit);
  if (includeRemoved) params.set("include_removed", includeRemoved);
  const qs = params.toString() ? `?${params.toString()}` : "";

  const response = await proxyEngineRequest(`/screening/entries${qs}`);
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load watchlist entries.") },
      { status: response.status },
    );
  }
  return NextResponse.json({ rows: payload }, { status: response.status });
}
