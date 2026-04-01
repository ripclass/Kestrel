import { PageFrame } from "@/components/common/page-frame";
import { NationalDashboard } from "@/components/reports/national-dashboard";

export default function NationalReportPage() {
  return (
    <PageFrame
      eyebrow="Layer 3"
      title="National threat dashboard"
      description="Director-level command view of typologies, exploited channels, and institutions requiring attention."
    >
      <NationalDashboard />
    </PageFrame>
  );
}
