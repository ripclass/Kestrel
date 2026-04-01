import { ActivityTimeline } from "@/components/investigate/activity-timeline";
import { getEntityDossier } from "@/lib/demo";

export function CaseTimeline() {
  return <ActivityTimeline events={getEntityDossier("ent-rizwana-account").timeline} />;
}
