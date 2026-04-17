import { PageFrame } from "@/components/common/page-frame";
import { IERCreateForm } from "@/components/iers/ier-create-form";
import { requireViewer } from "@/lib/auth";

export default async function NewIERPage() {
  await requireViewer();
  return (
    <PageFrame
      eyebrow="IER"
      title="Open a new exchange"
      description="Record an outbound request BFIU is sending to a foreign FIU, or log an inbound request you received."
    >
      <IERCreateForm />
    </PageFrame>
  );
}
