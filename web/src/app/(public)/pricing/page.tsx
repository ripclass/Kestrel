import { FinalCta } from "@/components/public/final-cta";
import { PricingTiers } from "@/components/public/pricing-tiers";
import { PublicFooter } from "@/components/public/public-footer";
import { PublicHeader } from "@/components/public/public-header";

export const metadata = {
  title: "Kestrel — Pricing",
  description:
    "Three tiers, BDT-denominated. Starter (Tk 60 lakh), Professional (Tk 1.5 crore), Enterprise (Tk 4 crore). No surprises.",
};

export default function PricingPage() {
  return (
    <main className="flex min-h-screen flex-col bg-landing-bg">
      <PublicHeader />
      <PricingTiers />
      <FinalCta />
      <PublicFooter />
    </main>
  );
}
