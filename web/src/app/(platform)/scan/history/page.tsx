import { PageFrame } from "@/components/common/page-frame";
import { DataTable } from "@/components/common/data-table";
import { detectionRuns } from "@/lib/demo";

export default function ScanHistoryPage() {
  return (
    <PageFrame
      eyebrow="Detection history"
      title="Past scans"
      description="Track the lifecycle of uploaded runs, generated alerts, and downstream case conversion."
    >
      <DataTable
        columns={["File", "Status", "Accounts", "Alerts", "Transactions"]}
        rows={detectionRuns.map((run) => [
          run.fileName,
          run.status,
          `${run.accountsScanned}`,
          `${run.alertsGenerated}`,
          `${run.txCount}`,
        ])}
      />
    </PageFrame>
  );
}
