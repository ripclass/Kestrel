import { PageFrame } from "@/components/common/page-frame";
import { TbmlDashboard } from "@/components/intel/tbml-dashboard";
import { requireViewer } from "@/lib/auth";

export const dynamic = "force-dynamic";

export default async function TbmlDashboardPage() {
  await requireViewer();
  return (
    <PageFrame
      eyebrow="Intelligence · TBML detection"
      title="Trade-based money laundering"
      description="BFIU-aligned coverage across the 29 BD-specific TBML avenues, with predicate offences and avenue references on every alert."
    >
      <TbmlDashboard />
    </PageFrame>
  );
}
