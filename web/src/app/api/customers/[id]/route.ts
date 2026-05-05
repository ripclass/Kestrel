import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";

export async function GET(_: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const response = await proxyEngineRequest(`/customers/${encodeURIComponent(id)}`);
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load customer.") },
      { status: response.status },
    );
  }
  return NextResponse.json(payload, { status: response.status });
}

export async function PATCH(request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const body = await request.text();
  const response = await proxyEngineRequest(`/customers/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: body || "{}",
    headers: { "Content-Type": "application/json" },
  });
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to update customer.") },
      { status: response.status },
    );
  }
  return NextResponse.json(payload, { status: response.status });
}
