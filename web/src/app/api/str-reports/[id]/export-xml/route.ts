import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";

type RouteContext = { params: Promise<{ id: string }> };

export async function GET(_request: NextRequest, context: RouteContext) {
  const { id } = await context.params;
  const response = await proxyEngineRequest(`/str-reports/${id}/export.xml`);
  if (!response.ok) {
    const detail = await response.text();
    return NextResponse.json({ detail: detail || "XML export failed." }, { status: response.status });
  }
  const body = await response.arrayBuffer();
  return new NextResponse(body, {
    status: 200,
    headers: {
      "Content-Type": "application/xml",
      "Content-Disposition":
        response.headers.get("Content-Disposition") ?? `attachment; filename="str-${id}.xml"`,
    },
  });
}
