import { PageFrame } from "@/components/common/page-frame";
import { TypologyCard } from "@/components/intelligence/typology-card";
import { typologies } from "@/lib/demo";

export default function TypologiesPage() {
  return (
    <PageFrame
      eyebrow="Typology library"
      title="Known scam typologies"
      description="Reusable patterns and indicators that guide both bank operations and regulator case development."
    >
      <div className="grid gap-6 lg:grid-cols-2">
        {typologies.map((typology) => (
          <TypologyCard key={typology.id} typology={typology} />
        ))}
      </div>
    </PageFrame>
  );
}
