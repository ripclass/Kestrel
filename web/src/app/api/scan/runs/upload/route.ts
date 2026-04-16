import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";
import { normalizeDetectionRunDetail } from "@/lib/scan";

export async function POST(request: NextRequest) {
  // Stream the incoming multipart body through to the engine, preserving the
  // boundary. We can't rebuild the FormData on the server side because
  // Next.js would need to re-encode it; forwarding the raw body + content-type
  // is cleaner and preserves the file bytes.
  const contentType = request.headers.get("content-type") ?? "";
  const bodyBuffer = await request.arrayBuffer();

  const response = await proxyEngineRequest("/scan/runs/upload", {
    method: "POST",
    headers: { "Content-Type": contentType },
    body: bodyBuffer,
  });

  const payload = await readResponsePayload<{ run?: unknown; message?: string }>(response);
  if (!response.ok) {
    return NextResponse.json(payload, { status: response.status });
  }

  const successPayload = payload as { run: unknown; message: string };
  return NextResponse.json(
    {
      run: normalizeDetectionRunDetail(successPayload.run as never),
      message: successPayload.message,
    },
    { status: response.status },
  );
}
