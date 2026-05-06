import Link from "next/link";

const tiers: {
  tag: string;
  name: string;
  price: string;
  cadence: string;
  pitch: string;
  groupHeader: string;
  features: string[];
  highlight?: boolean;
  cta: string;
  href: string;
}[] = [
  {
    tag: "Tier 01",
    name: "Starter",
    price: "Tk 60 lakh",
    cadence: "annual · 1 institution",
    pitch:
      "For NBFIs, MFS providers, and smaller banks adopting AI-AML for the first time.",
    groupHeader: "Includes",
    features: [
      "Pattern scanner with 8 detection rules",
      "AI alert explanations",
      "STR drafting from alerts",
      "goAML XML import and export",
      "Cross-bank intelligence (anonymised)",
      "Up to 5 CAMLCO seats",
      "Email support, business hours",
      "Hosted by Kestrel",
      "12-month contract",
    ],
    cta: "Run a pilot →",
    href: "/signup/bank",
  },
  {
    tag: "Tier 02 · Most common",
    name: "Professional",
    price: "Tk 1.5 crore",
    cadence: "annual · 1 institution",
    pitch:
      "For mid-size scheduled commercial banks. Where most pilots convert.",
    groupHeader: "Everything in Starter, plus",
    features: [
      "Real-time transaction scoring API",
      "Sanctions, PEP, adverse-media screening",
      "KYC and CDD automation",
      "Customer screening API",
      "Audit committee compliance dashboard",
      "Up to 15 CAMLCO seats",
      "Priority support, extended hours",
      "Network intelligence (full strength)",
      "12-month contract",
    ],
    highlight: true,
    cta: "Run a pilot →",
    href: "/signup/bank",
  },
  {
    tag: "Tier 03",
    name: "Enterprise",
    price: "Tk 4 crore",
    cadence: "annual · 1 institution",
    pitch:
      "For tier-1 banks and any institution requiring sovereign deployment.",
    groupHeader: "Everything in Professional, plus",
    features: [
      "On-premise deployment in your data centre",
      "Sovereign LLM running locally",
      "Custom rule authoring DSL",
      "Dedicated 24/7 support, named CSM",
      "Source code escrow",
      "Up to 50 CAMLCO seats",
      "24-month contract with 12-month break clause",
      "SLA-backed uptime: 99.9%",
    ],
    cta: "Schedule a briefing →",
    href: "/contact?audience=bfiu",
  },
];

export function PricingTiers() {
  return (
    <section className="border-b border-landing-rule bg-landing-bg">
      <div className="mx-auto w-full max-w-7xl px-6 py-24 lg:px-10">
        <div className="max-w-4xl space-y-6">
          <span className="flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-alarm">
            <span className="leading-none">┼</span> Kestrel · Pricing
          </span>
          <h2 className="font-landing-display text-3xl leading-[1.08] text-landing-foreground lg:text-5xl">
            Three tiers.
            <br />
            BDT-denominated.
            <br />
            <span className="text-landing-muted">No surprises.</span>
          </h2>
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
                <h3 className="font-landing-display text-2xl text-landing-foreground">
                  {tier.name}
                </h3>
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
              <div className="border-t border-landing-rule-solid pt-6">
                <p className="font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-muted">
                  {tier.groupHeader}
                </p>
                <ul className="mt-4 space-y-3">
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
              </div>
              <Link
                href={tier.href}
                className={`mt-auto inline-flex items-center justify-center gap-2 px-5 py-3 font-landing-body text-[11px] uppercase tracking-[0.22em] transition ${
                  tier.highlight
                    ? "bg-landing-alarm text-landing-bg hover:opacity-90"
                    : "border border-landing-rule-solid text-landing-foreground/85 hover:border-landing-foreground hover:text-landing-foreground"
                }`}
              >
                {tier.cta}
              </Link>
            </article>
          ))}
        </div>

        <p className="mt-12 max-w-3xl font-landing-body text-sm leading-relaxed text-landing-foreground/75">
          Implementation services priced separately. First-mover banks pilot at half-price for six
          months in exchange for reference customer status. All pricing is denominated in BDT and
          quoted before any contract is signed.
        </p>
      </div>
    </section>
  );
}
