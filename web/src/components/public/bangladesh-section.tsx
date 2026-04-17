export function BangladeshSection() {
  return (
    <section className="border-b border-white/5">
      <div className="mx-auto w-full max-w-7xl px-6 py-24 lg:px-10">
        <div className="grid gap-10 lg:grid-cols-[0.7fr_1.3fr] lg:items-start">
          <div>
            <p className="text-xs uppercase tracking-[0.28em] text-primary">Built in Bangladesh</p>
            <h2 className="mt-4 text-3xl font-semibold tracking-tight text-white lg:text-4xl">
              Local by design.
            </h2>
          </div>
          <p className="text-lg leading-relaxed text-slate-300">
            Kestrel is built for Bangladesh. BDT-native. Bangla-ready. Every rule is tuned to local
            channels — NPSB, BEFTN, RTGS, bKash, Nagad, Rocket. Every threshold respects local
            regulation. Every typology in the library is modelled on real Bangladesh scam patterns —
            from click-and-earn mule networks to hundi-style cross-border settlement to TBML
            under-invoicing.
          </p>
        </div>
      </div>
    </section>
  );
}
