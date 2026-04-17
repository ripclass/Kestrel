import { DisseminationWorkspace } from "@/components/disseminations/dissemination-workspace";
import { PageFrame } from "@/components/common/page-frame";
import { requireViewer } from "@/lib/auth";

type PageProps = {
  params: Promise<{ id: string }>;
};

export default async function DisseminationDetailPage({ params }: PageProps) {
  await requireViewer();
  const { id } = await params;
  return (
    <PageFrame
      eyebrow="Dissemination"
      title="Handoff record"
      description="Full context for a single intelligence dissemination, including the reports, entities, and cases that travelled with the packet."
    >
      <DisseminationWorkspace disseminationId={id} />
    </PageFrame>
  );
}
