import { PageFrame } from "@/components/common/page-frame";
import { DataTable } from "@/components/common/data-table";
import { demoViewers } from "@/lib/demo";

export default function TeamPage() {
  const viewers = Object.values(demoViewers);

  return (
    <PageFrame
      eyebrow="Administration"
      title="Team management"
      description="Invite users, assign personas, and control role-based access."
    >
      <DataTable
        columns={["Name", "Email", "Role", "Persona"]}
        rows={viewers.map((viewer) => [viewer.fullName, viewer.email, viewer.role, viewer.persona])}
      />
    </PageFrame>
  );
}
