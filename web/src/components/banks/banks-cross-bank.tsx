const lines: { code: string; line: string }[] = [
  { code: "MATCH · M-0041", line: "Subject reported by 5 banks in 14 days. Aggregate exposure BDT 2.3 crore." },
  { code: "MATCH · M-0038", line: "Phone +880 17·····001 flagged in 3 banks. First / last seen 47 hours apart." },
  { code: "MATCH · M-0029", line: "NID hash 0x4a··e2 returns 3 distinct entities, same canonical owner, two banks." },
];

export function BanksCrossBank() {
  return (
    <section id="cross-bank" className="border-b border-landing-rule bg-landing-bg">
      <div className="mx-auto w-full max-w-7xl px-6 py-24 lg:px-10">
        <div className="grid gap-12 lg:grid-cols-[1.1fr_0.9fr] lg:gap-16">
          <div className="space-y-6">
            <span className="flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-alarm">
              <span className="leading-none">┼</span> Subsection · Cross-bank intelligence
            </span>
            <h2 className="font-landing-display text-4xl leading-[1.05] text-landing-foreground lg:text-6xl">
              The signal
              <br />
              <span className="text-landing-muted">no other vendor has.</span>
            </h2>
            <p className="font-landing-body text-base leading-relaxed text-landing-foreground/85">
              Scam money does not stay inside one bank. It moves across six in twelve minutes.
              Kestrel is the only AML surface in Bangladesh that resolves entities across every
              participating bank — accounts, phones, wallets, NIDs, devices — and surfaces a peer
              warning the moment a counterparty already burned another bank touches yours.
            </p>
            <p className="font-landing-body text-base leading-relaxed text-landing-foreground/85">
              Your own book stays your own. Peer bank names are anonymised before the data leaves
              the engine. Your CAMLCO desk sees a flag, a confidence, and a typology — never a
              competitor&apos;s book. The persona invariants are enforced in the service layer and
              backed by unit tests + Postgres RLS.
            </p>
            <div className="flex flex-wrap gap-4 pt-2">
              <a
                href="/cross-bank-intelligence"
                className="inline-flex items-center gap-2 border border-landing-alarm px-5 py-3 font-landing-body text-[11px] uppercase tracking-[0.22em] text-landing-alarm transition hover:bg-landing-alarm hover:text-landing-bg"
              >
                <span>┼</span> Read the whitepaper →
              </a>
              <a
                href="#access"
                className="inline-flex items-center gap-2 border border-landing-rule-solid px-5 py-3 font-landing-body text-[11px] uppercase tracking-[0.22em] text-landing-foreground/80 transition hover:border-landing-foreground hover:text-landing-foreground"
              >
                Book a 30-minute walkthrough
              </a>
            </div>
          </div>

          <div className="border border-landing-rule-solid">
            <div className="flex items-center justify-between border-b border-landing-rule-solid px-6 py-4">
              <span className="font-landing-body text-[10px] uppercase tracking-[0.28em] text-landing-muted">
                Live cross-bank match log
              </span>
              <span className="font-landing-body text-[10px] uppercase tracking-[0.28em] text-landing-alarm">
                ┼ window 30d
              </span>
            </div>
            <ul>
              {lines.map((entry) => (
                <li
                  key={entry.code}
                  className="flex flex-col gap-2 border-b border-landing-rule-solid p-6 last:border-b-0"
                >
                  <span className="font-landing-body text-[11px] uppercase tracking-[0.22em] text-landing-alarm">
                    {entry.code}
                  </span>
                  <span className="font-landing-body text-sm leading-relaxed text-landing-foreground/85">
                    {entry.line}
                  </span>
                </li>
              ))}
              <li className="flex items-center justify-between p-6 font-landing-body text-[10px] uppercase tracking-[0.28em] text-landing-muted">
                <span>┼ peer bank names redacted for non-regulator personas</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
