const stats: {
  value: string;
  label: string;
  source: string;
}[] = [
  {
    value: "14,106",
    label: "STRs and SARs received by BFIU in a single reporting year, each reviewed by hand.",
    source: "BFIU Annual Report, FY 2022–23",
  },
  {
    value: "90.8%",
    label: "Share of suspicious activity that originates inside the banking system.",
    source: "BFIU Annual Report",
  },
  {
    value: "61",
    label: "Scheduled banks in Bangladesh. Each one is a blind spot to the others — until now.",
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
    <section className="border-b border-white/5">
      <div className="mx-auto w-full max-w-7xl px-6 py-16 lg:px-10">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map((stat) => (
            <div
              key={stat.value}
              className="rounded-2xl border border-white/10 bg-white/[0.03] p-5 backdrop-blur-sm"
            >
              <p className="font-mono text-3xl tracking-tight text-primary">{stat.value}</p>
              <p className="mt-3 text-sm leading-relaxed text-slate-300">{stat.label}</p>
              <p className="mt-3 text-[11px] uppercase tracking-[0.18em] text-slate-500">
                {stat.source}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
