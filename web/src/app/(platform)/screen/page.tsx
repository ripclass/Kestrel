import { PageFrame } from "@/components/common/page-frame";
import { ScreeningPanel } from "@/components/screening/screening-panel";
import { requireViewer } from "@/lib/auth";

export default async function ScreeningPage() {
  const viewer = await requireViewer();

  return (
    <PageFrame
      eyebrow="Sanctions / PEP screening"
      title="Watchlist screening for banks and the regulator"
      description="Fuzzy match a candidate name against OFAC SDN, UN consolidated, UK OFSI, EU consolidated, Bangladesh Bank's domestic list, and PEP. Adverse-media screening is wired to ComplyAdvantage when configured. Results are scored 0–1 across name + DOB + nationality + identifier."
    >
      <ScreeningPanel viewer={viewer} />
    </PageFrame>
  );
}
