import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";

export async function POST(request: NextRequest) {
  // Forward the raw multipart bytes so the boundary survives intact —
  // rebuilding FormData on the server round-trips through re-encoding.
  const contentType = request.headers.get("content-type") ?? "";
  const bodyBuffer = await request.arrayBuffer();

  const response = await proxyEngineRequest("/str-reports/import-xml", {
    method: "POST",
    headers: { "Content-Type": contentType },
    body: bodyBuffer,
  });
  const payload = await readResponsePayload<unknown>(response);
  return NextResponse.json(payload, { status: response.status });
}
