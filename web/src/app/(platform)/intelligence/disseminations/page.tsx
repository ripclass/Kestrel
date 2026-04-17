import { PageFrame } from "@/components/common/page-frame";
import { DisseminationList } from "@/components/disseminations/dissemination-list";
import { requireViewer } from "@/lib/auth";

export default async function DisseminationsPage() {
  const viewer = await requireViewer();

  return (
    <PageFrame
      eyebrow="Outbound intelligence"
      title="Disseminations"
      description="Every intelligence packet handed off to law enforcement, regulators, or foreign FIUs is recorded here with recipient, classification, and the underlying reports that travelled with it."
    >
      <DisseminationList viewer={viewer} />
    </PageFrame>
  );
}
