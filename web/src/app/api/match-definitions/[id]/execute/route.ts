import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";
import { normalizeMatchDefinitionDetail, normalizeMatchExecution } from "@/lib/intel";

type RouteContext = { params: Promise<{ id: string }> };

export async function POST(_request: NextRequest, context: RouteContext) {
  const { id } = await context.params;
  const response = await proxyEngineRequest(`/match-definitions/${id}/execute`, {
    method: "POST",
  });
  const payload = await readResponsePayload<{ execution: unknown; match_definition: unknown }>(response);
  if (!response.ok) return NextResponse.json(payload, { status: response.status });
  const success = payload as { execution: unknown; match_definition: unknown };
  return NextResponse.json(
    {
      execution: normalizeMatchExecution(success.execution as never),
      matchDefinition: normalizeMatchDefinitionDetail(success.match_definition as never),
    },
    { status: response.status },
  );
}
