import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";

export async function GET(
  _request: Request,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  const response = await proxyEngineRequest(`/trade/${id}`);
  const payload = await readResponsePayload<unknown>(response);
  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load trade transaction.") },
      { status: response.status },
    );
  }
  return NextResponse.json(payload, { status: response.status });
}
