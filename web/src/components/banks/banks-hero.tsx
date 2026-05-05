import { IntakeForm } from "@/components/public/intake-form";

export function BanksHero() {
  return (
    <section
      id="access"
      className="relative flex w-full flex-col overflow-hidden border-b border-landing-rule bg-landing-bg pt-24 pb-24 lg:pt-32"
    >
      <div className="relative z-10 mx-auto grid w-full max-w-7xl grid-cols-1 gap-16 px-6 lg:grid-cols-12 lg:gap-8 lg:px-10">
        <div className="col-span-1 flex flex-col space-y-16 lg:col-span-5">
          <div className="flex flex-col space-y-6">
            <span className="flex items-center gap-4 font-landing-body text-xs uppercase tracking-[0.3em] text-landing-alarm">
              <span className="text-lg leading-none">┼</span> For Bangladesh banks
            </span>
            <h1 className="font-landing-display text-4xl leading-[1.05] text-landing-foreground md:text-5xl lg:text-5xl">
              AI transaction monitoring and STR drafting,
              <br />
              <span className="text-landing-muted">deployed in weeks. Billed in BDT.</span>
            </h1>
            <p className="max-w-md font-landing-body text-base leading-relaxed text-landing-foreground/80">
              A real, browser-based AML platform aligned with Bangladesh Bank Circular 26/2024.
              Detection runs against your own transaction file. Alerts surface with explainable
              reasons. STR drafts arrive ready for CAMLCO review.
            </p>
            <div className="grid grid-cols-2 gap-4 pt-2 font-landing-body text-[11px] uppercase tracking-[0.22em] text-landing-foreground/70">
              <span className="flex items-center gap-2">
                <span className="text-landing-alarm">┼</span> 8 production rules
              </span>
              <span className="flex items-center gap-2">
                <span className="text-landing-alarm">┼</span> goAML round-trip
              </span>
              <span className="flex items-center gap-2">
                <span className="text-landing-alarm">┼</span> Cross-bank intel
              </span>
              <span className="flex items-center gap-2">
                <span className="text-landing-alarm">┼</span> BDT denominated
              </span>
            </div>
          </div>

          <IntakeForm />
        </div>

        <div className="relative col-span-1 min-h-[600px] lg:col-span-7 lg:min-h-full">
          <div className="pointer-events-none absolute inset-y-0 left-0 -right-[50vw]">
            <svg
              className="absolute left-0 top-1/2 h-[150%] w-full -translate-y-1/2"
              viewBox="0 0 1000 800"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-label="Stylised bank-direct transaction stream with one alert score crossing the action threshold"
              role="img"
            >
              <path d="M60 200 L940 200" stroke="var(--landing-rule)" strokeWidth="1" />
              <path d="M60 360 L940 360" stroke="var(--landing-rule-solid)" strokeWidth="1" strokeDasharray="2 4" />
              <path d="M60 520 L940 520" stroke="var(--landing-rule)" strokeWidth="1" />
              <path d="M60 680 L940 680" stroke="var(--landing-rule)" strokeWidth="1" />

              <text x="60" y="180" fill="var(--landing-muted)" className="font-landing-body" fontSize="9" letterSpacing="1.5">
                INGEST · NPSB · BEFTN · RTGS · MFS
              </text>
              <text x="60" y="345" fill="var(--landing-muted)" className="font-landing-body" fontSize="9" letterSpacing="1.5">
                ACTION THRESHOLD · SCORE 50
              </text>
              <text x="60" y="505" fill="var(--landing-muted)" className="font-landing-body" fontSize="9" letterSpacing="1.5">
                ALERT SURFACE · ANALYST QUEUE
              </text>
              <text x="60" y="665" fill="var(--landing-muted)" className="font-landing-body" fontSize="9" letterSpacing="1.5">
                STR DRAFT · CAMLCO REVIEW
              </text>

              <circle cx="160" cy="200" r="3" fill="var(--landing-foreground)" />
              <circle cx="240" cy="200" r="3" fill="var(--landing-foreground)" />
              <circle cx="320" cy="200" r="3" fill="var(--landing-foreground)" />
              <circle cx="420" cy="200" r="3" fill="var(--landing-foreground)" />
              <circle cx="520" cy="200" r="3" fill="var(--landing-foreground)" />
              <circle cx="620" cy="200" r="3" fill="var(--landing-foreground)" />
              <circle cx="720" cy="200" r="3" fill="var(--landing-foreground)" />
              <circle cx="820" cy="200" r="3" fill="var(--landing-foreground)" />

              <path
                d="M520 200 L520 360 L520 520 L520 680"
                stroke="var(--landing-alarm)"
                strokeWidth="2"
                strokeDasharray="4 4"
              />
              <circle cx="520" cy="200" r="6" fill="var(--landing-alarm)" />
              <circle cx="520" cy="360" r="14" fill="var(--landing-alarm)" opacity="0.18" />
              <circle cx="520" cy="360" r="6" fill="var(--landing-alarm)" />
              <circle cx="520" cy="520" r="5" fill="var(--landing-alarm)" />
              <circle cx="520" cy="680" r="5" fill="var(--landing-alarm)" />

              <text x="540" y="195" fill="var(--landing-alarm)" className="font-landing-body" fontSize="9" letterSpacing="1.2">
                TXN BDT 9,80,000 · MFS DEBIT
              </text>
              <text x="540" y="355" fill="var(--landing-alarm)" className="font-landing-body" fontSize="9" letterSpacing="1.2">
                SCORE 87 · STRUCTURING + RAPID CASHOUT
              </text>
              <text x="540" y="515" fill="var(--landing-alarm)" className="font-landing-body" fontSize="9" letterSpacing="1.2">
                ALERT · AL-2207 · PRIORITY HIGH
              </text>
              <text x="540" y="675" fill="var(--landing-alarm)" className="font-landing-body" fontSize="9" letterSpacing="1.2">
                STR · DRAFT · CAMLCO QUEUE
              </text>
            </svg>

            <div className="absolute left-[8%] top-[20%] text-xs leading-none text-landing-muted">┼</div>
            <div className="absolute left-[52%] top-[44%] text-xs leading-none text-landing-alarm">┼</div>
            <div className="absolute left-[92%] top-[80%] text-xs leading-none text-landing-muted">┼</div>
          </div>
        </div>
      </div>

      <div className="pointer-events-none absolute inset-0 z-0 bg-[linear-gradient(to_right,var(--landing-rule)_1px,transparent_1px),linear-gradient(to_bottom,var(--landing-rule)_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:linear-gradient(to_bottom,transparent,black,transparent)]" />
    </section>
  );
}
