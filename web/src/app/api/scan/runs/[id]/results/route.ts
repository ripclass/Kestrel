import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import { normalizeFlaggedAccount } from "@/lib/scan";

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function GET(_request: Request, { params }: RouteContext) {
  const { id } = await params;
  const response = await proxyEngineRequest(`/scan/runs/${id}/results`);
  const payload = await readResponsePayload<unknown[]>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load detection results.") },
      { status: response.status },
    );
  }

  return NextResponse.json(
    { results: ((payload as unknown[]) ?? []).map((item) => normalizeFlaggedAccount(item as never)) },
    { status: response.status },
  );
}
