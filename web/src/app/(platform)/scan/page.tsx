import { PageFrame } from "@/components/common/page-frame";
import { ScanWorkbench } from "@/components/scan/scan-workbench";

export default function ScanPage() {
  return (
    <PageFrame
      eyebrow="Layer 1B"
      title="Pattern scanning"
      description="Bank users upload raw transaction data, run the detection pipeline, and review accounts most likely to become STR candidates."
    >
      <ScanWorkbench />
    </PageFrame>
  );
}
