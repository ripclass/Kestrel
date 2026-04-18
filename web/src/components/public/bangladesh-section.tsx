const channelTags = ["NPSB", "BEFTN", "RTGS", "bKash", "Nagad", "Rocket", "BDT", "Bangla"];

export function BangladeshSection() {
  return (
    <section className="border-b border-landing-rule bg-landing-bg">
      <div className="mx-auto w-full max-w-7xl px-6 py-24 lg:px-10">
        <div className="grid gap-12 lg:grid-cols-[0.9fr_1.1fr] lg:gap-20">
          <div className="space-y-5">
            <span className="flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-alarm">
              <span className="leading-none">┼</span> Jurisdiction
            </span>
            <h2 className="font-landing-display text-4xl leading-[1.05] text-landing-foreground lg:text-6xl">
              Local by
              <br />
              <span className="text-landing-muted">design.</span>
            </h2>
          </div>
          <div className="space-y-6 font-landing-body text-base leading-relaxed text-landing-foreground/85 lg:text-lg">
            <p>
              Kestrel is built for Bangladesh. BDT-native. Bangla-ready. Tuned to the channels an
              analyst actually sees — NPSB, BEFTN, RTGS, bKash, Nagad, Rocket.
            </p>
            <p>
              Every threshold respects local regulation. Every typology in the library is modelled on
              real Bangladesh scam patterns: click-and-earn mule networks, hundi-style cross-border
              settlement, TBML under-invoicing.
            </p>
            <div className="flex flex-wrap gap-2 pt-4">
              {channelTags.map((tag) => (
                <span
                  key={tag}
                  className="border border-landing-rule-solid px-3 py-1 font-landing-body text-[11px] uppercase tracking-[0.22em] text-landing-foreground/80"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
