export function FinalCta() {
  return (
    <section className="border-b border-landing-rule bg-landing-bg">
      <div className="mx-auto w-full max-w-7xl px-6 py-28 lg:px-10">
        <div className="flex flex-col gap-6">
          <span className="flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-alarm">
            <span className="leading-none">┼</span> Restricted Issuance
          </span>
          <h2 className="font-landing-display text-4xl leading-[1.05] text-landing-foreground lg:text-7xl">
            Clearance is issued to
            <br />
            <span className="text-landing-muted">cleared institutions only.</span>
          </h2>
          <p className="max-w-2xl font-landing-body text-base leading-relaxed text-landing-foreground/85 lg:text-lg">
            BFIU · commercial banks · licensed MFS providers · peer FIUs in the Egmont Group ·
            accredited press. Return to the intake at the top of this page to file a request.
          </p>
          <div className="pt-4">
            <a
              href="#access"
              className="inline-flex items-center gap-3 border border-landing-rule-solid px-8 py-4 font-landing-display text-sm uppercase tracking-[0.22em] text-landing-foreground transition hover:border-landing-foreground hover:bg-landing-foreground hover:text-landing-bg"
            >
              <span className="text-landing-alarm">┼</span> Return to clearance intake
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
