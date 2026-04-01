import { PageFrame } from "@/components/common/page-frame";
import { TrendCharts } from "@/components/reports/trend-charts";

export default function TrendsPage() {
  return (
    <PageFrame
      eyebrow="Layer 3"
      title="Trend analysis"
      description="Monitor typology growth, reporting cycles, and network-driven alert momentum over time."
    >
      <TrendCharts />
    </PageFrame>
  );
}
