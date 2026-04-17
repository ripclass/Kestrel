import { PageFrame } from "@/components/common/page-frame";
import { IERWorkspace } from "@/components/iers/ier-workspace";
import { requireViewer } from "@/lib/auth";

type PageProps = { params: Promise<{ id: string }> };

export default async function IERDetailPage({ params }: PageProps) {
  await requireViewer();
  const { id } = await params;
  return (
    <PageFrame
      eyebrow="IER"
      title="Exchange record"
      description="Counterparty FIU, direction, deadline, narratives, and the linked entities that travelled with the exchange."
    >
      <IERWorkspace ierId={id} />
    </PageFrame>
  );
}
