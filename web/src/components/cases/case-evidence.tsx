import { EntityConnections } from "@/components/investigate/entity-connections";
import { getEntityDossier } from "@/lib/demo";

export function CaseEvidence() {
  return <EntityConnections entities={getEntityDossier("ent-rizwana-account").connections} />;
}
