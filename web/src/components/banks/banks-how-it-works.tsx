const steps: { code: string; title: string; body: string }[] = [
  {
    code: "Step 01 · Ingest",
    title: "Upload your transactions.",
    body:
      "CSV, XLSX, or goAML XML. NPSB, BEFTN, RTGS, MFS, cash, cheque, card, wire — whatever your core system speaks. The same parser feeds the nightly scan and the upload-a-file path.",
  },
  {
    code: "Step 02 · Score",
    title: "AI scans the file.",
    body:
      "Eight detection rules run across every account in the batch. Entities resolve across past and present scans. The scorer produces a 0-100 risk number with per-rule contributions you can defend in writing.",
  },
  {
    code: "Step 03 · Surface",
    title: "Alerts arrive in the queue.",
    body:
      "Anything past the action threshold lands on the analyst queue with severity, evidence, and a Claude-written narrative. Cross-bank matches show as an extra flag; the dossier is one click away.",
  },
  {
    code: "Step 04 · Draft",
    title: "STRs draft themselves.",
    body:
      "From the alert, your CAMLCO triggers a draft STR — subjects resolved, accounts attached, typology pre-tagged, narrative pre-written. Review, edit, submit. goAML XML on the way out.",
  },
];

export function BanksHowItWorks() {
  return (
    <section id="how-it-works" className="border-b border-landing-rule bg-landing-bg">
      <div className="mx-auto w-full max-w-7xl px-6 py-24 lg:px-10">
        <div className="max-w-4xl space-y-6">
          <span className="flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-alarm">
            <span className="leading-none">┼</span> Subsection · Operating loop
          </span>
          <h2 className="font-landing-display text-3xl leading-[1.08] text-landing-foreground lg:text-5xl">
            Four steps from raw transaction to filed STR.
          </h2>
        </div>

        <ol className="mt-16 grid grid-cols-1 border border-landing-rule-solid divide-y divide-landing-rule-solid md:grid-cols-2 md:divide-x lg:grid-cols-4 lg:divide-y-0">
          {steps.map((step) => (
            <li key={step.code} className="flex min-h-[280px] flex-col gap-5 p-8 lg:p-10">
              <span className="font-landing-body text-[10px] uppercase tracking-[0.28em] text-landing-muted">
                {step.code}
              </span>
              <h3 className="font-landing-display text-xl leading-tight text-landing-foreground lg:text-2xl">
                {step.title}
              </h3>
              <p className="font-landing-body text-sm leading-relaxed text-landing-foreground/80">
                {step.body}
              </p>
              <span className="mt-auto font-landing-body text-xs text-landing-alarm">┼</span>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
