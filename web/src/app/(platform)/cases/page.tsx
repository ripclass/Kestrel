import { CaseBoard } from "@/components/cases/case-board";
import { PageFrame } from "@/components/common/page-frame";

export default function CasesPage() {
  return (
    <PageFrame
      eyebrow="Case management"
      title="Case board"
      description="Cases aggregate alerts, linked entities, evidence, notes, and exportable narratives."
    >
      <CaseBoard />
    </PageFrame>
  );
}
