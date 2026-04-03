import type { EntitySummary } from "@/types/domain";
import { EmptyState } from "@/components/common/empty-state";
import { EntityConnections } from "@/components/investigate/entity-connections";

export function CaseEvidence({ entities }: { entities: EntitySummary[] }) {
  if (entities.length === 0) {
    return (
      <EmptyState
        title="No linked evidence entities"
        description="This case does not yet have linked entity evidence in the graph."
      />
    );
  }

  return <EntityConnections entities={entities} />;
}
