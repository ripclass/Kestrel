const personas = [
  {
    tag: "Operative",
    title: "BFIU Analysts",
    body: "Unified search across every reporting institution. Case management, disseminations, Egmont-wire intelligence exchange. Network graphs on every subject — no manual drawing.",
  },
  {
    tag: "Reporter",
    title: "Bank CAMLCOs",
    body: "A pattern scanner on your own transactions. STR drafting assisted by AI-detected alerts. Peer-network intelligence without exposing your own book.",
  },
  {
    tag: "Command",
    title: "BFIU Directors",
    body: "National threat dashboard. Bank-by-bank compliance scorecards. Typology trends. Executive briefings generated from live data.",
  },
];

export function PersonaCards() {
  return (
    <section className="border-b border-landing-rule bg-landing-bg">
      <div className="mx-auto w-full max-w-7xl px-6 py-24 lg:px-10">
        <div className="max-w-4xl space-y-6">
          <span className="flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-alarm">
            <span className="leading-none">┼</span> Authorised Access
          </span>
          <h2 className="font-landing-display text-3xl leading-[1.08] text-landing-foreground lg:text-5xl">
            Three personas.
            <br />
            <span className="text-landing-muted">One classified surface.</span>
          </h2>
        </div>
        <div className="mt-16 grid grid-cols-1 border border-landing-rule-solid divide-y divide-landing-rule-solid md:grid-cols-3 md:divide-x md:divide-y-0">
          {personas.map((persona, i) => (
            <div key={persona.title} className="relative flex min-h-[280px] flex-col p-8 lg:p-10">
              <span className="font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-muted">
                {`Class 0${i + 1} · ${persona.tag}`}
              </span>
              <h3 className="mt-6 font-landing-display text-2xl text-landing-foreground">
                {persona.title}
              </h3>
              <p className="mt-4 font-landing-body text-sm leading-relaxed text-landing-foreground/80">
                {persona.body}
              </p>
              <span className="mt-auto pt-8 font-landing-body text-xs text-landing-alarm">┼</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
