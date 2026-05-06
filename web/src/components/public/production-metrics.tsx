const metrics: {
  value: string;
  body: string;
}[] = [
  {
    value: "27,481",
    body: "Sanctions records screened daily across OFAC, UN, UK FCDO. Refreshed every 24 hours via scheduled tasks.",
  },
  {
    value: "< 500 ms",
    body: "Real-time transaction scoring SLA, with full rule explainability returned in the response.",
  },
  {
    value: "134",
    body: "Production API routes across STR, CTR, IER, case, screening, realtime, agentic investigation, admin.",
  },
  {
    value: "11",
    body: "Scheduled jobs running on production: nightly scan, daily digest, weekly compliance, KYC re-screening, audit retention.",
  },
  {
    value: "< 10 min",
    body: "From signup to populated demo workspace. Self-serve, with twelve months of synthetic data seeded automatically.",
  },
  {
    value: "99.5% / 99.9%",
    body: "Uptime SLA, Professional and Enterprise tiers. Live status page with 30 and 90 day windows.",
  },
];

export function ProductionMetrics() {
  return (
    <section className="border-b border-landing-rule bg-landing-bg">
      <div className="mx-auto w-full max-w-7xl px-6 py-24 lg:px-10">
        <div className="max-w-4xl space-y-6">
          <span className="flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-alarm">
            <span className="leading-none">┼</span> Production metrics
          </span>
          <h2 className="font-landing-display text-3xl leading-[1.08] text-landing-foreground lg:text-5xl">
            Real software,
            <br />
            <span className="text-landing-muted">running today.</span>
          </h2>
        </div>

        <div className="mt-16 grid grid-cols-1 divide-x divide-y divide-landing-rule-solid border border-landing-rule-solid sm:grid-cols-2 lg:grid-cols-3">
          {metrics.map((metric, i) => (
            <div
              key={metric.value}
              className="relative flex min-h-[220px] flex-col gap-4 p-8 lg:p-10"
            >
              <span className="font-landing-body text-[10px] uppercase tracking-[0.28em] text-landing-muted">
                {`Run 0${i + 1}`}
              </span>
              <p className="font-landing-display text-4xl leading-none tracking-tight text-landing-foreground lg:text-5xl">
                {metric.value}
              </p>
              <p className="font-landing-body text-sm leading-relaxed text-landing-foreground/80">
                {metric.body}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
