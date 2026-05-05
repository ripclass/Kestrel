import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const params = new URLSearchParams();
  const windowHours = url.searchParams.get("window_hours") ?? url.searchParams.get("windowHours");
  const topLimit = url.searchParams.get("top_limit") ?? url.searchParams.get("topLimit");
  if (windowHours) params.set("window_hours", windowHours);
  if (topLimit) params.set("top_limit", topLimit);
  const qs = params.toString() ? `?${params.toString()}` : "";

  const response = await proxyEngineRequest(`/transactions/score/metrics${qs}`);
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load realtime metrics.") },
      { status: response.status },
    );
  }

  return NextResponse.json({ metrics: payload }, { status: response.status });
}
