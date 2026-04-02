import { PageFrame } from "@/components/common/page-frame";
import { STRReportList } from "@/components/str-reports/str-report-list";
import { requireViewer } from "@/lib/auth";

export default async function STRReportsPage() {
  const viewer = await requireViewer();

  return (
    <PageFrame
      eyebrow="Native STR workflow"
      title="Suspicious transaction reports"
      description="Create, enrich, submit, and review STRs directly inside Kestrel without handing the core workflow off to another system."
    >
      <STRReportList viewer={viewer} />
    </PageFrame>
  );
}
