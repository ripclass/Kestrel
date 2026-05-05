import { PageFrame } from "@/components/common/page-frame";
import { RealtimeMonitoringDashboard } from "@/components/monitoring/realtime-dashboard";
import { requireViewer } from "@/lib/auth";

export default async function RealtimeMonitoringPage() {
  const viewer = await requireViewer();

  return (
    <PageFrame
      eyebrow="Real-time monitoring"
      title="Per-transaction decisioning, live"
      description="Every call to POST /transactions/score lands here. Decision distribution, latency p50/p95/p99, top scored transactions in the last hour, and cross-bank flags. Bank persona sees its own institution; regulator persona sees the system aggregate."
    >
      <RealtimeMonitoringDashboard viewer={viewer} />
    </PageFrame>
  );
}
