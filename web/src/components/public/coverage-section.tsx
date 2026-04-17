const uniqueCapabilities = [
  "AI alert explanations that translate rule hits into analyst-ready narratives",
  "Automatic cross-bank entity resolution across accounts, phones, wallets, NIDs, devices",
  "Two-hop network graphs on every subject, rendered without manual drawing",
  "Explainable risk scoring with per-rule weights, hit traces, and contribution breakdowns",
  "Compliance benchmarking and executive dashboards across every reporting institution",
  "Modern web interface accessible from any browser — no legacy desktop client",
];

export function CoverageSection() {
  return (
    <section id="coverage" className="border-b border-landing-rule bg-landing-bg">
      <div className="mx-auto w-full max-w-7xl px-6 py-24 lg:px-10">
        <div className="max-w-4xl space-y-6">
          <span className="flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-alarm">
            <span className="leading-none">┼</span> Subsection · Coverage
          </span>
          <h2 className="font-landing-display text-3xl leading-[1.08] text-landing-foreground lg:text-5xl">
            Everything goAML does.
            <br />
            <span className="text-landing-muted">Plus the ten things goAML can&apos;t.</span>
          </h2>
          <p className="font-landing-body text-lg italic text-landing-muted">
            goAML is the filing cabinet. Kestrel is the detective.
          </p>
        </div>

        <div className="mt-16 grid grid-cols-1 border border-landing-rule-solid divide-y divide-landing-rule-solid lg:grid-cols-2 lg:divide-x lg:divide-y-0">
          <div className="space-y-6 p-8 font-landing-body text-base leading-relaxed text-landing-foreground/85 lg:p-12">
            <p>
              Kestrel mirrors every goAML workflow that matters — STR, SAR, CTR, TBML, Complaint, IER,
              Adverse Media, Escalated reports, Additional Information Files, Catalogue Search,
              Disseminations, Match Definitions, Reference Tables, Statistics. Banks keep their existing
              XML pipelines unchanged. Import and export round-trip cleanly.
            </p>
            <p>
              On top of that, Kestrel delivers what a filing cabinet cannot: a live, shared, explainable
              intelligence surface that works while the money is still in motion.
            </p>
            <a
              href="https://github.com/ripclass/Kestrel/blob/main/docs/goaml-coverage.md"
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex items-center gap-2 border-b border-landing-alarm pb-0.5 font-landing-body text-xs uppercase tracking-[0.22em] text-landing-alarm transition hover:border-landing-foreground hover:text-landing-foreground"
            >
              View full coverage map ↗
            </a>
          </div>
          <div className="p-8 lg:p-12">
            <p className="font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-muted">
              Kestrel ships with
            </p>
            <ul className="mt-6 space-y-4">
              {uniqueCapabilities.map((item) => (
                <li
                  key={item}
                  className="flex items-start gap-4 font-landing-body text-sm leading-relaxed text-landing-foreground"
                >
                  <span className="pt-0.5 font-landing-display leading-none text-landing-alarm">┼</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
