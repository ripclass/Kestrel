import { PageFrame } from "@/components/common/page-frame";
import { TenantManagement } from "@/components/operator/tenant-management";
import { requirePlatformOperator } from "@/lib/auth";

export default async function TenantsPage() {
  await requirePlatformOperator();
  return (
    <PageFrame
      eyebrow="Operator · Tenants"
      title="Tenant management"
      description="Provision a new tenant — organization, plan, classification, and the first admin invite — in one step, or manage existing ones. Marking a tenant demo / pilot / live controls how the Pilot Health board groups it; the classification is a label only and does not touch the tenant's data, plan, or isolation."
    >
      <TenantManagement />
    </PageFrame>
  );
}
