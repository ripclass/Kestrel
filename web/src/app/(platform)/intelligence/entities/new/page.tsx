import { PageFrame } from "@/components/common/page-frame";
import { NewSubjectForm } from "@/components/intel/new-subject-form";
import { requireViewer } from "@/lib/auth";

export default async function NewSubjectPage() {
  await requireViewer();
  return (
    <PageFrame
      eyebrow="Intelligence"
      title="New subject"
      description="Register an account, person, or business directly. Every identifier you attach is resolved into the shared entity pool and linked with same_owner connections for the graph."
    >
      <NewSubjectForm />
    </PageFrame>
  );
}
