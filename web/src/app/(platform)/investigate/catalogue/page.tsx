import { PageFrame } from "@/components/common/page-frame";
import { CatalogueGrid } from "@/components/investigate/catalogue-grid";
import { requireViewer } from "@/lib/auth";

export default async function CataloguePage() {
  await requireViewer();
  return (
    <PageFrame
      eyebrow="Catalogue search (goAML)"
      title="Catalogue"
      description="Labelled entry points into Kestrel's unified search. Every tile is powered by the same omnisearch index; the goAML vocabulary is preserved so analysts who know the old screens can recognise them here."
    >
      <CatalogueGrid />
    </PageFrame>
  );
}
