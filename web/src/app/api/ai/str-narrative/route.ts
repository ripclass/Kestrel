import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";

export async function POST(request: NextRequest) {
  const body = await request.json();

  const response = await proxyEngineRequest("/ai/str-narrative", {
    method: "POST",
    body: JSON.stringify({
      subject_name: body.subjectName ?? null,
      subject_account: body.subjectAccount ?? null,
      total_amount: body.totalAmount ?? null,
      category: body.category ?? null,
      trigger_facts: body.triggerFacts ?? [],
    }),
  });
  const payload = await readResponsePayload<unknown>(response);

  if (!response.ok) {
    return NextResponse.json(payload, { status: response.status });
  }

  const envelope = payload as {
    meta: Record<string, unknown>;
    result: {
      narrative: string;
      missing_fields: string[];
      category_suggestion: string;
      severity_suggestion: string;
    };
  };

  return NextResponse.json({
    meta: {
      task: envelope.meta.task,
      provider: envelope.meta.provider,
      model: envelope.meta.model,
      fallbackUsed: envelope.meta.fallback_used,
    },
    result: {
      narrative: envelope.result.narrative,
      missingFields: envelope.result.missing_fields,
      categorySuggestion: envelope.result.category_suggestion,
      severitySuggestion: envelope.result.severity_suggestion,
    },
  });
}
