const stats: {
  value: string;
  label: string;
  source: string;
}[] = [
  {
    value: "14,106",
    label: "STRs and SARs reviewed by hand in one reporting year.",
    source: "BFIU Annual Report · FY 2022–23",
  },
  {
    value: "90.8%",
    label: "Share of suspicious activity originating inside the banking system.",
    source: "BFIU Annual Report",
  },
  {
    value: "61",
    label: "Scheduled banks in Bangladesh — each blind to the others, until now.",
    source: "Bangladesh Bank",
  },
  {
    value: "~$7.8B",
    label: "Laundered via mobile money in a single year, per published estimates.",
    source: "Centre for Policy Dialogue",
  },
];

export function StatsRow() {
  return (
    <section className="border-b border-landing-rule bg-landing-bg">
      <div className="mx-auto w-full max-w-7xl px-6 lg:px-10">
        <div className="grid grid-cols-2 divide-x divide-y divide-landing-rule-solid border border-landing-rule-solid lg:grid-cols-4 lg:divide-y-0">
          {stats.map((stat, i) => (
            <div key={stat.value} className="relative flex min-h-[240px] flex-col gap-4 p-8 lg:p-10">
              <span className="font-landing-body text-[10px] uppercase tracking-[0.28em] text-landing-muted">
                {`Anchor 0${i + 1}`}
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
