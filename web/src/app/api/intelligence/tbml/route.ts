import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const target = `/intelligence/tbml/summary${url.search}`;
  const response = await proxyEngineRequest(target);
  const payload = await readResponsePayload<unknown>(response);
  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load TBML summary.") },
      { status: response.status },
    );
  }
  return NextResponse.json(payload, { status: response.status });
}
