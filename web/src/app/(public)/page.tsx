import Link from "next/link";

import { BangladeshSection } from "@/components/public/bangladesh-section";
import { CoverageSection } from "@/components/public/coverage-section";
import { FinalCta } from "@/components/public/final-cta";
import { LandingHero } from "@/components/public/landing-hero";
import { PersonaCards } from "@/components/public/persona-cards";
import { ProductionMetrics } from "@/components/public/production-metrics";
import { PublicFooter } from "@/components/public/public-footer";
import { PublicHeader } from "@/components/public/public-header";
import { StartHereCards } from "@/components/public/start-here-cards";
import { StatsRow } from "@/components/public/stats-row";
import { demoPersonaOptions } from "@/lib/demo";
import { isDemoModeConfigured } from "@/lib/runtime";

export const metadata = {
  title: "Kestrel — Financial crime intelligence for Bangladesh's banks",
  description:
    "Pattern detection, cross-bank entity intelligence, AI-drafted STRs, real-time transaction scoring, and goAML interoperability. Billable in BDT, deployable on local infrastructure.",
};

export default function LandingPage() {
  const demoModeEnabled = isDemoModeConfigured();

  return (
    <main className="flex min-h-screen flex-col bg-landing-bg">
      <PublicHeader />
      <LandingHero />

      {demoModeEnabled ? (
        <section className="border-b border-landing-rule bg-landing-bg">
          <div className="mx-auto flex w-full max-w-7xl flex-wrap items-center gap-3 px-6 py-4 text-xs text-landing-muted lg:px-10">
            <span className="font-landing-body uppercase tracking-[0.22em] text-landing-alarm">Demo mode</span>
            <span className="font-landing-body text-landing-muted">Launch a pre-signed persona against the live platform:</span>
            {demoPersonaOptions.map((option) => (
              <Link
                key={option.persona}
                href={`/demo/${option.persona}?next=/overview`}
                className="font-landing-body rounded-none border border-landing-rule px-3 py-1 transition hover:border-landing-foreground hover:text-landing-foreground uppercase"
              >
                {option.title}
              </Link>
            ))}
          </div>
        </section>
      ) : null}

      <StartHereCards />
      <StatsRow />
      <CoverageSection />
      <ProductionMetrics />
      <PersonaCards />
      <BangladeshSection />
      <FinalCta />
      <PublicFooter />
    </main>
  );
}
