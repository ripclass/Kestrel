import { PageFrame } from "@/components/common/page-frame";
import { OperationalStatisticsDashboard } from "@/components/reports/operational-statistics";
import { requireViewer } from "@/lib/auth";

export default async function OperationalStatisticsPage() {
  await requireViewer();
  return (
    <PageFrame
      eyebrow="Command"
      title="Operational statistics"
      description="goAML-shape summary views over reports, CTRs, cases, and disseminations — regulator-scoped."
    >
      <OperationalStatisticsDashboard />
    </PageFrame>
  );
}
