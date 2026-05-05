import Link from "next/link";

export const dynamic = "force-static";

export default function DemoPage() {
  return (
    <div className="mx-auto max-w-4xl px-6 py-16">
      <header className="mb-12 border-b border-landing-foreground/10 pb-6">
        <p className="font-mono text-[10px] uppercase tracking-[0.32em] text-landing-foreground/60">
          <span aria-hidden className="mr-2 text-landing-accent">┼</span>
          Kestrel · Demo
        </p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight text-landing-foreground">
          Same data. Different lens.
        </h1>
        <p className="mt-4 max-w-2xl text-base text-landing-foreground/70">
          Kestrel is one platform with three personas. The transactions and STRs are the same; what
          changes is the level of detail each persona can see. Sign in below to step into the demo
          tenant — the synthetic dataset refreshes weekly, so you always see recent activity.
        </p>
      </header>

      <section className="grid grid-cols-1 gap-6 md:grid-cols-3">
        <PersonaCard
          eyebrow="Bank · CAMLCO"
          title="Sonali Bank PLC"
          description="Bank-direct view. Cross-bank intelligence with peer banks anonymised, transaction-scoring stream, KYC onboarding, sanctions screening, your own STRs."
          email="camlco@sonali.example"
          highlight="Peer banks rendered as 'Peer institution N'. Match keys redacted to last 4 chars."
        />
        <PersonaCard
          eyebrow="BFIU · Director"
          title="Bangladesh FIU"
          description="Command-level dashboards. Full cross-bank view with real bank names, national typology trends, dissemination ledger, IER workflow, regulator-only admin surfaces."
          email="director@bfiu.gov.bd"
          highlight="Sees all bank names + full match keys. Posts to the public status page."
        />
        <PersonaCard
          eyebrow="BFIU · Analyst"
          title="Bangladesh FIU"
          description="Working-level view. STR triage, alert review, case management, network graph, AI alert explanation drafts."
          email="analyst@bfiu.gov.bd"
          highlight="Same data scope as the director, narrower action surface."
        />
      </section>

      <section className="mt-16 space-y-6 border border-landing-foreground/10 p-8">
        <p className="font-mono text-[10px] uppercase tracking-[0.32em] text-landing-foreground/60">
          <span aria-hidden className="mr-2 text-landing-accent">┼</span>
          Get into the demo
        </p>
        <p className="text-base text-landing-foreground/80">
          The demo tenant is shared and read-mostly — onboarding a customer or running a screen is
          fine, but please do not post status incidents (those surface on the public status page).
        </p>
        <div className="flex flex-wrap gap-4">
          <Link
            href="/login"
            className="border border-landing-foreground bg-landing-foreground px-5 py-2 font-mono text-[11px] uppercase tracking-[0.22em] text-landing-bg transition hover:bg-landing-bg hover:text-landing-foreground"
          >
            Sign in
          </Link>
          <Link
            href="/banks"
            className="border border-landing-foreground/40 px-5 py-2 font-mono text-[11px] uppercase tracking-[0.22em] text-landing-foreground/80 transition hover:border-landing-foreground hover:text-landing-foreground"
          >
            Bank-direct landing
          </Link>
          <Link
            href="/status"
            className="border border-landing-foreground/40 px-5 py-2 font-mono text-[11px] uppercase tracking-[0.22em] text-landing-foreground/80 transition hover:border-landing-foreground hover:text-landing-foreground"
          >
            Platform status
          </Link>
        </div>
      </section>

      <footer className="mt-16 space-y-2 border-t border-landing-foreground/10 pt-6">
        <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-landing-foreground/60">
          ┼ Demo data refreshes every Monday at 04:00 BDT
        </p>
        <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-landing-foreground/60">
          Three personas · one platform · same production deployment
        </p>
      </footer>
    </div>
  );
}

function PersonaCard({
  eyebrow,
  title,
  description,
  email,
  highlight,
}: {
  eyebrow: string;
  title: string;
  description: string;
  email: string;
  highlight: string;
}) {
  return (
    <article className="flex flex-col gap-4 border border-landing-foreground/10 p-6">
      <p className="font-mono text-[10px] uppercase tracking-[0.32em] text-landing-foreground/60">
        <span aria-hidden className="mr-2 text-landing-accent">┼</span>
        {eyebrow}
      </p>
      <h2 className="text-xl font-semibold tracking-tight text-landing-foreground">{title}</h2>
      <p className="text-sm text-landing-foreground/70">{description}</p>
      <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-landing-accent">
        ┼ {highlight}
      </p>
      <p className="mt-auto font-mono text-[11px] text-landing-foreground/60">
        Sign in as <span className="text-landing-foreground">{email}</span>
      </p>
    </article>
  );
}
