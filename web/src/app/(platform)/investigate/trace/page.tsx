import { EmptyState } from "@/components/common/empty-state";
import { PageFrame } from "@/components/common/page-frame";

export default function TracePage() {
  return (
    <PageFrame
      eyebrow="Money flow tracer"
      title="Trace funds"
      description="Trace from source to beneficiary through network depth, time windows, and channel filters."
    >
      <EmptyState
        title="Trace builder scaffolded"
        description="Connect this page to the network pathfinder endpoints to drive from->to tracing and evidentiary exports."
      />
    </PageFrame>
  );
}
