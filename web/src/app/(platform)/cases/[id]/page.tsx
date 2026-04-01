import { PageFrame } from "@/components/common/page-frame";
import { CaseWorkspace } from "@/components/cases/case-workspace";
import { cases } from "@/lib/demo";

export default async function CasePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const currentCase = cases.find((item) => item.id === id) ?? cases[0];

  return (
    <PageFrame
      eyebrow="Case workspace"
      title={currentCase.title}
      description={currentCase.summary}
    >
      <CaseWorkspace />
    </PageFrame>
  );
}
