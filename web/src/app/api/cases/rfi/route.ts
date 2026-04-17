import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";
import { normalizeCaseWorkspace } from "@/lib/cases";

export async function POST(request: NextRequest) {
  const body = await request.json();
  const response = await proxyEngineRequest("/cases/rfi", {
    method: "POST",
    body: JSON.stringify({
      title: body.title,
      summary: body.summary,
      requested_from: body.requestedFrom,
      parent_case_id: body.parentCaseId ?? null,
      linked_alert_ids: body.linkedAlertIds ?? [],
      linked_entity_ids: body.linkedEntityIds ?? [],
    }),
  });
  const payload = await readResponsePayload<{ case: unknown }>(response);
  if (!response.ok) {
    return NextResponse.json(payload, { status: response.status });
  }
  const success = payload as { case: unknown };
  return NextResponse.json(
    { case: normalizeCaseWorkspace(success.case as never) },
    { status: response.status },
  );
}
