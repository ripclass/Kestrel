import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { ReportExportPayload } from "@/types/api";

export async function POST(request: Request) {
  const body = (await request.json()) as ReportExportPayload;
  const reportType = body.reportType || "national";
  const response = await proxyEngineRequest(
    `/reports/export?report_type=${encodeURIComponent(reportType)}`,
    { method: "POST" },
  );

  // Engine streams PDF bytes; preserve them for the browser. JSON only on error.
  if (!response.ok) {
    const payload = await readResponsePayload<unknown>(response);
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to generate export.") },
      { status: response.status },
    );
  }

  const bytes = await response.arrayBuffer();
  const disposition =
    response.headers.get("content-disposition") ??
    `attachment; filename="kestrel-${reportType}-pack.pdf"`;
  return new NextResponse(bytes, {
    status: response.status,
    headers: {
      "Content-Type": response.headers.get("content-type") ?? "application/pdf",
      "Content-Disposition": disposition,
      "Cache-Control": "no-store",
    },
  });
}
