import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { normalizeSTRReportDetail } from "@/lib/str-reports";

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function POST(_request: NextRequest, context: RouteContext) {
  const { id } = await context.params;
  const response = await proxyEngineRequest(`/str-reports/${id}/enrich`, {
    method: "POST",
  });
  const payload = await response.json();
  if (!response.ok) {
    return NextResponse.json(payload, { status: response.status });
  }
  return NextResponse.json(
    {
      report: normalizeSTRReportDetail(payload.report),
      enrichment: normalizeSTRReportDetail(payload.report).enrichment,
    },
    { status: response.status },
  );
}
