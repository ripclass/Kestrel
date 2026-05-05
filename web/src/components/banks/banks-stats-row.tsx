const stats: {
  value: string;
  label: string;
  source: string;
}[] = [
  {
    value: "8",
    label: "Bangladesh-tuned detection rules in production. Structuring, layering, fan-in, fan-out, dormant spike, more.",
    source: "engine/app/core/detection/rules",
  },
  {
    value: "4",
    label: "Banks already on the cross-bank intelligence layer. Each new tenant strengthens every other tenant's signal.",
    source: "kestrel-engine · matches table",
  },
  {
    value: "BDT",
    label: "Native pricing, native channels, native typologies. NPSB / BEFTN / RTGS / bKash / Nagad / Rocket out of the box.",
    source: "Bangladesh-only by design",
  },
  {
    value: "4 wks",
    label: "From signed order to first STR drafted in production. No multi-quarter integration project.",
    source: "Standard onboarding plan",
  },
];

export function BanksStatsRow() {
  return (
    <section className="border-b border-landing-rule bg-landing-bg">
      <div className="mx-auto w-full max-w-7xl px-6 lg:px-10">
        <div className="grid grid-cols-2 divide-x divide-y divide-landing-rule-solid border border-landing-rule-solid lg:grid-cols-4 lg:divide-y-0">
          {stats.map((stat, i) => (
            <div key={stat.value} className="relative flex min-h-[240px] flex-col gap-4 p-8 lg:p-10">
              <span className="font-landing-body text-[10px] uppercase tracking-[0.28em] text-landing-muted">
                {`Spec 0${i + 1}`}
              </span>
              <p className="font-landing-display text-4xl leading-none tracking-tight text-landing-foreground lg:text-5xl">
                {stat.value}
              </p>
              <p className="font-landing-body text-sm leading-relaxed text-landing-foreground/80">
                {stat.label}
              </p>
              <p className="mt-auto font-landing-body text-[10px] uppercase tracking-[0.24em] text-landing-muted">
                {stat.source}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
