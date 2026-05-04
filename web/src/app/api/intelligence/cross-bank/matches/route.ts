import { NextResponse } from "next/server";

import { normalizeMatchView } from "@/lib/cross-bank";
import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const params = new URLSearchParams();
  for (const key of ["window_days", "severity", "min_banks", "limit"]) {
    const v = url.searchParams.get(key);
    if (v !== null) params.set(key, v);
  }
  const qs = params.toString() ? `?${params.toString()}` : "";

  const response = await proxyEngineRequest(`/intelligence/cross-bank/matches${qs}`);
  const payload = await readResponsePayload<unknown[]>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load cross-bank matches.") },
      { status: response.status },
    );
  }

  return NextResponse.json(
    { matches: ((payload as unknown[]) ?? []).map((item) => normalizeMatchView(item as never)) },
    { status: response.status },
  );
}
