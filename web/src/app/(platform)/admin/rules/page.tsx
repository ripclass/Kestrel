import { PageFrame } from "@/components/common/page-frame";
import { EmptyState } from "@/components/common/empty-state";

export default function RulesPage() {
  return (
    <PageFrame
      eyebrow="Administration"
      title="Detection rules"
      description="Configure YAML-backed rules, weights, and institution-specific overlays."
    >
      <EmptyState
        title="Rule management scaffolded"
        description="Connect this screen to rule definitions, versioning, and activation workflows."
      />
    </PageFrame>
  );
}
