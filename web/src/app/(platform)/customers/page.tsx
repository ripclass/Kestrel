import Link from "next/link";

import { PageFrame } from "@/components/common/page-frame";
import { CustomersList } from "@/components/customers/customers-list";
import { requireViewer } from "@/lib/auth";

export default async function CustomersPage() {
  await requireViewer();
  return (
    <PageFrame
      eyebrow="KYC / CDD"
      title="Customers"
      description="Onboarded customers, scored against the shared sanctions / PEP / adverse-media pool. Risk level and KYC status are computed at onboarding and refreshed by the daily re-screening Beat task."
      actions={
        <Link
          href="/customers/new"
          className="border border-foreground bg-foreground px-5 py-2 font-mono text-[11px] uppercase tracking-[0.22em] text-background transition hover:bg-background hover:text-foreground"
        >
          Onboard customer
        </Link>
      }
    >
      <CustomersList />
    </PageFrame>
  );
}
