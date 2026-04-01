import { PageFrame } from "@/components/common/page-frame";
import { AnalystView } from "@/components/overview/analyst-view";
import { BankView } from "@/components/overview/bank-view";
import { CommandView } from "@/components/overview/command-view";
import { requireViewer } from "@/lib/auth";

export default async function OverviewPage() {
  const viewer = await requireViewer();

  return (
    <PageFrame
      eyebrow="Role-aware overview"
      title="National intelligence at the right altitude"
      description="Kestrel changes the overview surface by persona so the same platform feels like three products with one intelligence engine underneath."
    >
      {viewer.persona === "bfiu_director" ? (
        <CommandView />
      ) : viewer.persona === "bank_camlco" ? (
        <BankView />
      ) : (
        <AnalystView />
      )}
    </PageFrame>
  );
}
