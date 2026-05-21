import { PageFrame } from "@/components/common/page-frame";
import { SystemHealthPanel } from "@/components/operator/system-health-panel";
import { requirePlatformOperator } from "@/lib/auth";

export default async function SystemHealthPage() {
  await requirePlatformOperator();
  return (
    <PageFrame
      eyebrow="Operator · System health"
      title="System health"
      description="Live component probes — auth, database, Redis, storage, worker, AI — plus 30-day uptime and any active incidents. The same readiness signal that drives the public status page, in one operator pane."
    >
      <SystemHealthPanel />
    </PageFrame>
  );
}
