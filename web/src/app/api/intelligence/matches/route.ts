import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import { normalizeMatchSummary } from "@/lib/investigation";

export async function GET() {
  const response = await proxyEngineRequest("/intelligence/matches");
  const payload = await readResponsePayload<unknown[]>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load cross-bank matches.") },
      { status: response.status },
    );
  }

  return NextResponse.json(
    { matches: ((payload as unknown[]) ?? []).map((item) => normalizeMatchSummary(item as never)) },
    { status: response.status },
  );
}
