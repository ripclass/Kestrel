import { NextRequest, NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";
import { normalizeIERDetail } from "@/lib/iers";

export async function POST(request: NextRequest) {
  const body = await request.json();
  const response = await proxyEngineRequest("/iers/outbound", {
    method: "POST",
    body: JSON.stringify({
      counterparty_fiu: body.counterpartyFiu,
      counterparty_country: body.counterpartyCountry ?? null,
      request_narrative: body.requestNarrative,
      egmont_ref: body.egmontRef ?? null,
      deadline: body.deadline ?? null,
      linked_entity_ids: body.linkedEntityIds ?? [],
    }),
  });
  const payload = await readResponsePayload<{ ier: unknown }>(response);
  if (!response.ok) return NextResponse.json(payload, { status: response.status });
  const success = payload as { ier: unknown };
  return NextResponse.json(
    { ier: normalizeIERDetail(success.ier as never) },
    { status: response.status },
  );
}
