import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import { normalizeComplianceResponse } from "@/lib/reports";

export async function GET() {
  const response = await proxyEngineRequest("/reports/compliance");
  const payload = await readResponsePayload<{ banks: unknown[] }>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load compliance scorecard.") },
      { status: response.status },
    );
  }

  const result = payload as { banks: unknown[] };
  return NextResponse.json(normalizeComplianceResponse(result.banks as never), { status: response.status });
}
