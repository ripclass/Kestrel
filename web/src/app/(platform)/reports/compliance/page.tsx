import { PageFrame } from "@/components/common/page-frame";
import { ComplianceScorecard } from "@/components/reports/compliance-scorecard";

export default function CompliancePage() {
  return (
    <PageFrame
      eyebrow="Layer 3"
      title="Compliance scorecard"
      description="Track peer reporting posture, submission quality, and relative readiness for regulator review."
    >
      <ComplianceScorecard />
    </PageFrame>
  );
}
