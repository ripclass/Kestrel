import { ArrowUpRight, Check } from "lucide-react";

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
    <section className="border-b border-white/5">
      <div className="mx-auto w-full max-w-7xl px-6 py-24 lg:px-10">
        <div className="max-w-3xl space-y-4">
          <p className="text-xs uppercase tracking-[0.28em] text-primary">Coverage</p>
          <h2 className="text-3xl font-semibold tracking-tight text-white lg:text-4xl">
            Everything goAML does. Plus the ten things goAML can&apos;t.
          </h2>
          <p className="text-lg italic text-slate-400">
            goAML is the filing cabinet. Kestrel is the detective.
          </p>
        </div>

        <div className="mt-12 grid gap-8 lg:grid-cols-2">
          <div className="space-y-4 text-base leading-relaxed text-slate-300">
            <p>
              Kestrel mirrors every goAML workflow that matters: STR, SAR, CTR, TBML, Complaint, IER,
              Adverse Media, Escalated reports, Additional Information Files, Catalogue Search,
              Disseminations, Match Definitions, Reference Tables, and Statistics. Banks keep their
              existing XML pipelines unchanged — import and export round-trip cleanly.
            </p>
            <p>
              On top of that, Kestrel adds the capabilities a filing cabinet could never deliver: a
              live, shared, explainable intelligence surface that works while the money is still in
              motion.
            </p>
            <a
              href="https://github.com/ripclass/Kestrel/blob/main/docs/goaml-coverage.md"
              target="_blank"
              rel="noreferrer noopener"
              className="inline-flex items-center gap-1 text-sm font-medium text-primary transition hover:text-white"
            >
              View the full coverage map
              <ArrowUpRight className="h-4 w-4" />
            </a>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 backdrop-blur-sm">
            <p className="text-xs uppercase tracking-[0.22em] text-primary">Kestrel ships with</p>
            <ul className="mt-4 space-y-3">
              {uniqueCapabilities.map((item) => (
                <li key={item} className="flex items-start gap-3 text-sm leading-relaxed text-slate-200">
                  <Check className="mt-0.5 h-4 w-4 flex-none text-primary" aria-hidden />
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
