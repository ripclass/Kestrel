import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";
import { normalizeReferenceTableCounts } from "@/lib/admin-intel";

export async function GET() {
  const response = await proxyEngineRequest("/reference-tables/tables");
  const payload = await readResponsePayload<{ tables?: unknown[] }>(response);
  if (!response.ok) return NextResponse.json(payload, { status: response.status });
  const success = payload as { tables?: unknown[] };
  return NextResponse.json(
    { tables: normalizeReferenceTableCounts((success.tables ?? []) as never) },
    { status: response.status },
  );
}
