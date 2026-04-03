import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import { normalizeReportExportResponse } from "@/lib/reports";
import type { ReportExportPayload } from "@/types/api";

export async function POST(request: Request) {
  const body = (await request.json()) as ReportExportPayload;
  const reportType = body.reportType || "national";
  const response = await proxyEngineRequest(
    `/reports/export?report_type=${encodeURIComponent(reportType)}`,
    { method: "POST" },
  );
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to queue export.") },
      { status: response.status },
    );
  }

  return NextResponse.json(normalizeReportExportResponse(payload as never), { status: response.status });
}
