import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ task_id: string }> },
) {
  const { task_id } = await params;
  const response = await proxyEngineRequest(
    `/admin/screening/refresh-status/${encodeURIComponent(task_id)}`,
  );
  const payload = await readResponsePayload<unknown>(response);
  return NextResponse.json(payload, { status: response.status });
}
