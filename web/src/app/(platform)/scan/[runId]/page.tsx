import { PageFrame } from "@/components/common/page-frame";
import { ScanResults } from "@/components/scan/scan-results";

export default async function ScanRunPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;

  return (
    <PageFrame
      eyebrow="Detection run"
      title={`Scan run ${runId}`}
      description="Detailed detection output, account-level scoring, and explainable alert candidates."
    >
      <ScanResults />
    </PageFrame>
  );
}
