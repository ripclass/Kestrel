import { Briefcase, ShieldCheck, Users } from "lucide-react";

const personas = [
  {
    Icon: ShieldCheck,
    title: "BFIU Analysts",
    body: "Unified search across every reporting institution. Case management, disseminations, and an IER workflow for Egmont cooperation. Network graphs on every subject, no manual drawing required.",
  },
  {
    Icon: Briefcase,
    title: "Bank CAMLCOs",
    body: "A pattern scanner on your own transactions. STR drafting assisted by AI-detected alerts. Peer-network intelligence without exposing your own book.",
  },
  {
    Icon: Users,
    title: "BFIU Directors",
    body: "National threat dashboard. Bank-by-bank compliance scorecards. Typology trend analysis. Executive briefings generated from live data.",
  },
];

export function PersonaCards() {
  return (
    <section className="border-b border-white/5">
      <div className="mx-auto w-full max-w-7xl px-6 py-24 lg:px-10">
        <div className="max-w-3xl space-y-4">
          <p className="text-xs uppercase tracking-[0.28em] text-primary">Who it&apos;s for</p>
          <h2 className="text-3xl font-semibold tracking-tight text-white lg:text-4xl">
            One platform. Three personas. All signed in at the same time.
          </h2>
        </div>
        <div className="mt-12 grid gap-6 md:grid-cols-3">
          {personas.map(({ Icon, title, body }) => (
            <div
              key={title}
              className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 backdrop-blur-sm"
            >
              <div className="inline-flex rounded-xl bg-primary/15 p-2.5 text-primary">
                <Icon className="h-5 w-5" />
              </div>
              <h3 className="mt-4 text-lg font-semibold text-white">{title}</h3>
              <p className="mt-3 text-sm leading-relaxed text-slate-300">{body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
