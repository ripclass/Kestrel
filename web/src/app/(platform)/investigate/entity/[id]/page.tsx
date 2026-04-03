import { notFound } from "next/navigation";

import { PageFrame } from "@/components/common/page-frame";
import { EntityDossier } from "@/components/investigate/entity-dossier";
import { fetchEntityDossier } from "@/lib/investigation";

export default async function EntityPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const dossier = await fetchEntityDossier(id);

  if (!dossier) {
    notFound();
  }

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
