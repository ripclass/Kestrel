import Link from "next/link";

export function FinalCta() {
  return (
    <section className="border-b border-landing-rule bg-landing-bg">
      <div className="mx-auto w-full max-w-7xl px-6 py-28 lg:px-10">
        <div className="flex flex-col gap-6">
          <span className="flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-alarm">
            <span className="leading-none">┼</span> Next step
          </span>
          <h2 className="font-landing-display text-4xl leading-[1.05] text-landing-foreground lg:text-7xl">
            Ready to
            <br />
            <span className="text-landing-muted">evaluate?</span>
          </h2>
          <p className="max-w-2xl font-landing-body text-base leading-relaxed text-landing-foreground/85 lg:text-lg">
            Bank pilots run for thirty days at a fixed pilot fee that converts to subscription on
            contract. Briefings for BFIU and peer regulators are scheduled directly. Press, partners,
            and accredited researchers can download the full press kit without registration.
          </p>
          <div className="flex flex-wrap gap-4 pt-4">
            <Link
              href="/signup/bank"
              className="inline-flex items-center gap-3 bg-landing-alarm px-8 py-4 font-landing-display text-sm uppercase tracking-[0.22em] text-landing-bg transition hover:opacity-90"
            >
              <span>┼</span> Run a pilot →
            </Link>
            <Link
              href="/contact?audience=bfiu"
              className="inline-flex items-center gap-3 border border-landing-foreground px-8 py-4 font-landing-body text-sm uppercase tracking-[0.22em] text-landing-foreground transition hover:bg-landing-foreground hover:text-landing-bg"
            >
              Schedule a briefing →
            </Link>
            <Link
              href="/docs"
              className="inline-flex items-center gap-3 border border-landing-rule-solid px-8 py-4 font-landing-body text-sm uppercase tracking-[0.22em] text-landing-foreground/85 transition hover:border-landing-foreground hover:text-landing-foreground"
            >
              Read the docs →
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
