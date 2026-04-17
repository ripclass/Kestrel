const steps: { n: string; title: string; body: string }[] = [
  {
    n: "01",
    title: "Ingest",
    body: "Banks submit STRs, SARs, and CTRs through their existing goAML-format XML pipelines — or directly via Kestrel\u2019s web forms. Bulk upload, round-trip XML, supplements, and additional-information files are all first-class.",
  },
  {
    n: "02",
    title: "Resolve",
    body: "Every subject — account, phone, wallet, NID, device — is resolved against Kestrel\u2019s shared entity pool. Duplicates merge. Cross-bank matches surface automatically whenever a second institution reports the same identifier.",
  },
  {
    n: "03",
    title: "Detect",
    body: "Eight tuned detection rules run continuously: rapid cashout, fan-in and fan-out bursts, dormant spike, layering, structuring, proximity-to-flagged, first-time high-value. Each hit is weighted, scored, and explained.",
  },
  {
    n: "04",
    title: "Act",
    body: "Analysts triage alerts, open cases, disseminate to law enforcement, and exchange intelligence with foreign FIUs — all from one interface, all audit-logged under the Money Laundering Prevention Act.",
  },
];

export function HowItWorks() {
  return (
    <section id="how" className="border-b border-white/5">
      <div className="mx-auto w-full max-w-7xl px-6 py-24 lg:px-10">
        <div className="max-w-3xl space-y-4">
          <p className="text-xs uppercase tracking-[0.28em] text-primary">How it works</p>
          <h2 className="text-3xl font-semibold tracking-tight text-white lg:text-4xl">
            Four steps from report to dissemination.
          </h2>
        </div>
        <div className="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {steps.map((step) => (
            <div
              key={step.n}
              className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 backdrop-blur-sm"
            >
              <p className="font-mono text-xs tracking-[0.22em] text-primary">{step.n}</p>
              <h3 className="mt-3 text-lg font-semibold text-white">{step.title}</h3>
              <p className="mt-3 text-sm leading-relaxed text-slate-300">{step.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
