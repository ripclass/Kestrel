import { PageFrame } from "@/components/common/page-frame";
import { DiagramBuilder } from "@/components/intel/diagram-builder";
import { requireViewer } from "@/lib/auth";

export default async function DiagramPage() {
  await requireViewer();
  return (
    <PageFrame
      eyebrow="Investigate"
      title="Diagram builder"
      description="Compose a manual case diagram from any entities in the shared intelligence pool. Save it to a case or STR as evidence, or keep it free-standing."
    >
      <DiagramBuilder />
    </PageFrame>
  );
}
