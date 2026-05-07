export function LandingHero() {
  return (
    <section
      id="hero"
      className="relative flex w-full flex-col overflow-hidden border-b border-landing-rule bg-landing-bg pt-24 pb-24 lg:pt-32"
    >
      <div className="relative z-10 mx-auto grid w-full max-w-7xl grid-cols-1 gap-16 px-6 lg:grid-cols-12 lg:gap-8 lg:px-10">
        <div className="col-span-1 flex flex-col space-y-10 lg:col-span-5">
          <div className="flex flex-col space-y-6">
            <span className="flex items-center gap-4 font-landing-body text-xs uppercase tracking-[0.3em] text-landing-alarm">
              <span className="text-lg leading-none">┼</span> Kestrel — Financial Crime Intelligence
            </span>
            <h1 className="font-landing-display text-4xl leading-[1.05] text-landing-foreground md:text-5xl lg:text-5xl">
              Financial crime
              <br />
              intelligence
              <br />
              for Bangladesh&apos;s
              <br />
              <span className="text-landing-muted">banks.</span>
            </h1>
            <p className="max-w-md font-landing-body text-base leading-relaxed text-landing-foreground/80">
              Pattern detection, cross-bank entity intelligence, AI-drafted STRs, real-time
              transaction scoring, and goAML interoperability. Billable in BDT, deployable on local
              infrastructure, ready to demonstrate today.
            </p>
          </div>

          <div className="space-y-4 border-t border-landing-rule-solid pt-8">
            <span className="font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-muted">
              Field note
            </span>
            <p className="max-w-md font-landing-body text-base leading-relaxed text-landing-foreground/85">
              Scam money moves across six banks in twelve minutes. Your CAMLCO sees only what passed
              through your bank. Kestrel adds the intelligence layer above, with anonymised
              cross-bank signal, AI-assisted investigation, and BFIU-ready reporting that
              complements every system you already run.
            </p>
          </div>
        </div>

        <div
          aria-hidden
          className="relative col-span-1 hidden lg:block lg:col-span-7 lg:min-h-full"
        >
          <div className="absolute -top-2 left-2 z-10 flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-muted">
            <span className="text-landing-alarm">┼</span>
            <span>Schematic · Cross-bank cluster</span>
          </div>
          <div className="pointer-events-none absolute inset-y-0 left-0 -right-[50vw]">
            <svg
              className="absolute left-0 top-1/2 h-[150%] w-full -translate-y-1/2"
              viewBox="0 0 1000 800"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-label="Schematic of a cross-bank entity cluster — institution nodes ping outward in sequence as if the network were polling, with a vermillion suspicious-flow path animating along its dashed edge."
              role="img"
            >
              <style>{`
                .kx-node-ping {
                  fill: var(--landing-foreground);
                  animation: kxPing 5s ease-out infinite;
                  transform-box: fill-box;
                  transform-origin: center;
                }
                .kx-node-ping-1 { animation-delay: 0s; }
                .kx-node-ping-2 { animation-delay: 1.25s; }
                .kx-node-ping-3 { animation-delay: 2.5s; }
                .kx-node-ping-4 { animation-delay: 3.75s; }
                .kx-flow-path { stroke-dasharray: 6 6; animation: kxFlow 1.6s linear infinite; }
                @keyframes kxPing {
                  0%   { transform: scale(1);   opacity: 0.55; }
                  70%  { transform: scale(3.5); opacity: 0; }
                  100% { transform: scale(3.5); opacity: 0; }
                }
                @keyframes kxFlow {
                  to { stroke-dashoffset: -24; }
                }
                @media (prefers-reduced-motion: reduce) {
                  .kx-node-ping, .kx-flow-path { animation: none !important; opacity: 0; }
                }
              `}</style>

              <path d="M100 400 L800 400" stroke="var(--landing-rule)" strokeWidth="1" />
              <path d="M300 200 L300 600" stroke="var(--landing-rule)" strokeWidth="1" />
              <path d="M100 400 L300 200 L500 400 L800 600" stroke="var(--landing-rule)" strokeWidth="1" />
              <path d="M500 400 L500 700" stroke="var(--landing-rule)" strokeWidth="1" />

              <circle className="kx-node-ping kx-node-ping-1" cx="100" cy="400" r="4" />
              <circle className="kx-node-ping kx-node-ping-2" cx="300" cy="200" r="4" />
              <circle className="kx-node-ping kx-node-ping-3" cx="500" cy="700" r="4" />
              <circle className="kx-node-ping kx-node-ping-4" cx="800" cy="600" r="4" />

              <circle cx="100" cy="400" r="4" fill="var(--landing-foreground)" />
              <circle cx="300" cy="200" r="4" fill="var(--landing-foreground)" />
              <circle cx="500" cy="700" r="4" fill="var(--landing-foreground)" />
              <circle cx="800" cy="600" r="4" fill="var(--landing-foreground)" />

              <circle cx="300" cy="600" r="6" fill="var(--landing-alarm)" />
              <circle cx="500" cy="400" r="4" fill="var(--landing-alarm)" />

              <circle cx="800" cy="400" r="4" fill="var(--landing-alarm)" />

              <path
                className="kx-flow-path"
                d="M300 600 L500 400 L800 400"
                stroke="var(--landing-alarm)"
                strokeWidth="2"
              />

              <text x="320" y="605" fill="var(--landing-alarm)" className="font-landing-body" fontSize="10" letterSpacing="1">
                CLUSTER · SMURFING
              </text>
              <text x="520" y="395" fill="var(--landing-alarm)" className="font-landing-body" fontSize="10" letterSpacing="1">
                ENTITY · CROSS-FLAGGED
              </text>
              <text x="320" y="195" fill="var(--landing-muted)" className="font-landing-body" fontSize="10" letterSpacing="1">
                NODE · COMMERCIAL BANK
              </text>

              <path d="M500 400 L1000 400" stroke="var(--landing-rule-solid)" strokeWidth="1" />
              <text x="900" y="390" fill="var(--landing-muted)" className="font-landing-body" fontSize="8" letterSpacing="1">
                FLOW · MULTI-BANK
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
