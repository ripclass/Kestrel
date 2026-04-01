import { PageFrame } from "@/components/common/page-frame";
import { EmptyState } from "@/components/common/empty-state";

export default function AdminPage() {
  return (
    <PageFrame
      eyebrow="Administration"
      title="Organization settings"
      description="Manage tenant-level configuration, integration posture, and access defaults."
    >
      <EmptyState
        title="Admin settings scaffolded"
        description="Wire this surface to org settings, goAML adapter controls, and notification configuration."
      />
    </PageFrame>
  );
}
