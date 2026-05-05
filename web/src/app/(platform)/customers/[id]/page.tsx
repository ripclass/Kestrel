import { notFound } from "next/navigation";

import { PageFrame } from "@/components/common/page-frame";
import { CustomerDetail } from "@/components/customers/customer-detail";
import { requireViewer } from "@/lib/auth";

export default async function CustomerDetailPage({ params }: { params: Promise<{ id: string }> }) {
  await requireViewer();
  const { id } = await params;
  if (!id || id.length < 8) notFound();
  return (
    <PageFrame
      eyebrow="KYC / CDD · Customer"
      title="Customer detail"
      description="Profile, screening results, beneficial owners, and review actions. Re-screening calls the same engine path as the periodic Beat task — useful when the watchlist pool just gained new entries and you want to verify a specific customer."
    >
      <CustomerDetail customerId={id} />
    </PageFrame>
  );
}
