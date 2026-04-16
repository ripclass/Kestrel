import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";

export async function GET(request: NextRequest) {
  const response = await proxyEngineRequest(`/ctr${request.nextUrl.search}`);
  const payload = await readResponsePayload<unknown>(response);
  if (!response.ok) {
    return NextResponse.json(payload, { status: response.status });
  }
  return NextResponse.json(payload, { status: response.status });
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const response = await proxyEngineRequest("/ctr/import", {
    method: "POST",
    body: JSON.stringify({ records: body.records }),
  });
  const payload = await readResponsePayload<unknown>(response);
  if (!response.ok) {
    return NextResponse.json(payload, { status: response.status });
  }
  return NextResponse.json(payload, { status: response.status });
}
