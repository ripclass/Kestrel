import Link from "next/link";
import { ArrowRight, ShieldCheck, Waypoints } from "lucide-react";

import { DeploymentReadinessPanel } from "@/components/public/deployment-readiness";
import { Button } from "@/components/ui/button";
import { fetchDeploymentReadiness } from "@/lib/system";
import { demoPersonaOptions } from "@/lib/demo";
import { isDemoModeConfigured } from "@/lib/runtime";

export const dynamic = "force-dynamic";

export default async function LandingPage() {
  const readiness = await fetchDeploymentReadiness();
  const demoModeEnabled = isDemoModeConfigured();

  return (
    <main className="grid-surface mx-auto flex min-h-screen w-full max-w-7xl flex-col px-6 py-10 lg:px-10">
      <header className="flex items-center justify-between py-4">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-primary">Kestrel</p>
          <p className="text-sm text-muted-foreground">Financial crime intelligence for Bangladesh</p>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/pricing" className="text-sm text-muted-foreground hover:text-foreground">
            Pricing
          </Link>
          <Link href="/login">
            <Button>Enter platform</Button>
          </Link>
        </div>
      </header>
      <section className="grid flex-1 gap-12 py-20 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
        <div className="space-y-8">
          <div className="space-y-4">
            <p className="text-xs uppercase tracking-[0.3em] text-primary">Built for BFIU, banks, and directors</p>
            <h1 className="max-w-4xl text-5xl font-semibold tracking-tight text-white lg:text-7xl">
              goAML is the filing cabinet. Kestrel is the detective.
            </h1>
            <p className="max-w-2xl text-lg text-slate-300">
              A national intelligence layer for cross-bank matches, network analysis, explainable risk scoring, and command reporting.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link href="/login">
              <Button size="lg">
                Enter Kestrel
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link href="/pricing">
              <Button variant="outline" size="lg">Review deployment model</Button>
            </Link>
          </div>
          {demoModeEnabled ? (
            <div className="flex flex-wrap gap-2">
              {demoPersonaOptions.map((option) => (
                <Link
                  key={option.persona}
                  href={`/demo/${option.persona}?next=/overview`}
                  className="rounded-full border border-white/10 px-4 py-2 text-sm text-slate-300 transition hover:border-primary/40 hover:text-white"
                >
                  Launch {option.title}
                </Link>
              ))}
            </div>
          ) : null}
        </div>
        <div className="space-y-4">
          {[
            {
              title: "Cross-bank intelligence",
              detail: "See the same account, phone, or wallet across multiple banks in one dossier.",
              Icon: ShieldCheck,
            },
            {
              title: "Network-first analysis",
              detail: "Trace money flows through beneficiaries, wallets, and shared devices with reusable graph views.",
              Icon: Waypoints,
            },
          ].map(({ title, detail, Icon: ItemIcon }) => {
            return (
              <div key={title} className="rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur">
                <div className="mb-4 inline-flex rounded-2xl bg-primary/20 p-3 text-primary">
                  <ItemIcon className="h-5 w-5" />
                </div>
                <h2 className="text-xl font-semibold text-white">{title}</h2>
                <p className="mt-2 text-sm text-slate-300">{detail}</p>
              </div>
            );
          })}
        </div>
      </section>
      <section className="space-y-6 pb-12">
        <div className="flex flex-col gap-2">
          <p className="text-xs uppercase tracking-[0.28em] text-primary">Live posture</p>
          <h2 className="text-2xl font-semibold text-white">Cloud deployment health is visible from the front door.</h2>
          <p className="max-w-3xl text-sm text-slate-300">
            The public surface now reflects actual engine readiness across auth, database, storage, worker, and optional AI providers.
          </p>
        </div>
        <DeploymentReadinessPanel readiness={readiness} compact />
      </section>
    </main>
  );
}
