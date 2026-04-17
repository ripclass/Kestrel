import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";

export async function GET() {
  const response = await proxyEngineRequest("/alerts/export.xlsx");
  if (!response.ok) {
    const detail = await response.text();
    return NextResponse.json({ detail: detail || "Export failed." }, { status: response.status });
  }
  const body = await response.arrayBuffer();
  return new NextResponse(body, {
    status: 200,
    headers: {
      "Content-Type":
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "Content-Disposition":
        response.headers.get("Content-Disposition") ?? 'attachment; filename="kestrel-alerts.xlsx"',
    },
  });
}
