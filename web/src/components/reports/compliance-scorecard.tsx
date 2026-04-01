import { DataTable } from "@/components/common/data-table";
import { complianceScores } from "@/lib/demo";

export function ComplianceScorecard() {
  return (
    <DataTable
      columns={["Bank", "Timeliness", "Conversion", "Coverage", "Score"]}
      rows={complianceScores.map((bank) => [
        bank.orgName,
        `${bank.submissionTimeliness}`,
        `${bank.alertConversion}`,
        `${bank.peerCoverage}`,
        `${bank.score}`,
      ])}
    />
  );
}
