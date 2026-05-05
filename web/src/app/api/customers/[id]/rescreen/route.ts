import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";

export async function POST(_: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const response = await proxyEngineRequest(`/customers/${encodeURIComponent(id)}/rescreen`, {
    method: "POST",
    body: "{}",
    headers: { "Content-Type": "application/json" },
  });
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to rescreen customer.") },
      { status: response.status },
    );
  }
  return NextResponse.json(payload, { status: response.status });
}
