const obligations: { code: string; line: string }[] = [
  {
    code: "Obligation · 01",
    line:
      "Risk-based transaction monitoring with documented rules, thresholds, and reasoning. Kestrel ships 8 rules with YAML definitions, weighted scoring, and per-hit traces.",
  },
  {
    code: "Obligation · 02",
    line:
      "Timely STR submission to BFIU in goAML XML. Kestrel imports goAML XML from existing pipelines and exports STR / SAR / CTR / TBML / IER / 5 more variants in goAML-compliant XML.",
  },
  {
    code: "Obligation · 03",
    line:
      "Auditable analyst workflow with immutable evidence trail. Kestrel writes every action to an append-only audit log; STR drafts, edits, submissions, and dispositions are all timestamped and attributed.",
  },
  {
    code: "Obligation · 04",
    line:
      "Cross-institutional intelligence sharing where permitted. Kestrel resolves entities across participating banks with peer-anonymised views and BFIU-only full-data access.",
  },
];

export function BanksCircularCallout() {
  return (
    <section className="border-b border-landing-rule bg-landing-bg">
      <div className="mx-auto w-full max-w-7xl px-6 py-24 lg:px-10">
        <div className="grid gap-12 lg:grid-cols-[0.9fr_1.1fr] lg:gap-20">
          <div className="space-y-5">
            <span className="flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-alarm">
              <span className="leading-none">┼</span> Regulatory anchor
            </span>
            <h2 className="font-landing-display text-4xl leading-[1.05] text-landing-foreground lg:text-6xl">
              Bangladesh Bank
              <br />
              <span className="text-landing-muted">Circular 26 / 2024.</span>
            </h2>
            <p className="font-landing-body text-base leading-relaxed text-landing-foreground/80">
              The 2024 AML/CFT modernisation cycle pushes scheduled banks toward risk-based
              monitoring, faster STR cycles, and higher-fidelity analyst evidence. Kestrel was
              built around those obligations from day one — not retrofitted to them.
            </p>
            <p className="font-landing-body text-[11px] uppercase tracking-[0.22em] text-landing-muted">
              Reference · BB Circular 26/2024 · AML/CFT instructions for scheduled banks
            </p>
          </div>
          <div className="border border-landing-rule-solid">
            <div className="border-b border-landing-rule-solid px-8 py-5 lg:px-10">
              <span className="font-landing-body text-[10px] uppercase tracking-[0.28em] text-landing-muted">
                ┼ How Kestrel satisfies it
              </span>
            </div>
            <ul>
              {obligations.map((row) => (
                <li
                  key={row.code}
                  className="flex flex-col gap-2 border-b border-landing-rule-solid p-8 last:border-b-0 lg:p-10"
                >
                  <span className="font-landing-body text-[11px] uppercase tracking-[0.22em] text-landing-alarm">
                    {row.code}
                  </span>
                  <p className="font-landing-body text-sm leading-relaxed text-landing-foreground/85">
                    {row.line}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
