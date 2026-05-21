import { PageFrame } from "@/components/common/page-frame";
import { PilotHealthBoard } from "@/components/platform/pilot-health-board";
import { requirePlatformOperator } from "@/lib/auth";

export default async function PlatformConsolePage() {
  await requirePlatformOperator();
  return (
    <PageFrame
      eyebrow="Platform · Pilot health"
      title="Pilot health"
      description="Cross-tenant operator view — who has signed in, who is doing real work, and which pilots are stalling. Enso-internal; never visible to bank or BFIU users. Engagement combines Supabase sign-in recency with audit-log activity (the load-bearing signal — it tracks real work, not just visits)."
    >
      <PilotHealthBoard />
    </PageFrame>
  );
}
