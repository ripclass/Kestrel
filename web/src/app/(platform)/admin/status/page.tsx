import { PageFrame } from "@/components/common/page-frame";
import { AdminStatusPanel } from "@/components/admin/admin-status-panel";
import { requireRole } from "@/lib/auth";

export default async function AdminStatusPage() {
  await requireRole("admin", "superadmin");
  return (
    <PageFrame
      eyebrow="Admin · Status"
      title="Post status incidents"
      description="Surfaces a new entry on the public status page (kestrel-nine.vercel.app/status) within seconds. Use major / outage to drive the overall-status banner; minor incidents stay informational. Only regulator-org admins can post."
    >
      <AdminStatusPanel />
    </PageFrame>
  );
}
