"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { readResponsePayload } from "@/lib/http";
import type { MatchListResponse } from "@/types/api";
import type { MatchSummary } from "@/types/domain";

const severityTone: Record<string, string> = {
  critical: "text-accent",
  high: "text-accent",
  medium: "text-foreground",
  low: "text-muted-foreground",
};

export function MatchTicker() {
  const [matches, setMatches] = useState<MatchSummary[]>([]);

  useEffect(() => {
    void (async () => {
      try {
        const response = await fetch("/api/intelligence/matches", { cache: "no-store" });
        if (!response.ok) return;
        const payload = (await readResponsePayload<MatchListResponse>(response)) as MatchListResponse;
        setMatches(payload.matches.slice(0, 5));
      } catch {
        // Degrade silently — ticker is supplementary.
      }
    })();
  }, []);

  if (matches.length === 0) return null;

  return (
    <div className="flex items-center gap-0 overflow-x-auto border border-border bg-card">
      <span className="flex items-center gap-2 whitespace-nowrap border-r border-border px-4 py-3 font-mono text-[10px] uppercase tracking-[0.28em] text-accent">
        <span aria-hidden className="leading-none">┼</span>
        Cross-bank wire
      </span>
      {matches.map((match) => (
        <Link
          key={match.id}
          href="/intelligence/matches"
          className="flex min-w-max items-center gap-3 border-r border-border px-4 py-3 text-sm last:border-r-0 hover:bg-foreground/[0.03]"
        >
          <span
            className={`font-mono text-[10px] uppercase tracking-[0.22em] ${severityTone[match.severity] ?? "text-muted-foreground"}`}
          >
            {match.severity}
          </span>
          <span className="font-mono text-foreground">{match.matchKey}</span>
          <span className="font-mono text-[11px] text-muted-foreground">
            {match.involvedOrgs.length} banks
          </span>
        </Link>
      ))}
    </div>
  );
}
