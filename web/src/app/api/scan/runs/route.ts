import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import { normalizeDetectionRunDetail, normalizeDetectionRunSummary } from "@/lib/scan";
import type { ScanQueuePayload } from "@/types/api";

export async function GET() {
  const response = await proxyEngineRequest("/scan/runs");
  const payload = await readResponsePayload<unknown[]>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load scan history.") },
      { status: response.status },
    );
  }

  return NextResponse.json(
    { runs: ((payload as unknown[]) ?? []).map((item) => normalizeDetectionRunSummary(item as never)) },
    { status: response.status },
  );
}

export async function POST(request: Request) {
  const body = (await request.json()) as ScanQueuePayload;
  const response = await proxyEngineRequest("/scan/runs", {
    method: "POST",
    body: JSON.stringify({
      file_name: body.fileName,
      selected_rules: body.selectedRules,
    }),
  });
  const payload = await readResponsePayload<{ run: unknown; message: string }>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to queue detection run.") },
      { status: response.status },
    );
  }

  const result = payload as { run: unknown; message: string };
  return NextResponse.json(
    { run: normalizeDetectionRunDetail(result.run as never), message: result.message },
    { status: response.status },
  );
}
