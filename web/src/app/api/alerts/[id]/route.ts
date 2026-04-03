import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import { normalizeAlertDetail } from "@/lib/alerts";

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function GET(_request: Request, { params }: RouteContext) {
  const { id } = await params;
  const response = await proxyEngineRequest(`/alerts/${id}`);
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load alert.") },
      { status: response.status },
    );
  }

  return NextResponse.json(
    { alert: normalizeAlertDetail(payload as never) },
    { status: response.status },
  );
}
