import Link from "next/link";

type CommercialTier = {
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
};

const commercialTiers: CommercialTier[] = [
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
    cta: "Run a pilot →",
    href: "/signup/bank",
  },
];

const regulatorTier = {
  tag: "Tier 04 · Regulator",
  name: "Regulator",
  subtitle: "National infrastructure",
  pitch:
    "For national financial intelligence units, central banks, and supervisory authorities deploying Kestrel as shared infrastructure across an entire banking system.",
  groupHeader: "Bespoke deployment includes",
  features: [
    "Multi-year contract, scope-priced",
    "On-premise default, in your data centre",
    "Sovereign LLM running on your infrastructure",
    "Dedicated technical account management",
    "On-site implementation and analyst training",
    "Custom rule authoring + national-typology library",
    "Direct access to platform engineering",
    "Pricing structured around scope of deployment and not published publicly",
  ],
  cta: "Request proposal →",
  href: "/contact?audience=regulator",
};

export function PricingTiers() {
  return (
    <section className="border-b border-landing-rule bg-landing-bg">
      <div className="mx-auto w-full max-w-7xl px-6 py-24 lg:px-10">
        <div className="max-w-4xl space-y-6">
          <span className="flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-alarm">
            <span className="leading-none">┼</span> Kestrel · Pricing
          </span>
          <h2 className="font-landing-display text-3xl leading-[1.08] text-landing-foreground lg:text-5xl">
            Four tiers.
            <br />
            BDT-denominated for banks.
            <br />
            <span className="text-landing-muted">Quoted bespoke for regulators.</span>
          </h2>
        </div>

        <div className="mt-16 flex flex-col gap-3 border-l-2 border-landing-alarm pl-6">
          <span className="font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-alarm">
            ┼ Commercial tiers
          </span>
          <p className="max-w-2xl font-landing-body text-sm leading-relaxed text-landing-foreground/80">
            For banks, NBFIs, and MFS providers. National regulator deployments are structured
            separately — see Tier 04 below.
          </p>
        </div>

        <div className="mt-8 grid grid-cols-1 gap-px border border-landing-rule-solid bg-landing-rule-solid lg:grid-cols-3">
          {commercialTiers.map((tier) => (
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

        <div className="mt-16 flex flex-col gap-3 border-l-2 border-landing-foreground/40 pl-6">
          <span className="font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-foreground/70">
            ┼ Regulator tier
          </span>
          <p className="max-w-2xl font-landing-body text-sm leading-relaxed text-landing-foreground/80">
            For BFIU, peer FIUs, central banks, and supervisory authorities. Priced bespoke
            against scope of deployment, not against a public sticker.
          </p>
        </div>

        <article className="mt-8 grid grid-cols-1 gap-10 border border-landing-rule-solid bg-landing-bg p-8 lg:grid-cols-3 lg:p-12">
          <div className="space-y-6 lg:col-span-2">
            <div className="flex flex-col gap-3">
              <span className="font-landing-body text-[10px] uppercase tracking-[0.28em] text-landing-muted">
                {regulatorTier.tag}
              </span>
              <h3 className="font-landing-display text-3xl leading-tight text-landing-foreground lg:text-4xl">
                {regulatorTier.name}
                <br />
                <span className="text-landing-muted">{regulatorTier.subtitle}</span>
              </h3>
            </div>
            <p className="max-w-2xl font-landing-body text-base leading-relaxed text-landing-foreground/85">
              {regulatorTier.pitch}
            </p>
            <Link
              href={regulatorTier.href}
              className="inline-flex items-center gap-3 border border-landing-foreground px-6 py-4 font-landing-body text-sm uppercase tracking-[0.22em] text-landing-foreground transition hover:bg-landing-foreground hover:text-landing-bg"
            >
              {regulatorTier.cta}
            </Link>
          </div>

          <div className="border-t border-landing-rule-solid pt-6 lg:border-l lg:border-t-0 lg:pl-10 lg:pt-0">
            <p className="font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-muted">
              {regulatorTier.groupHeader}
            </p>
            <ul className="mt-4 space-y-3">
              {regulatorTier.features.map((line) => (
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
        </article>

        <p className="mt-12 max-w-3xl font-landing-body text-sm leading-relaxed text-landing-foreground/75">
          Commercial tiers: implementation services priced separately. First-mover banks pilot at
          half-price for six months in exchange for reference customer status. All BDT pricing is
          quoted in writing before any contract is signed.
        </p>
      </div>
    </section>
  );
}
