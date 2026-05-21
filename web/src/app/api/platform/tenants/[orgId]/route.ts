import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";

export async function PATCH(
  request: Request,
  context: { params: Promise<{ orgId: string }> },
) {
  const { orgId } = await context.params;
  const body = await request.text();
  const response = await proxyEngineRequest(
    `/platform/tenants/${encodeURIComponent(orgId)}`,
    {
      method: "PATCH",
      body: body || "{}",
      headers: { "Content-Type": "application/json" },
    },
  );
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to update tenant.") },
      { status: response.status },
    );
  }
  return NextResponse.json(payload, { status: response.status });
}
