import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const params = new URLSearchParams();
  const limit = url.searchParams.get("limit");
  const onlyCorrected = url.searchParams.get("only_corrected");
  if (limit) params.set("limit", limit);
  if (onlyCorrected) params.set("only_corrected", onlyCorrected);
  const qs = params.toString() ? `?${params.toString()}` : "";

  const response = await proxyEngineRequest(`/ai/outcomes/recent${qs}`);
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load recent AI outcomes.") },
      { status: response.status },
    );
  }
  return NextResponse.json({ rows: payload }, { status: response.status });
}
