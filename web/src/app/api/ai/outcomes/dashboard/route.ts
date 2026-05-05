import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const window = url.searchParams.get("window_days");
  const qs = window ? `?window_days=${encodeURIComponent(window)}` : "";

  const response = await proxyEngineRequest(`/ai/outcomes/dashboard${qs}`);
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load AI outcome dashboard.") },
      { status: response.status },
    );
  }
  return NextResponse.json(payload, { status: response.status });
}
