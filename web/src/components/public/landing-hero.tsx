import Image from "next/image";

export function LandingHero() {
  return (
    <section
      id="hero"
      className="relative flex w-full flex-col overflow-hidden border-b border-landing-rule bg-landing-bg pt-24 pb-24 lg:pt-32"
    >
      <div className="relative z-10 mx-auto grid w-full max-w-7xl grid-cols-1 gap-16 px-6 lg:grid-cols-12 lg:gap-12 lg:px-10">
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

        <div className="relative col-span-1 lg:col-span-7">
          <figure className="relative">
            <div className="border border-landing-rule-solid bg-[color:var(--landing-bg-elevated,#15171c)] p-2 shadow-[0_30px_80px_-30px_rgba(0,0,0,0.7)]">
              <div className="border border-landing-rule">
                <Image
                  src="/hero-cross-bank.png"
                  alt="Kestrel cross-bank intelligence dashboard rendered for the bank persona — peer institutions anonymised, match keys redacted to last four characters, aggregate exposure in BDT."
                  width={1883}
                  height={889}
                  priority
                  className="block h-auto w-full"
                  sizes="(min-width: 1024px) 58vw, 100vw"
                />
              </div>
            </div>
            <figcaption className="mt-4 flex items-center gap-3 font-landing-body text-[10px] uppercase tracking-[0.3em] text-landing-muted">
              <span className="text-landing-alarm">┼</span>
              <span>Live · Cross-bank intelligence dashboard · Bank CAMLCO view</span>
            </figcaption>
          </figure>
        </div>
      </div>

      <div className="pointer-events-none absolute inset-0 z-0 bg-[linear-gradient(to_right,var(--landing-rule)_1px,transparent_1px),linear-gradient(to_bottom,var(--landing-rule)_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:linear-gradient(to_bottom,transparent,black,transparent)]" />
    </section>
  );
}
