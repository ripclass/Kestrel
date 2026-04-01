import { PageFrame } from "@/components/common/page-frame";
import { ReportBuilder } from "@/components/reports/report-builder";

export default function ExportPage() {
  return (
    <PageFrame
      eyebrow="Layer 3"
      title="Export center"
      description="Prepare PDF and spreadsheet packs for BFIU leadership, bank follow-up, or mutual evaluation briefings."
    >
      <ReportBuilder />
    </PageFrame>
  );
}
