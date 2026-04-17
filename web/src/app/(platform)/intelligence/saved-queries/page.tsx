import { PageFrame } from "@/components/common/page-frame";
import { SavedQueryList } from "@/components/intel/saved-query-list";
import { requireViewer } from "@/lib/auth";

export default async function SavedQueriesPage() {
  const viewer = await requireViewer();
  return (
    <PageFrame
      eyebrow="Intel"
      title="Saved queries"
      description="Reusable filters across investigate, alerts, cases, and STRs. Share across your organization or keep them private to you."
    >
      <SavedQueryList viewer={viewer} />
    </PageFrame>
  );
}
