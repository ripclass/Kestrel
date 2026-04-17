import { redirect } from "next/navigation";

import { PageFrame } from "@/components/common/page-frame";
import { ReferenceTablesAdmin } from "@/components/admin/reference-tables-admin";
import { requireViewer } from "@/lib/auth";

export default async function ReferenceTablesPage() {
  const viewer = await requireViewer();
  if (!["admin", "superadmin", "manager"].includes(viewer.role)) {
    redirect("/admin");
  }
  return (
    <PageFrame
      eyebrow="Admin"
      title="Reference tables"
      description="Lookup masters that populate every dropdown in the app. Banks, MFS providers, channels, categories, countries, currencies, and recipient agencies — regulator-owned."
    >
      <ReferenceTablesAdmin viewerRole={viewer.role} orgType={viewer.orgType} />
    </PageFrame>
  );
}
