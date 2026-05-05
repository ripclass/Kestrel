import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";

export async function POST(request: Request) {
  const body = await request.text();
  const response = await proxyEngineRequest(`/agents/investigate`, {
    method: "POST",
    body: body || "{}",
    headers: { "Content-Type": "application/json" },
  });
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to run investigation.") },
      { status: response.status },
    );
  }
  return NextResponse.json(payload, { status: response.status });
}
