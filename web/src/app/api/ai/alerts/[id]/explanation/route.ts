import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";

type RouteContext = {
  params: Promise<{ id: string }>;
};

export async function POST(_request: Request, { params }: RouteContext) {
  const { id } = await params;
  const response = await proxyEngineRequest(`/ai/alerts/${id}/explanation`, {
    method: "POST",
  });
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(payload, { status: response.status });
  }

  const envelope = payload as {
    meta: Record<string, unknown>;
    result: { summary: string; why_it_matters: string; recommended_actions: string[] };
  };

  return NextResponse.json({
    meta: {
      task: envelope.meta.task,
      provider: envelope.meta.provider,
      model: envelope.meta.model,
      fallbackUsed: envelope.meta.fallback_used,
    },
    result: {
      summary: envelope.result.summary,
      whyItMatters: envelope.result.why_it_matters,
      recommendedActions: envelope.result.recommended_actions,
    },
  });
}
