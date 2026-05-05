import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const limit = url.searchParams.get("limit") ?? "50";
  const qs = `?limit=${encodeURIComponent(limit)}`;

  const response = await proxyEngineRequest(`/transactions/score/recent${qs}`);
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load recent scores.") },
      { status: response.status },
    );
  }

  return NextResponse.json({ rows: payload }, { status: response.status });
}
