import { AlertDetail } from "@/components/alerts/alert-detail";
import { PageFrame } from "@/components/common/page-frame";

export default async function AlertPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return (
    <PageFrame
      eyebrow="Alert detail"
      title="Alert workspace"
      description="Review explainability, assign ownership, disposition the alert, and escalate into a linked case."
    >
      <AlertDetail alertId={id} />
    </PageFrame>
  );
}
