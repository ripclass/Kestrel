import { BanksCircularCallout } from "@/components/banks/banks-circular-callout";
import { BanksCrossBank } from "@/components/banks/banks-cross-bank";
import { BanksFeatures } from "@/components/banks/banks-features";
import { BanksFinalCta } from "@/components/banks/banks-final-cta";
import { BanksHero } from "@/components/banks/banks-hero";
import { BanksHowItWorks } from "@/components/banks/banks-how-it-works";
import { BanksPricing } from "@/components/banks/banks-pricing";
import { BanksStatsRow } from "@/components/banks/banks-stats-row";
import { PublicFooter } from "@/components/public/public-footer";
import { PublicHeader } from "@/components/public/public-header";

export const metadata = {
  title: "Kestrel for banks — AI transaction monitoring + STR drafting in Bangladesh",
  description:
    "AI transaction monitoring, AI-explained alerts, draft STR generation, cross-bank intelligence. BB Circular 26/2024 aligned. Deployed in 4 weeks. Billed in BDT.",
};

export default function BanksLandingPage() {
  return (
    <main className="flex min-h-screen flex-col bg-landing-bg">
      <PublicHeader />
      <BanksHero />
      <BanksStatsRow />
      <BanksFeatures />
      <BanksCrossBank />
      <BanksCircularCallout />
      <BanksPricing />
      <BanksHowItWorks />
      <BanksFinalCta />
      <PublicFooter />
    </main>
  );
}
