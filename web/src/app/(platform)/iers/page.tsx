import { PageFrame } from "@/components/common/page-frame";
import { IERList } from "@/components/iers/ier-list";
import { requireViewer } from "@/lib/auth";

export default async function IERPage() {
  await requireViewer();
  return (
    <PageFrame
      eyebrow="Information Exchange Request (goAML)"
      title="Exchange"
      description="Outbound requests BFIU sends to foreign FIUs through the Egmont Group, and inbound requests BFIU receives. Every exchange is recorded in the shared audit trail."
    >
      <IERList />
    </PageFrame>
  );
}
