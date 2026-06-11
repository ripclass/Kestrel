import Link from "next/link";
import { redirect } from "next/navigation";

import { BankSignupForm } from "@/components/banks/bank-signup-form";
import { PublicFooter } from "@/components/public/public-footer";
import { PublicHeader } from "@/components/public/public-header";
import { isBankDirectSignupEnabled } from "@/lib/runtime";

export const metadata = {
  title: "Request a bank workspace — Kestrel",
  description:
    "Workspace requests for Bangladesh banks. Verified against the Bangladesh Bank scheduled-bank list, approved within one business day, delivered as a magic-link invite to a pre-seeded demo tenant.",
};

export const dynamic = "force-dynamic";

export default function BankSignupPage() {
  if (!isBankDirectSignupEnabled()) {
    // Self-serve provisioning is gated until applicant vetting exists —
    // route the intent to the briefing-intake form instead of a dead 404
    // (11 public-surface CTAs link here).
    redirect("/banks#access");
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
                Request a bank workspace.
                <br />
                <span className="text-landing-muted">Approved within one business day.</span>
              </h1>
              <p className="max-w-md font-landing-body text-base leading-relaxed text-landing-foreground/80">
                Direct requests for Bangladesh banks. Every request is verified against the
                Bangladesh Bank scheduled-bank list before provisioning — your workspace lands
                isolated from every other tenant, with a pre-seeded synthetic dataset
                (transactions, alerts, draft STRs, cross-bank context) staged so you can exercise
                the platform on day one.
              </p>
            </div>
            <ul className="flex flex-col gap-3 border border-landing-rule-solid p-6 font-landing-body text-sm leading-relaxed text-landing-foreground/85">
              <li className="flex items-start gap-3">
                <span className="pt-0.5 leading-none text-landing-alarm">┼</span>
                <span>
                  Requests are verified against the{" "}
                  <span className="uppercase tracking-[0.18em]">Bangladesh Bank</span> scheduled-bank
                  list. Use your official bank email — personal domains are declined.
                </span>
              </li>
              <li className="flex items-start gap-3">
                <span className="pt-0.5 leading-none text-landing-alarm">┼</span>
                <span>
                  On approval you become an <span className="uppercase tracking-[0.18em]">admin</span> of
                  a fresh bank tenant via magic-link invite. Persona is auto-set to{" "}
                  <span className="uppercase tracking-[0.18em]">bank_camlco</span>.
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
                  Workspace request
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
