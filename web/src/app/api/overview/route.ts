import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import { normalizeOverviewResponse } from "@/lib/overview";

export async function GET() {
  const response = await proxyEngineRequest("/overview");
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load overview metrics.") },
      { status: response.status },
    );
  }

  return NextResponse.json(normalizeOverviewResponse(payload as never), { status: response.status });
}
