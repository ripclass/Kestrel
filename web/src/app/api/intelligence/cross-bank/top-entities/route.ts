import { NextResponse } from "next/server";

import { normalizeEntityRow } from "@/lib/cross-bank";
import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const params = new URLSearchParams();
  for (const key of ["window_days", "limit"]) {
    const v = url.searchParams.get(key);
    if (v !== null) params.set(key, v);
  }
  const qs = params.toString() ? `?${params.toString()}` : "";

  const response = await proxyEngineRequest(`/intelligence/cross-bank/top-entities${qs}`);
  const payload = await readResponsePayload<unknown[]>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load top cross-bank entities.") },
      { status: response.status },
    );
  }

  return NextResponse.json(
    { entities: ((payload as unknown[]) ?? []).map((item) => normalizeEntityRow(item as never)) },
    { status: response.status },
  );
}
