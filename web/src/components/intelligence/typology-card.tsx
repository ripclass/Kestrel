import type { TypologySummary } from "@/types/domain";
import { PREDICATE_OFFENCE_LABELS } from "@/types/domain";

export function TypologyCard({ typology }: { typology: TypologySummary }) {
  const predicates = typology.predicateOffences ?? [];
  const ref = typology.bfiuAvenueRef;
  return (
    <section className="border border-border bg-card">
      <div className="border-b border-border px-6 py-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Typology · {typology.category}
          {ref ? (
            <span className="ml-2 text-accent">┼ BFIU §{ref}</span>
          ) : null}
        </p>
        <h3 className="mt-2 text-lg font-semibold text-foreground">{typology.title}</h3>
      </div>
      <div className="space-y-4 px-6 py-5">
        <p className="text-sm leading-relaxed text-foreground">{typology.narrative}</p>
        {typology.indicators.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {typology.indicators.map((indicator) => (
              <span
                key={indicator}
                className="border border-border px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground"
              >
                {indicator}
              </span>
            ))}
          </div>
        ) : null}
        {predicates.length > 0 ? (
          <div className="space-y-2">
            <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
              <span aria-hidden className="mr-2 text-accent">┼</span>
              Predicate offences · MLPA §2(cc)
            </p>
            <div className="flex flex-wrap gap-2">
              {predicates.map((code) => (
                <span
                  key={code}
                  className="border border-accent/40 px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.18em] text-accent"
                >
                  {PREDICATE_OFFENCE_LABELS[code]}
                </span>
              ))}
            </div>
          </div>
        ) : null}
      </div>
    </section>
  );
}
