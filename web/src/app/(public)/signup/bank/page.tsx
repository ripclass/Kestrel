import Link from "next/link";
import { notFound } from "next/navigation";

import { BankSignupForm } from "@/components/banks/bank-signup-form";
import { PublicFooter } from "@/components/public/public-footer";
import { PublicHeader } from "@/components/public/public-header";
import { isBankDirectSignupEnabled } from "@/lib/runtime";

export const metadata = {
  title: "Provision a bank workspace — Kestrel",
  description:
    "Self-serve signup for Bangladesh banks. Provision a Kestrel workspace, get a magic-link invite, land on a pre-seeded demo tenant, file your first STR.",
};

export const dynamic = "force-dynamic";

export default function BankSignupPage() {
  if (!isBankDirectSignupEnabled()) {
    notFound();
  }

  return (
    <main className="flex min-h-screen flex-col bg-landing-bg">
      <PublicHeader />
      <section className="border-b border-landing-rule bg-landing-bg pt-24 pb-24 lg:pt-32">
        <div className="mx-auto grid w-full max-w-7xl grid-cols-1 gap-16 px-6 lg:grid-cols-12 lg:gap-12 lg:px-10">
          <div className="col-span-1 flex flex-col gap-8 lg:col-span-5">
            <div className="flex flex-col gap-6">
              <span className="flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-alarm">
                <span className="leading-none">┼</span> Workspace provisioning
              </span>
              <h1 className="font-landing-display text-4xl leading-[1.05] text-landing-foreground md:text-5xl">
                Provision a bank workspace.
                <br />
                <span className="text-landing-muted">Magic link in your inbox in 60 seconds.</span>
              </h1>
              <p className="max-w-md font-landing-body text-base leading-relaxed text-landing-foreground/80">
                Direct signup for Bangladesh banks. Your workspace lands isolated from every other
                tenant — RLS-enforced. A pre-seeded synthetic dataset (transactions, alerts, draft
                STRs, cross-bank context) is staged so you can exercise the platform on day one.
              </p>
            </div>
            <ul className="flex flex-col gap-3 border border-landing-rule-solid p-6 font-landing-body text-sm leading-relaxed text-landing-foreground/85">
              <li className="flex items-start gap-3">
                <span className="pt-0.5 leading-none text-landing-alarm">┼</span>
                <span>
                  You become an <span className="uppercase tracking-[0.18em]">admin</span> of a fresh
                  bank tenant. Persona is auto-set to <span className="uppercase tracking-[0.18em]">bank_camlco</span>.
                </span>
              </li>
              <li className="flex items-start gap-3">
                <span className="pt-0.5 leading-none text-landing-alarm">┼</span>
                <span>
                  No BFIU intervention required. Banks are a first-class tenant.
                </span>
              </li>
              <li className="flex items-start gap-3">
                <span className="pt-0.5 leading-none text-landing-alarm">┼</span>
                <span>
                  Demo data appears on first login. Replace with your own scan upload anytime.
                </span>
              </li>
            </ul>
            <p className="font-landing-body text-[11px] uppercase tracking-[0.22em] text-landing-muted">
              Not ready for self-serve?
              <Link href="/banks#access" className="ml-2 border-b border-landing-rule-solid pb-0.5 text-landing-foreground/80 transition hover:border-landing-foreground hover:text-landing-foreground">
                File a briefing intake instead
              </Link>
            </p>
          </div>

          <div className="col-span-1 lg:col-span-7">
            <div className="border border-landing-rule-solid p-8 lg:p-10">
              <div className="mb-8 flex items-center justify-between">
                <h2 className="font-landing-display text-2xl text-landing-foreground">
                  Bank-direct signup
                </h2>
                <span className="font-landing-body text-[10px] uppercase tracking-[0.28em] text-landing-alarm">
                  ┼ Tier · Trial
                </span>
              </div>
              <BankSignupForm />
            </div>
          </div>
        </div>
      </section>
      <PublicFooter />
    </main>
  );
}
