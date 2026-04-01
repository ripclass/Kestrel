import { PageFrame } from "@/components/common/page-frame";
import { NetworkCanvas } from "@/components/investigate/network-canvas";
import { getEntityDossier } from "@/lib/demo";

export default async function NetworkPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const dossier = getEntityDossier(id);

  return (
    <PageFrame
      eyebrow="Network explorer"
      title={`Graph for ${dossier.displayValue}`}
      description="Reusable React Flow surface embedded across dossiers, alerts, and cases."
    >
      <NetworkCanvas graph={dossier.graph} />
    </PageFrame>
  );
}
