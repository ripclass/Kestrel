import { redirect } from "next/navigation";

import { PageFrame } from "@/components/common/page-frame";
import { MatchDefinitionsAdmin } from "@/components/intel/match-definitions-admin";
import { requireViewer } from "@/lib/auth";

export default async function MatchDefinitionsPage() {
  const viewer = await requireViewer();
  if (!["manager", "admin", "superadmin"].includes(viewer.role)) {
    redirect("/admin");
  }
  return (
    <PageFrame
      eyebrow="Admin"
      title="Match definitions"
      description="BFIU-defined matching rules that run alongside the 8 system rules. Each definition is a JSON policy; executions are recorded here for audit."
    >
      <MatchDefinitionsAdmin />
    </PageFrame>
  );
}
