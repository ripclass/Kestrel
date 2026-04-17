import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";
import { normalizeStatistics } from "@/lib/admin-intel";

export async function GET() {
  const response = await proxyEngineRequest("/admin/statistics");
  const payload = await readResponsePayload<unknown>(response);
  if (!response.ok) return NextResponse.json(payload, { status: response.status });
  return NextResponse.json(normalizeStatistics(payload as never), { status: response.status });
}
