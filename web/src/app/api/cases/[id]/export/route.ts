import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function GET(_request: Request, { params }: RouteContext) {
  const { id } = await params;
  const response = await proxyEngineRequest(`/cases/${id}/export.pdf`);

  if (!response.ok) {
    const detail = await response.text();
    return NextResponse.json(
      { detail: detail || "PDF export failed." },
      { status: response.status },
    );
  }

  // Stream the PDF bytes back to the browser with the Content-Disposition header
  const body = await response.arrayBuffer();
  return new NextResponse(body, {
    status: 200,
    headers: {
      "Content-Type": "application/pdf",
      "Content-Disposition": response.headers.get("Content-Disposition") ?? `attachment; filename="case-${id}.pdf"`,
    },
  });
}
