import Link from "next/link";

const cards: {
  tag: string;
  title: string;
  body: string;
  cta: string;
  href: string;
  external?: boolean;
  highlight?: boolean;
}[] = [
  {
    tag: "For · Commercial banks",
    title: "Run a pilot. Populated workspace in 10 minutes.",
    body:
      "Self-serve signup creates your tenant, fires demo data within ten minutes, and unlocks the full bank-side surface: pattern scanner, AI-drafted STRs, cross-bank intelligence, real-time scoring, and the compliance dashboard. No commitment beyond the pilot window.",
    cta: "Run a pilot →",
    href: "/signup/bank",
    highlight: true,
  },
  {
    tag: "For · Regulators and FIUs",
    title: "Schedule a platform briefing.",
    body:
      "National-scale deployment for FIUs, with the full goAML report lifecycle, IER workflow, and sovereign LLM deployment inside your data centre. Briefings cover the BFIU command view, cross-institutional intelligence, and the contract framework for regulator-grade deployments.",
    cta: "Schedule briefing →",
    href: "/contact?audience=bfiu",
  },
  {
    tag: "For · Integration teams and CTOs",
    title: "Read the docs.",
    body:
      "The integration spec your engineers ship from on a Friday, the security posture your CTO signs off on, and the goAML coverage answer your CAMLCO needs. Three short documents, no registration.",
    cta: "Open the docs →",
    href: "/docs",
  },
];

export function StartHereCards() {
  return (
    <section
      id="access"
      className="border-b border-landing-rule bg-landing-bg"
    >
      <div className="mx-auto w-full max-w-7xl px-6 py-24 lg:px-10">
        <div className="max-w-4xl space-y-6">
          <span className="flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-alarm">
            <span className="leading-none">┼</span> Start here
          </span>
          <h2 className="font-landing-display text-3xl leading-[1.08] text-landing-foreground lg:text-5xl">
            Three ways to evaluate Kestrel.
          </h2>
        </div>

        <div className="mt-16 grid grid-cols-1 gap-px border border-landing-rule-solid bg-landing-rule-solid lg:grid-cols-3">
          {cards.map((card, i) => (
            <article
              key={card.title}
              className={`flex flex-col gap-6 bg-landing-bg p-8 lg:p-10 ${
                card.highlight ? "ring-1 ring-inset ring-landing-alarm" : ""
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-landing-body text-[10px] uppercase tracking-[0.28em] text-landing-muted">
                  {`Path 0${i + 1} · ${card.tag}`}
                </span>
                {card.highlight ? (
                  <span className="font-landing-body text-[10px] uppercase tracking-[0.28em] text-landing-alarm">
                    ┼ Self-serve
                  </span>
                ) : null}
              </div>
              <h3 className="font-landing-display text-2xl leading-tight text-landing-foreground">
                {card.title}
              </h3>
              <p className="font-landing-body text-sm leading-relaxed text-landing-foreground/80">
                {card.body}
              </p>
              {card.external ? (
                <a
                  href={card.href}
                  target="_blank"
                  rel="noreferrer noopener"
                  className={`mt-auto inline-flex items-center justify-center gap-2 px-5 py-3 font-landing-body text-[11px] uppercase tracking-[0.22em] transition ${
                    card.highlight
                      ? "bg-landing-alarm text-landing-bg hover:opacity-90"
                      : "border border-landing-rule-solid text-landing-foreground/85 hover:border-landing-foreground hover:text-landing-foreground"
                  }`}
                >
                  {card.cta}
                </a>
              ) : (
                <Link
                  href={card.href}
                  className={`mt-auto inline-flex items-center justify-center gap-2 px-5 py-3 font-landing-body text-[11px] uppercase tracking-[0.22em] transition ${
                    card.highlight
                      ? "bg-landing-alarm text-landing-bg hover:opacity-90"
                      : "border border-landing-rule-solid text-landing-foreground/85 hover:border-landing-foreground hover:text-landing-foreground"
                  }`}
                >
                  {card.cta}
                </Link>
              )}
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
