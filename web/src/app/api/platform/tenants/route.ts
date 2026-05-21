import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";

export async function GET() {
  const response = await proxyEngineRequest(`/platform/tenants`);
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load tenants.") },
      { status: response.status },
    );
  }
  return NextResponse.json(payload, { status: response.status });
}
