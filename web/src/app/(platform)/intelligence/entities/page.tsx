import { PageFrame } from "@/components/common/page-frame";
import { EntityTable } from "@/components/intelligence/entity-table";

export default function IntelligenceEntitiesPage() {
  return (
    <PageFrame
      eyebrow="Shared intelligence"
      title="Flagged entity database"
      description="Browsable, role-aware view of shared entities that sit above any single institution."
    >
      <EntityTable />
    </PageFrame>
  );
}
