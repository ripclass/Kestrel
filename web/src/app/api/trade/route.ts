import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const target = `/trade${url.search}`;
  const response = await proxyEngineRequest(target);
  const payload = await readResponsePayload<unknown>(response);
  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load trade transactions.") },
      { status: response.status },
    );
  }
  return NextResponse.json(payload, { status: response.status });
}

export async function POST(request: Request) {
  const body = await request.text();
  const response = await proxyEngineRequest("/trade", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });
  const payload = await readResponsePayload<unknown>(response);
  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to create trade transaction.") },
      { status: response.status },
    );
  }
  return NextResponse.json(payload, { status: response.status });
}
