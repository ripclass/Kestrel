import { PageFrame } from "@/components/common/page-frame";
import { STRReportWorkspace } from "@/components/str-reports/str-report-workspace";
import { requireViewer } from "@/lib/auth";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function STRReportDetailPage({ params }: PageProps) {
  const viewer = await requireViewer();
  const { id } = await params;

  return (
    <PageFrame
      eyebrow="Phase 4"
      title="STR workspace"
      description="Drafting, enrichment, submission, and regulator review are now handled as a first-class Kestrel workflow."
    >
      <STRReportWorkspace reportId={id} viewer={viewer} />
    </PageFrame>
  );
}
