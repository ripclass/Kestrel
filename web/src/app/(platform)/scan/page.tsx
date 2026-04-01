import { PageFrame } from "@/components/common/page-frame";
import { UploadDrop } from "@/components/scan/upload-drop";
import { ScanConfig } from "@/components/scan/scan-config";
import { ScanProgress } from "@/components/scan/scan-progress";
import { ScanResults } from "@/components/scan/scan-results";

export default function ScanPage() {
  return (
    <PageFrame
      eyebrow="Layer 1B"
      title="Pattern scanning"
      description="Bank users upload raw transaction data, run the detection pipeline, and review accounts most likely to become STR candidates."
    >
      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <div className="space-y-6">
          <UploadDrop />
          <ScanConfig />
        </div>
        <div className="space-y-6">
          <ScanProgress />
          <ScanResults />
        </div>
      </div>
    </PageFrame>
  );
}
