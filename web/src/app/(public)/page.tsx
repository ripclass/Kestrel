import Link from "next/link";

import { BangladeshSection } from "@/components/public/bangladesh-section";
import { CoverageSection } from "@/components/public/coverage-section";
import { FinalCta } from "@/components/public/final-cta";
import { LandingHero } from "@/components/public/landing-hero";
import { PersonaCards } from "@/components/public/persona-cards";
import { PublicFooter } from "@/components/public/public-footer";
import { PublicHeader } from "@/components/public/public-header";
import { StatsRow } from "@/components/public/stats-row";
import { demoPersonaOptions } from "@/lib/demo";
import { isDemoModeConfigured } from "@/lib/runtime";

export const metadata = {
  title: "Kestrel — Financial crime intelligence for Bangladesh",
  description:
    "Kestrel is a national financial intelligence platform. Cross-bank entity resolution, explainable alerts, network analysis, and full goAML coverage — in one live, browser-based interface.",
};

export default function LandingPage() {
  const demoModeEnabled = isDemoModeConfigured();

  return (
    <main className="flex min-h-screen flex-col bg-landing-bg">
      <PublicHeader />
      
      {/* 
        Sovereign Ledger Hero contains the core Problem/Product value proposition
        and the edge-to-edge network graph.
      */}
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

      <StatsRow />
      
      {/* 
        Legacy blocks Removed: ProblemSection, ProductSection, HowItWorks.
        Their narrative is now folded into the LandingHero and the brutalist context.
      */}

      <CoverageSection />
      <PersonaCards />
      <BangladeshSection />
      
      {/* Assuming FinalCta is styled brutally via its own CSS or defaults. Will be a 'Known Gap' to refactor completely matching the form */}
      <FinalCta />
      <PublicFooter />
    </main>
  );
}
