import { PageFrame } from "@/components/common/page-frame";
import { Omnisearch } from "@/components/investigate/omnisearch";

export default function InvestigatePage() {
  return (
    <PageFrame
      eyebrow="Layer 1A"
      title="Investigate"
      description="Universal search across accounts, phones, wallets, names, and NIDs. This is the core BFIU analyst surface."
    >
      <Omnisearch />
    </PageFrame>
  );
}
