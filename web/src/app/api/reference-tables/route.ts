import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";
import {
  normalizeReferenceEntry,
  normalizeReferenceEntryList,
} from "@/lib/admin-intel";

export async function GET(request: NextRequest) {
  const response = await proxyEngineRequest(`/reference-tables${request.nextUrl.search}`);
  const payload = await readResponsePayload<{ entries?: unknown[] }>(response);
  if (!response.ok) return NextResponse.json(payload, { status: response.status });
  const success = payload as { entries?: unknown[] };
  return NextResponse.json(
    { entries: normalizeReferenceEntryList((success.entries ?? []) as never) },
    { status: response.status },
  );
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const response = await proxyEngineRequest("/reference-tables", {
    method: "POST",
    body: JSON.stringify({
      table_name: body.tableName,
      code: body.code,
      value: body.value,
      description: body.description ?? null,
      parent_code: body.parentCode ?? null,
      metadata: body.metadata ?? {},
      is_active: body.isActive ?? true,
    }),
  });
  const payload = await readResponsePayload<{ entry: unknown }>(response);
  if (!response.ok) return NextResponse.json(payload, { status: response.status });
  const success = payload as { entry: unknown };
  return NextResponse.json(
    { entry: normalizeReferenceEntry(success.entry as never) },
    { status: response.status },
  );
}
