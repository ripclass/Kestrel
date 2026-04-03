import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import { normalizeSyntheticBackfillPlan, normalizeSyntheticBackfillResult } from "@/lib/admin";

export async function GET() {
  const response = await proxyEngineRequest("/admin/synthetic-backfill");
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load synthetic backfill plan.") },
      { status: response.status },
    );
  }

  return NextResponse.json(
    { plan: normalizeSyntheticBackfillPlan(payload as never) },
    { status: response.status },
  );
}

export async function POST() {
  const response = await proxyEngineRequest("/admin/synthetic-backfill", {
    method: "POST",
  });
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to run synthetic backfill.") },
      { status: response.status },
    );
  }

  return NextResponse.json(
    { result: normalizeSyntheticBackfillResult(payload as never) },
    { status: response.status },
  );
}
