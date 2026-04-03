import { PageFrame } from "@/components/common/page-frame";
import { EntityTable } from "@/components/intelligence/entity-table";
import { fetchSharedEntities } from "@/lib/investigation";

export default async function IntelligenceEntitiesPage() {
  const entities = await fetchSharedEntities();

  return (
    <PageFrame
      eyebrow="Shared intelligence"
      title="Flagged entity database"
      description="Browsable, role-aware view of shared entities that sit above any single institution."
    >
      <EntityTable entities={entities} />
    </PageFrame>
  );
}
