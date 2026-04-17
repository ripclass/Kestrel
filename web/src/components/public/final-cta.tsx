import { ArrowRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { accessRequestMailto } from "@/lib/access-request";

export function FinalCta() {
  return (
    <section id="access" className="border-b border-white/5">
      <div className="mx-auto w-full max-w-7xl px-6 py-24 lg:px-10">
        <div className="rounded-[2.5rem] border border-white/10 bg-gradient-to-br from-primary/15 via-white/[0.02] to-transparent p-10 backdrop-blur-sm lg:p-16">
          <div className="max-w-3xl space-y-6">
            <p className="text-xs uppercase tracking-[0.28em] text-primary">Ready to see it?</p>
            <h2 className="text-3xl font-semibold tracking-tight text-white lg:text-5xl">
              Access is granted to BFIU, commercial banks, MFS providers, and authorised regulatory
              partners.
            </h2>
            <p className="text-lg leading-relaxed text-slate-300">
              Tell us who you are and how you&apos;d use Kestrel. We&apos;ll set up a walkthrough on
              synthetic data and discuss what it would take to stand Kestrel up in your environment.
            </p>
            <div className="flex flex-wrap gap-3 pt-2">
              <a href={accessRequestMailto()}>
                <Button size="lg" aria-label="Request access to Kestrel">
                  Request access
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </a>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
