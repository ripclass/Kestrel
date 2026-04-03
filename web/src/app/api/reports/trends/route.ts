import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import { normalizeTrendSeriesResponse } from "@/lib/reports";

export async function GET() {
  const response = await proxyEngineRequest("/reports/trends");
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load trend series.") },
      { status: response.status },
    );
  }

  return NextResponse.json(normalizeTrendSeriesResponse(payload as never), { status: response.status });
}
