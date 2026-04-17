import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";
import { normalizeSTRReportDetail, normalizeSTRReportList } from "@/lib/str-reports";

type RouteContext = { params: Promise<{ id: string }> };

export async function GET(_request: NextRequest, context: RouteContext) {
  const { id } = await context.params;
  const response = await proxyEngineRequest(`/str-reports/${id}/supplements`);
  const payload = await readResponsePayload<{ reports?: unknown[] }>(response);
  if (!response.ok) return NextResponse.json(payload, { status: response.status });
  const success = payload as { reports?: unknown[] };
  return NextResponse.json(
    { reports: normalizeSTRReportList((success.reports ?? []) as never) },
    { status: response.status },
  );
}

export async function POST(request: NextRequest, context: RouteContext) {
  const { id } = await context.params;
  const body = await request.json();
  // Report_type + supplements_report_id are set by the engine router — the
  // client only needs to forward subject / narrative / any context it knows.
  const response = await proxyEngineRequest(`/str-reports/${id}/supplements`, {
    method: "POST",
    body: JSON.stringify({
      report_type: "additional_info",
      subject_name: body.subjectName ?? null,
      subject_account: body.subjectAccount ?? null,
      subject_bank: body.subjectBank ?? null,
      total_amount: body.totalAmount ?? 0,
      currency: body.currency ?? "BDT",
      transaction_count: body.transactionCount ?? 0,
      category: body.category ?? "other",
      narrative: body.narrative ?? null,
      channels: body.channels ?? [],
      date_range_start: body.dateRangeStart || null,
      date_range_end: body.dateRangeEnd || null,
      metadata: body.metadata ?? {},
      supplements_report_id: id,
    }),
  });
  const payload = await readResponsePayload<{ report: unknown }>(response);
  if (!response.ok) return NextResponse.json(payload, { status: response.status });
  const success = payload as { report: unknown };
  return NextResponse.json(
    { report: normalizeSTRReportDetail(success.report as never) },
    { status: response.status },
  );
}
