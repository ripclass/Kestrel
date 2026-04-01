import { PageFrame } from "@/components/common/page-frame";
import { EntityDossier } from "@/components/investigate/entity-dossier";
import { getEntityDossier } from "@/lib/demo";

export default async function EntityPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const dossier = getEntityDossier(id);

  return (
    <PageFrame
      eyebrow="Entity dossier"
      title={dossier.displayValue}
      description={dossier.narrative}
    >
      <EntityDossier entity={dossier} />
    </PageFrame>
  );
}
