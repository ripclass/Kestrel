const tiers: {
  tag: string;
  name: string;
  price: string;
  cadence: string;
  pitch: string;
  features: string[];
  highlight?: boolean;
  cta: string;
}[] = [
  {
    tag: "Tier 01 · Starter",
    name: "Starter",
    price: "Tk 60 lakh",
    cadence: "annual · 1 institution",
    pitch:
      "The smallest banks. Daily batch monitoring, AI-assisted alert review, goAML round-trip.",
    features: [
      "8 production detection rules",
      "Nightly scan of your transaction file",
      "AI-explained alerts (Claude Sonnet 4.6)",
      "Draft STR generator (goAML XML export)",
      "5 user seats included",
      "goAML XML import + export",
      "Standard email support · Bangladesh hours",
    ],
    cta: "Request Starter brief",
  },
  {
    tag: "Tier 02 · Professional",
    name: "Professional",
    price: "Tk 1.5 crore",
    cadence: "annual · 1 institution",
    pitch:
      "Mid-sized banks running an active CAMLCO desk. Cross-bank intelligence layer included.",
    features: [
      "Everything in Starter, plus —",
      "Cross-bank intelligence (peer-anonymised)",
      "Custom rule authoring via JSON DSL",
      "Match definitions and saved queries",
      "Network graph and 2-hop dossier on every subject",
      "20 user seats included",
      "Priority Slack / email support",
    ],
    highlight: true,
    cta: "Request Professional brief",
  },
  {
    tag: "Tier 03 · Enterprise",
    name: "Enterprise",
    price: "Tk 4 crore",
    cadence: "annual · 1 institution",
    pitch:
      "The largest banks and the ones moving toward real-time core-banking integration.",
    features: [
      "Everything in Professional, plus —",
      "Real-time scoring API · sub-500ms p99",
      "Dedicated solutions engineer",
      "Custom typology library tuned to your portfolio",
      "Adverse-media + sanctions screening (when GA)",
      "Unlimited user seats",
      "99.9% SLA · 24×7 incident channel",
      "On-prem / VPC deployment option",
    ],
    cta: "Request Enterprise brief",
  },
];

export function BanksPricing() {
  return (
    <section id="pricing" className="border-b border-landing-rule bg-landing-bg">
      <div className="mx-auto w-full max-w-7xl px-6 py-24 lg:px-10">
        <div className="max-w-4xl space-y-6">
          <span className="flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-alarm">
            <span className="leading-none">┼</span> Subsection · Procurement
          </span>
          <h2 className="font-landing-display text-3xl leading-[1.08] text-landing-foreground lg:text-5xl">
            Three tiers. BDT-denominated.
            <br />
            <span className="text-landing-muted">No surprise FX.</span>
          </h2>
          <p className="font-landing-body text-base leading-relaxed text-landing-foreground/80">
            Annual licence per institution. No per-transaction metering on Starter or Professional.
            Enterprise meters the real-time scoring API only. Procurement-ready quotation issued
            within 5 working days of a signed NDA.
          </p>
        </div>

        <div className="mt-16 grid grid-cols-1 gap-px border border-landing-rule-solid bg-landing-rule-solid lg:grid-cols-3">
          {tiers.map((tier) => (
            <article
              key={tier.name}
              className={`flex flex-col gap-6 bg-landing-bg p-8 lg:p-10 ${
                tier.highlight ? "ring-1 ring-inset ring-landing-alarm" : ""
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-landing-body text-[10px] uppercase tracking-[0.28em] text-landing-muted">
                  {tier.tag}
                </span>
                {tier.highlight ? (
                  <span className="font-landing-body text-[10px] uppercase tracking-[0.28em] text-landing-alarm">
                    ┼ Recommended
                  </span>
                ) : null}
              </div>
              <div className="space-y-2">
                <p className="font-landing-display text-4xl leading-none text-landing-foreground">
                  {tier.price}
                </p>
                <p className="font-landing-body text-[11px] uppercase tracking-[0.22em] text-landing-muted">
                  {tier.cadence}
                </p>
              </div>
              <p className="font-landing-body text-sm leading-relaxed text-landing-foreground/80">
                {tier.pitch}
              </p>
              <ul className="space-y-3 border-t border-landing-rule-solid pt-6">
                {tier.features.map((line) => (
                  <li
                    key={line}
                    className="flex items-start gap-3 font-landing-body text-[13px] leading-relaxed text-landing-foreground/85"
                  >
                    <span className="pt-0.5 leading-none text-landing-alarm">┼</span>
                    <span>{line}</span>
                  </li>
                ))}
              </ul>
              <a
                href="#access"
                className={`mt-auto inline-flex items-center justify-center gap-2 px-5 py-3 font-landing-body text-[11px] uppercase tracking-[0.22em] transition ${
                  tier.highlight
                    ? "bg-landing-alarm text-landing-bg hover:opacity-90"
                    : "border border-landing-rule-solid text-landing-foreground/85 hover:border-landing-foreground hover:text-landing-foreground"
                }`}
              >
                {tier.cta}
              </a>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
