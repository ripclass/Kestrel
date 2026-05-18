import { PageFrame } from "@/components/common/page-frame";
import { PromoteFromInvestigation } from "@/components/str-reports/promote-from-investigation";
import { requireViewer } from "@/lib/auth";

type PageProps = {
  searchParams: Promise<{ investigation?: string; entity?: string }>;
};

export const dynamic = "force-dynamic";

export default async function STRPromoteFromInvestigationPage({ searchParams }: PageProps) {
  await requireViewer();
  const { investigation, entity } = await searchParams;

  return (
    <PageFrame
      eyebrow="STR draft · AI promotion"
      title="Create STR draft from AI investigation"
      description="Kestrel is taking the agent's hypothesis, evidence trail, and suggested actions and seeding a new STR draft. You will be redirected to the editable workspace as soon as the draft is created."
    >
      <PromoteFromInvestigation
        investigationId={investigation ?? null}
        entityId={entity ?? null}
      />
    </PageFrame>
  );
}
