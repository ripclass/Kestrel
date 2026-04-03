import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import { normalizeNationalReportResponse } from "@/lib/reports";

export async function GET() {
  const response = await proxyEngineRequest("/reports/national");
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load national dashboard metrics.") },
      { status: response.status },
    );
  }

  return NextResponse.json(normalizeNationalReportResponse(payload as never), { status: response.status });
}
