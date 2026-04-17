import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";
import {
  normalizeDisseminationDetail,
  normalizeDisseminationList,
} from "@/lib/disseminations";

export async function GET(request: NextRequest) {
  const response = await proxyEngineRequest(`/disseminations${request.nextUrl.search}`);
  const payload = await readResponsePayload<{ disseminations?: unknown[] }>(response);
  if (!response.ok) {
    return NextResponse.json(payload, { status: response.status });
  }
  const success = payload as { disseminations?: unknown[] };
  return NextResponse.json(
    { disseminations: normalizeDisseminationList((success.disseminations ?? []) as never) },
    { status: response.status },
  );
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const response = await proxyEngineRequest("/disseminations", {
    method: "POST",
    body: JSON.stringify({
      recipient_agency: body.recipientAgency,
      recipient_type: body.recipientType,
      subject_summary: body.subjectSummary,
      linked_report_ids: body.linkedReportIds ?? [],
      linked_entity_ids: body.linkedEntityIds ?? [],
      linked_case_ids: body.linkedCaseIds ?? [],
      classification: body.classification ?? "confidential",
      metadata: body.metadata ?? {},
    }),
  });
  const payload = await readResponsePayload<{ dissemination: unknown }>(response);
  if (!response.ok) {
    return NextResponse.json(payload, { status: response.status });
  }
  const success = payload as { dissemination: unknown };
  return NextResponse.json(
    { dissemination: normalizeDisseminationDetail(success.dissemination as never) },
    { status: response.status },
  );
}
