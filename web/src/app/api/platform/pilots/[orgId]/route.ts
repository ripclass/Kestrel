import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";

export async function GET(
  _request: Request,
  context: { params: Promise<{ orgId: string }> },
) {
  const { orgId } = await context.params;
  const response = await proxyEngineRequest(
    `/platform/pilots/${encodeURIComponent(orgId)}`,
  );
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load tenant detail.") },
      { status: response.status },
    );
  }
  return NextResponse.json(payload, { status: response.status });
}
