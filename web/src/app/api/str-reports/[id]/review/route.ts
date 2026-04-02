import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { normalizeSTRReportDetail } from "@/lib/str-reports";

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function POST(request: NextRequest, context: RouteContext) {
  const { id } = await context.params;
  const body = await request.json();
  const response = await proxyEngineRequest(`/str-reports/${id}/review`, {
    method: "POST",
    body: JSON.stringify({
      action: body.action,
      note: body.note,
      assigned_to: body.assignedTo,
    }),
  });
  const payload = await response.json();
  if (!response.ok) {
    return NextResponse.json(payload, { status: response.status });
  }
  return NextResponse.json({ report: normalizeSTRReportDetail(payload.report) }, { status: response.status });
}
