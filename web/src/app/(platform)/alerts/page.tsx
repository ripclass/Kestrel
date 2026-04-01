import { AlertQueue } from "@/components/alerts/alert-queue";
import { PageFrame } from "@/components/common/page-frame";

export default function AlertsPage() {
  return (
    <PageFrame
      eyebrow="Alert management"
      title="Alert queue"
      description="Prioritized triage with explainability, entity context, and direct handoff into case workflows."
    >
      <AlertQueue />
    </PageFrame>
  );
}
