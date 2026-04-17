import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";
import {
  normalizeMatchDefinitionDetail,
  normalizeMatchDefinitionList,
} from "@/lib/intel";

export async function GET(request: NextRequest) {
  const response = await proxyEngineRequest(`/match-definitions${request.nextUrl.search}`);
  const payload = await readResponsePayload<{ match_definitions?: unknown[] }>(response);
  if (!response.ok) return NextResponse.json(payload, { status: response.status });
  const success = payload as { match_definitions?: unknown[] };
  return NextResponse.json(
    { matchDefinitions: normalizeMatchDefinitionList((success.match_definitions ?? []) as never) },
    { status: response.status },
  );
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const response = await proxyEngineRequest("/match-definitions", {
    method: "POST",
    body: JSON.stringify({
      name: body.name,
      description: body.description ?? null,
      definition: body.definition ?? {},
      is_active: body.isActive ?? true,
    }),
  });
  const payload = await readResponsePayload<{ match_definition: unknown }>(response);
  if (!response.ok) return NextResponse.json(payload, { status: response.status });
  const success = payload as { match_definition: unknown };
  return NextResponse.json(
    { matchDefinition: normalizeMatchDefinitionDetail(success.match_definition as never) },
    { status: response.status },
  );
}
