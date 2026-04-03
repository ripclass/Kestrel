import { PageFrame } from "@/components/common/page-frame";
import { ScanHistoryTable } from "@/components/scan/scan-history-table";

export default function ScanHistoryPage() {
  return (
    <PageFrame
      eyebrow="Detection history"
      title="Past scans"
      description="Track the lifecycle of uploaded runs, generated alerts, and downstream case conversion."
    >
      <ScanHistoryTable />
    </PageFrame>
  );
}
