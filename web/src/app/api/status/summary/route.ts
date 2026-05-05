import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";

// Public — no auth header is forwarded because the engine route is open.
export async function GET() {
  const response = await proxyEngineRequest(`/status/summary`);
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load status.") },
      { status: response.status },
    );
  }
  return NextResponse.json(payload, { status: response.status });
}
