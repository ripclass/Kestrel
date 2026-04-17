import type { MatchSummary } from "@/types/domain";

export function MatchDetail({ match }: { match: MatchSummary }) {
  return (
    <section className="border border-border">
      <div className="border-b border-border px-6 py-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Section · Match detail
        </p>
        <h2 className="mt-2 font-mono text-xl text-foreground">{match.matchKey}</h2>
      </div>
      <div className="space-y-3 px-6 py-5">
        <p className="text-sm leading-relaxed text-foreground">
          <span className="font-mono uppercase tracking-[0.18em] text-muted-foreground">
            {match.matchType}
          </span>{" "}
          overlap across <span className="font-mono tabular-nums">{match.involvedOrgs.length}</span>{" "}
          institutions.
        </p>
        <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          {match.involvedOrgs.join(" · ")}
        </p>
      </div>
    </section>
  );
}
