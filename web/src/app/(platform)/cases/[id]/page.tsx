import { PageFrame } from "@/components/common/page-frame";
import { CaseWorkspace } from "@/components/cases/case-workspace";

export default async function CasePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return (
    <PageFrame
      eyebrow="Case workspace"
      title="Case workspace"
      description="Work linked evidence, record analyst notes, manage assignment, and move the case through its lifecycle."
    >
      <CaseWorkspace caseId={id} />
    </PageFrame>
  );
}
