import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { accessRequestMailto } from "@/lib/access-request";
import { NetworkIllustration } from "./network-illustration";

export function Hero() {
  return (
    <section className="relative border-b border-white/5">
      <div className="mx-auto grid w-full max-w-7xl gap-12 px-6 pb-20 pt-16 lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:px-10 lg:pt-24">
        <div className="space-y-8">
          <p className="text-xs uppercase tracking-[0.3em] text-primary">
            Financial crime intelligence · Built in Bangladesh
          </p>
          <h1 className="text-4xl font-semibold leading-[1.05] tracking-tight text-white sm:text-5xl lg:text-6xl">
            Scam money moves across six banks in twelve minutes.
            <span className="block text-slate-400">Your analyst finds out six weeks later.</span>
          </h1>
          <p className="max-w-2xl text-lg leading-relaxed text-slate-300">
            Kestrel connects every suspicious transaction report, every flagged account,
            and every money trail across every bank into one real-time intelligence picture.
            What used to take days of manual cross-referencing now surfaces in the time it takes to type
            an account number.
          </p>
          <div className="flex flex-wrap gap-3">
            <a href={accessRequestMailto()}>
              <Button size="lg" aria-label="Request access to Kestrel">
                Request access
                <ArrowRight className="h-4 w-4" />
              </Button>
            </a>
            <Link href="#how">
              <Button size="lg" variant="outline" aria-label="See how Kestrel works">
                See how it works
              </Button>
            </Link>
          </div>
          <p className="text-sm text-slate-400">
            Built for BFIU, banks, and reporting organisations under the Money Laundering Prevention Act, 2012.
          </p>
        </div>

        <div className="relative">
          <div className="absolute inset-0 -z-10 rounded-[2.5rem] bg-primary/10 blur-3xl" aria-hidden />
          <div className="rounded-[2rem] border border-white/10 bg-white/[0.04] p-6 backdrop-blur-sm">
            <div className="mb-4 flex items-center justify-between text-xs text-slate-400">
              <span className="font-mono uppercase tracking-[0.2em]">entity · 8f4c··e21</span>
              <span className="rounded-full border border-rose-400/30 bg-rose-500/10 px-2 py-0.5 font-mono text-[10px] text-rose-200">
                cross-bank match
              </span>
            </div>
            <NetworkIllustration className="h-auto w-full" />
            <div className="mt-4 grid grid-cols-3 gap-2 text-center text-[11px] text-slate-400">
              <div className="rounded-lg border border-white/5 bg-white/[0.02] px-2 py-2">
                <p className="font-mono text-sm text-white">6</p>
                <p className="mt-0.5">banks reporting</p>
              </div>
              <div className="rounded-lg border border-white/5 bg-white/[0.02] px-2 py-2">
                <p className="font-mono text-sm text-white">87</p>
                <p className="mt-0.5">risk score</p>
              </div>
              <div className="rounded-lg border border-white/5 bg-white/[0.02] px-2 py-2">
                <p className="font-mono text-sm text-white">12m</p>
                <p className="mt-0.5">first to last hop</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
