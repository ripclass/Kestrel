import { PageFrame } from "@/components/common/page-frame";
import { TenantManagement } from "@/components/operator/tenant-management";
import { requirePlatformOperator } from "@/lib/auth";

export default async function TenantsPage() {
  await requirePlatformOperator();
  return (
    <PageFrame
      eyebrow="Operator · Tenants"
      title="Tenant management"
      description="Every tenant on the platform, with plan, seat coverage and classification. Mark a tenant demo / pilot / live — the classification controls how the Pilot Health board groups it. It is a label only; it does not touch the tenant's data, plan, or isolation."
    >
      <TenantManagement />
    </PageFrame>
  );
}
