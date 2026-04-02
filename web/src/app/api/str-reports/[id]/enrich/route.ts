import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";
import { normalizeSTRReportDetail } from "@/lib/str-reports";

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function POST(_request: NextRequest, context: RouteContext) {
  const { id } = await context.params;
  const response = await proxyEngineRequest(`/str-reports/${id}/enrich`, {
    method: "POST",
  });
  const payload = await readResponsePayload<{ report: unknown }>(response);
  if (!response.ok) {
    return NextResponse.json(payload, { status: response.status });
  }
  const successPayload = payload as { report: unknown };
  const report = normalizeSTRReportDetail(successPayload.report as never);
  return NextResponse.json(
    {
      report,
      enrichment: report.enrichment,
    },
    { status: response.status },
  );
}
