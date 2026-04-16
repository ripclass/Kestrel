import { NextResponse } from "next/server";

import { proxyEngineRequest } from "@/lib/engine-server";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { TypologySummary } from "@/types/domain";

type RawTypology = {
  id: string;
  title: string;
  category: string;
  channels: string[];
  indicators: string[];
  narrative: string;
};

function normalize(row: RawTypology): TypologySummary {
  return {
    id: row.id,
    title: row.title,
    category: row.category,
    channels: row.channels ?? [],
    indicators: row.indicators ?? [],
    narrative: row.narrative,
  };
}

export async function GET() {
  const response = await proxyEngineRequest("/intelligence/typologies");
  const payload = await readResponsePayload<unknown[]>(response);

  if (!response.ok) {
    return NextResponse.json(
      { detail: detailFromPayload(payload, "Unable to load typologies.") },
      { status: response.status },
    );
  }

  return NextResponse.json(
    { typologies: ((payload as unknown[]) ?? []).map((item) => normalize(item as never)) },
    { status: response.status },
  );
}
