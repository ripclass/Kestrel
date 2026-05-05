const features: {
  tag: string;
  title: string;
  body: string;
  hits: { code: string; line: string }[];
}[] = [
  {
    tag: "Module · Pattern scanner",
    title: "8 detection rules, batched or real-time.",
    body:
      "Eight production rules tuned for Bangladesh: rapid cashout, fan-in burst, fan-out burst, structuring, layering, first-time high value, dormant spike, proximity to flagged. Run nightly across your portfolio or call the scoring API per transaction.",
    hits: [
      { code: "RUL · STRUCTURING", line: "9× BDT 4.95 lakh deposits in 14 days" },
      { code: "RUL · RAPID CASHOUT", line: "credit BDT 12 lakh → 6× MFS debit < 60 min" },
      { code: "RUL · FAN-IN BURST", line: "47 unique senders → one current account / 7d" },
    ],
  },
  {
    tag: "Module · AI explanation",
    title: "Every alert ships with an analyst-ready narrative.",
    body:
      "Claude Sonnet 4.6, routed via OpenRouter, transforms rule hits + entity context into the kind of paragraph an analyst would write at the start of an STR. Names redacted at the prompt boundary; full audit trail on every model call.",
    hits: [
      { code: "ALERT · AL-2207", line: "Subject Mohammad K. moved BDT 38 lakh through 4 banks in 12 minutes…" },
      { code: "ALERT · AL-1944", line: "Account 71****0182 received 47 micro-deposits matching mule-network typology…" },
      { code: "ALERT · AL-1812", line: "Dormant savings account reactivated; BDT 6.2 lakh debited within 38 hours…" },
    ],
  },
  {
    tag: "Module · STR drafting",
    title: "Draft STR generated from the alert, not from a blank page.",
    body:
      "One click on a flagged alert produces a populated draft STR — subjects resolved, accounts attached, narrative pre-written, typology pre-tagged. CAMLCO reviews, edits, and submits. goAML XML is the export format Bangladesh Bank already accepts.",
    hits: [
      { code: "STR · DRAFT · A2207", line: "Suspicious activity report · structuring · 2 subjects · 9 transactions" },
      { code: "STR · DRAFT · A1944", line: "Suspicious activity report · mule network · 1 subject · 47 txns" },
      { code: "STR · DRAFT · A1812", line: "Suspicious activity report · dormant-spike · 1 subject · 6 txns" },
    ],
  },
];

export function BanksFeatures() {
  return (
    <section id="features" className="border-b border-landing-rule bg-landing-bg">
      <div className="mx-auto w-full max-w-7xl px-6 py-24 lg:px-10">
        <div className="max-w-4xl space-y-6">
          <span className="flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-alarm">
            <span className="leading-none">┼</span> Subsection · Capability
          </span>
          <h2 className="font-landing-display text-3xl leading-[1.08] text-landing-foreground lg:text-5xl">
            What your CAMLCO desk gets on day one.
          </h2>
          <p className="font-landing-body text-base leading-relaxed text-landing-foreground/80">
            Three modules. Each replaces a manual workflow that today eats analyst hours and lets
            real signal slip through. All three are live in the platform now — not on a roadmap.
          </p>
        </div>

        <div className="mt-16 grid grid-cols-1 border border-landing-rule-solid divide-y divide-landing-rule-solid lg:grid-cols-3 lg:divide-x lg:divide-y-0">
          {features.map((feature, i) => (
            <div key={feature.title} className="flex flex-col gap-6 p-8 lg:p-10">
              <span className="font-landing-body text-[10px] uppercase tracking-[0.28em] text-landing-muted">
                {`0${i + 1} · ${feature.tag}`}
              </span>
              <h3 className="font-landing-display text-2xl leading-tight text-landing-foreground">
                {feature.title}
              </h3>
              <p className="font-landing-body text-sm leading-relaxed text-landing-foreground/80">
                {feature.body}
              </p>
              <div className="mt-auto border-t border-landing-rule-solid pt-6">
                <p className="font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-muted">
                  Sample hits
                </p>
                <ul className="mt-4 space-y-3">
                  {feature.hits.map((hit) => (
                    <li
                      key={hit.code}
                      className="flex flex-col gap-1 font-landing-body text-[11px] leading-relaxed text-landing-foreground/85"
                    >
                      <span className="uppercase tracking-[0.18em] text-landing-alarm">{hit.code}</span>
                      <span className="text-landing-foreground/75">{hit.line}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
