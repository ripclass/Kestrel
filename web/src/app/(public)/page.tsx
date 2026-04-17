import Link from "next/link";

import { BangladeshSection } from "@/components/public/bangladesh-section";
import { CoverageSection } from "@/components/public/coverage-section";
import { FinalCta } from "@/components/public/final-cta";
import { Hero } from "@/components/public/hero";
import { HowItWorks } from "@/components/public/how-it-works";
import { PersonaCards } from "@/components/public/persona-cards";
import { ProblemSection } from "@/components/public/problem-section";
import { ProductSection } from "@/components/public/product-section";
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
    <main className="flex min-h-screen flex-col">
      <PublicHeader />
      <Hero />

      {demoModeEnabled ? (
        <section className="border-b border-white/5 bg-white/[0.02]">
          <div className="mx-auto flex w-full max-w-7xl flex-wrap items-center gap-3 px-6 py-4 text-xs text-slate-400 lg:px-10">
            <span className="font-mono uppercase tracking-[0.22em] text-primary">Demo mode</span>
            <span className="text-slate-500">Launch a pre-signed persona against the live platform:</span>
            {demoPersonaOptions.map((option) => (
              <Link
                key={option.persona}
                href={`/demo/${option.persona}?next=/overview`}
                className="rounded-full border border-white/10 px-3 py-1 transition hover:border-primary/40 hover:text-white"
              >
                {option.title}
              </Link>
            ))}
          </div>
        </section>
      ) : null}

      <StatsRow />
      <ProblemSection />
      <ProductSection />
      <HowItWorks />
      <CoverageSection />
      <PersonaCards />
      <BangladeshSection />
      <FinalCta />
      <PublicFooter />
    </main>
  );
}
