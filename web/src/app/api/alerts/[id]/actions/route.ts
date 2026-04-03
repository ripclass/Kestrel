import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import { normalizeAlertDetail } from "@/lib/alerts";
import { normalizeCaseSummary } from "@/lib/cases";
import type { AlertMutationPayload } from "@/types/api";

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function POST(request: Request, { params }: RouteContext) {
  const { id } = await params;
  const body = (await request.json()) as AlertMutationPayload;
  const response = await proxyEngineRequest(`/alerts/${id}/actions`, {
    method: "POST",
    body: JSON.stringify({
      action: body.action,
      note: body.note,
      case_title: body.caseTitle,
    }),
  });
  const payload = await readResponsePayload<{ alert: unknown; case?: unknown | null }>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to update alert.") },
      { status: response.status },
    );
  }

  return NextResponse.json(
    {
      alert: normalizeAlertDetail((payload as { alert: unknown }).alert as never),
      case: (payload as { case?: unknown | null }).case
        ? normalizeCaseSummary((payload as { case: unknown }).case as never)
        : null,
    },
    { status: response.status },
  );
}
