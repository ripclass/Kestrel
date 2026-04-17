import { IntakeForm } from "./intake-form";

export function LandingHero() {
  return (
    <section
      id="access"
      className="relative flex w-full flex-col overflow-hidden border-b border-landing-rule bg-landing-bg pt-24 pb-24 lg:pt-32"
    >
      <div className="relative z-10 mx-auto grid w-full max-w-7xl grid-cols-1 gap-16 px-6 lg:grid-cols-12 lg:gap-8 lg:px-10">
        <div className="col-span-1 flex flex-col space-y-16 lg:col-span-5">
          <div className="flex flex-col space-y-6">
            <span className="flex items-center gap-4 font-landing-body text-xs uppercase tracking-[0.3em] text-landing-alarm">
              <span className="text-lg leading-none">┼</span> Kestrel Intelligence
            </span>
            <h1 className="font-landing-display text-4xl leading-[1.05] text-landing-foreground md:text-5xl lg:text-5xl">
              Scam money moves across six banks in twelve minutes.
              <br />
              <span className="text-landing-muted">Your analyst finds out six weeks later.</span>
            </h1>
            <p className="max-w-md font-landing-body text-base leading-relaxed text-landing-foreground/80">
              Kestrel connects every suspicious transaction report, every flagged account, and every
              money trail across every bank into one real-time intelligence picture.
            </p>
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
              aria-label="Edge-to-edge cross-bank network graph with flagged nodes highlighted in alarm vermillion"
              role="img"
            >
              <path d="M100 400 L800 400" stroke="var(--landing-rule)" strokeWidth="1" />
              <path d="M300 200 L300 600" stroke="var(--landing-rule)" strokeWidth="1" />
              <path d="M100 400 L300 200 L500 400 L800 600" stroke="var(--landing-rule)" strokeWidth="1" />
              <path d="M500 400 L500 700" stroke="var(--landing-rule)" strokeWidth="1" />

              <circle cx="100" cy="400" r="4" fill="var(--landing-foreground)" />
              <circle cx="300" cy="200" r="4" fill="var(--landing-foreground)" />
              <circle cx="500" cy="700" r="4" fill="var(--landing-foreground)" />
              <circle cx="800" cy="600" r="4" fill="var(--landing-foreground)" />

              <circle cx="300" cy="600" r="12" fill="var(--landing-alarm)" opacity="0.2" />
              <circle cx="300" cy="600" r="6" fill="var(--landing-alarm)" />
              <circle cx="500" cy="400" r="16" fill="var(--landing-alarm)" opacity="0.1" />
              <circle cx="500" cy="400" r="4" fill="var(--landing-alarm)" />
              <circle cx="800" cy="400" r="4" fill="var(--landing-alarm)" />

              <path
                d="M300 600 L500 400 L800 400"
                stroke="var(--landing-alarm)"
                strokeWidth="2"
                strokeDasharray="4 4"
              />

              <text x="320" y="605" fill="var(--landing-alarm)" className="font-landing-body" fontSize="10" letterSpacing="1">
                FLG · SMURFING · CONF 92%
              </text>
              <text x="520" y="395" fill="var(--landing-alarm)" className="font-landing-body" fontSize="10" letterSpacing="1">
                FLG · E-COM GATEWAY
              </text>
              <text x="320" y="195" fill="var(--landing-muted)" className="font-landing-body" fontSize="10" letterSpacing="1">
                NODE · COMMERCIAL BANK
              </text>

              <path d="M500 400 L1000 400" stroke="var(--landing-rule-solid)" strokeWidth="1" />
              <text x="900" y="390" fill="var(--landing-muted)" className="font-landing-body" fontSize="8" letterSpacing="1">
                TRACE AL-449
              </text>
            </svg>

            <div className="absolute left-[30%] top-[20%] text-xs leading-none text-landing-muted">┼</div>
            <div className="absolute left-[80%] top-[80%] text-xs leading-none text-landing-muted">┼</div>
            <div className="absolute left-[10%] top-[40%] text-xs leading-none text-landing-alarm">┼</div>
          </div>
        </div>
      </div>

      <div className="pointer-events-none absolute inset-0 z-0 bg-[linear-gradient(to_right,var(--landing-rule)_1px,transparent_1px),linear-gradient(to_bottom,var(--landing-rule)_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:linear-gradient(to_bottom,transparent,black,transparent)]" />
    </section>
  );
}
