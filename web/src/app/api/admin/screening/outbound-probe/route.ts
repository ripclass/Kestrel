import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";

export async function GET() {
  const response = await proxyEngineRequest("/admin/screening/outbound-probe");
  const payload = await readResponsePayload<unknown>(response);
  return NextResponse.json(payload, { status: response.status });
}
