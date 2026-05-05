export function BanksFinalCta() {
  return (
    <section className="border-b border-landing-rule bg-landing-bg">
      <div className="mx-auto w-full max-w-7xl px-6 py-28 lg:px-10">
        <div className="flex flex-col gap-6">
          <span className="flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-alarm">
            <span className="leading-none">┼</span> Briefing intake
          </span>
          <h2 className="font-landing-display text-4xl leading-[1.05] text-landing-foreground lg:text-7xl">
            Request a 30-minute demo.
            <br />
            <span className="text-landing-muted">On real data. With your CAMLCO.</span>
          </h2>
          <p className="max-w-2xl font-landing-body text-base leading-relaxed text-landing-foreground/85 lg:text-lg">
            We walk through detection on a synthetic but realistic Bangladesh transaction file, an
            AI-explained alert, a draft STR, and the cross-bank intelligence view as a bank persona
            sees it. No slide deck. No NDA required for the walkthrough.
          </p>
          <div className="flex flex-wrap gap-4 pt-4">
            <a
              href="#access"
              className="inline-flex items-center gap-3 bg-landing-alarm px-8 py-4 font-landing-display text-sm uppercase tracking-[0.22em] text-landing-bg transition hover:opacity-90"
            >
              <span>┼</span> File a demo request
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
