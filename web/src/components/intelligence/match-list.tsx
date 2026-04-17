import Link from "next/link";

import type { MatchSummary } from "@/types/domain";

export function MatchList({
  compact = false,
  matches = [],
}: {
  compact?: boolean;
  matches?: MatchSummary[];
}) {
  const list = compact ? matches.slice(0, 2) : matches;

  return (
    <section className="border border-border">
      <div className="border-b border-border px-6 py-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Section · Cross-bank matches
        </p>
      </div>
      {list.length === 0 ? (
        <p className="px-6 py-6 font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
          No cross-bank overlaps resolved
        </p>
      ) : (
        <ul className="divide-y divide-border">
          {list.map((match) => (
            <li key={match.id}>
              <Link
                href={match.entityId ? `/investigate/entity/${match.entityId}` : "/intelligence/matches"}
                className="flex flex-col gap-2 px-6 py-4 transition hover:bg-foreground/[0.03]"
              >
                <div className="flex items-center justify-between gap-4">
                  <p className="font-mono text-sm text-foreground">{match.matchKey}</p>
                  <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-accent">
                    <span className="tabular-nums">{match.matchCount}</span> hits
                  </span>
                </div>
                <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                  {match.involvedOrgs.join(" · ")}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
