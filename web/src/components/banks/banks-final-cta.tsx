import Link from "next/link";

export function BanksFinalCta() {
  return (
    <section className="border-b border-landing-rule bg-landing-bg">
      <div className="mx-auto w-full max-w-7xl px-6 py-28 lg:px-10">
        <div className="flex flex-col gap-6">
          <span className="flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-alarm">
            <span className="leading-none">┼</span> Two ways in
          </span>
          <h2 className="font-landing-display text-4xl leading-[1.05] text-landing-foreground lg:text-7xl">
            Provision a workspace, or request a 30-minute demo.
            <br />
            <span className="text-landing-muted">Either way, on real data.</span>
          </h2>
          <p className="max-w-2xl font-landing-body text-base leading-relaxed text-landing-foreground/85 lg:text-lg">
            Self-serve signup spins up an isolated bank tenant pre-loaded with a synthetic
            Bangladesh dataset — exercise detection, alerts, draft STRs, cross-bank intelligence on
            day one. Or file a briefing intake and we walk through it with you on a 30-minute call.
          </p>
          <div className="flex flex-wrap gap-4 pt-4">
            <Link
              href="/signup/bank"
              className="inline-flex items-center gap-3 bg-landing-alarm px-8 py-4 font-landing-display text-sm uppercase tracking-[0.22em] text-landing-bg transition hover:opacity-90"
            >
              <span>┼</span> Provision a workspace
            </Link>
            <a
              href="#access"
              className="inline-flex items-center gap-3 border border-landing-foreground px-8 py-4 font-landing-body text-sm uppercase tracking-[0.22em] text-landing-foreground transition hover:bg-landing-foreground hover:text-landing-bg"
            >
              File a briefing request
            </a>
            <a
              href="https://github.com/ripclass/Kestrel/blob/main/docs/cross-bank-intelligence.md"
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex items-center gap-3 border border-landing-rule-solid px-8 py-4 font-landing-body text-sm uppercase tracking-[0.22em] text-landing-foreground/85 transition hover:border-landing-foreground hover:text-landing-foreground"
            >
              Read the cross-bank whitepaper ↗
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
