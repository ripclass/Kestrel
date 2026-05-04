import { PageFrame } from "@/components/common/page-frame";
import { CrossBankDashboard } from "@/components/intel/cross-bank-dashboard";
import { requireViewer } from "@/lib/auth";

export default async function CrossBankIntelligencePage() {
  const viewer = await requireViewer();

  return (
    <PageFrame
      eyebrow="Cross-bank intelligence"
      title="The signal no other vendor has"
      description="Every entity reported by two or more institutions surfaces here. Bank persona sees own-bank reports plus anonymised peer counts. Regulator persona sees the full picture across the banking system."
    >
      <CrossBankDashboard viewer={viewer} />
    </PageFrame>
  );
}
