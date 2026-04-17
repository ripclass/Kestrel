import { redirect } from "next/navigation";

import { PageFrame } from "@/components/common/page-frame";
import { SchedulesView } from "@/components/admin/schedules-view";
import { requireViewer } from "@/lib/auth";

export default async function SchedulesPage() {
  const viewer = await requireViewer();
  if (!["admin", "superadmin"].includes(viewer.role) || viewer.orgType !== "regulator") {
    redirect("/admin");
  }
  return (
    <PageFrame
      eyebrow="Admin"
      title="Scheduled processes"
      description="Jobs that operators plan to run on a schedule, plus a live view of attached Celery workers."
    >
      <SchedulesView />
    </PageFrame>
  );
}
