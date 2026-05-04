import { NextResponse } from "next/server";

import { normalizeSummary } from "@/lib/cross-bank";
import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const windowDays = url.searchParams.get("window_days") ?? url.searchParams.get("windowDays");
  const qs = windowDays ? `?window_days=${encodeURIComponent(windowDays)}` : "";

  const response = await proxyEngineRequest(`/intelligence/cross-bank/summary${qs}`);
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load cross-bank summary.") },
      { status: response.status },
    );
  }

  return NextResponse.json({ summary: normalizeSummary(payload as never) }, { status: response.status });
}
