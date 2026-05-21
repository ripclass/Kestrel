import { PageFrame } from "@/components/common/page-frame";
import { PilotHealthBoard } from "@/components/operator/pilot-health-board";
import { requirePlatformOperator } from "@/lib/auth";

export default async function PilotHealthPage() {
  await requirePlatformOperator();
  return (
    <PageFrame
      eyebrow="Operator · Pilot health"
      title="Pilot health"
      description="Are the pilot banks using Kestrel, and which ones are stalling. Real pilots are listed first; demo / sandbox tenants are separated below. Engagement combines Supabase sign-in recency with audit-log activity — the load-bearing signal, since it tracks real work, not visits."
    >
      <PilotHealthBoard />
    </PageFrame>
  );
}
