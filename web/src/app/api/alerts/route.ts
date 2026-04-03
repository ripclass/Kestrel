import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import { normalizeAlertSummary } from "@/lib/alerts";

export async function GET() {
  const response = await proxyEngineRequest("/alerts");
  const payload = await readResponsePayload<unknown[]>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load alerts.") },
      { status: response.status },
    );
  }

  return NextResponse.json(
    { alerts: ((payload as unknown[]) ?? []).map((item) => normalizeAlertSummary(item as never)) },
    { status: response.status },
  );
}
