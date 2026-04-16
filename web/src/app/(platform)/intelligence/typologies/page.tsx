import { PageFrame } from "@/components/common/page-frame";
import { TypologyCard } from "@/components/intelligence/typology-card";
import { EmptyState } from "@/components/common/empty-state";
import { proxyEngineRequest } from "@/lib/engine-server";
import { readResponsePayload } from "@/lib/http";
import type { TypologySummary } from "@/types/domain";

type RawTypology = {
  id: string;
  title: string;
  category: string;
  channels: string[];
  indicators: string[];
  narrative: string;
};

async function fetchTypologies(): Promise<TypologySummary[]> {
  try {
    const response = await proxyEngineRequest("/intelligence/typologies");
    if (!response.ok) return [];
    const payload = (await readResponsePayload<RawTypology[]>(response)) as RawTypology[];
    return payload.map((row) => ({
      id: row.id,
      title: row.title,
      category: row.category,
      channels: row.channels ?? [],
      indicators: row.indicators ?? [],
      narrative: row.narrative,
    }));
  } catch {
    return [];
  }
}

export default async function TypologiesPage() {
  const typologies = await fetchTypologies();

  return (
    <PageFrame
      eyebrow="Typology library"
      title="Known scam typologies"
      description="Reusable patterns and indicators that guide both bank operations and regulator case development."
    >
      {typologies.length === 0 ? (
        <EmptyState
          title="No typologies available"
          description="The typology library is empty or the intelligence service is unreachable."
        />
      ) : (
        <div className="grid gap-6 lg:grid-cols-2">
          {typologies.map((typology) => (
            <TypologyCard key={typology.id} typology={typology} />
          ))}
        </div>
      )}
    </PageFrame>
  );
}
