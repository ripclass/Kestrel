import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import { normalizeCaseSummary } from "@/lib/cases";

export async function GET() {
  const response = await proxyEngineRequest("/cases");
  const payload = await readResponsePayload<unknown[]>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load cases.") },
      { status: response.status },
    );
  }

  return NextResponse.json(
    { cases: ((payload as unknown[]) ?? []).map((item) => normalizeCaseSummary(item as never)) },
    { status: response.status },
  );
}
