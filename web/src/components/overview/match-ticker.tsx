"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { readResponsePayload } from "@/lib/http";
import type { MatchListResponse } from "@/types/api";
import type { MatchSummary } from "@/types/domain";

const severityColor: Record<string, string> = {
  critical: "text-red-400",
  high: "text-orange-400",
  medium: "text-yellow-400",
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
        // Degrade silently — match ticker is supplementary
      }
    })();
  }, []);

  if (matches.length === 0) return null;

  return (
    <div className="flex gap-4 overflow-x-auto rounded-2xl border border-border/80 bg-card/80 px-4 py-3 text-sm">
      <span className="min-w-max font-medium text-muted-foreground">Cross-bank</span>
      {matches.map((match) => (
        <Link
          key={match.id}
          href={`/intelligence/matches`}
          className="flex min-w-max items-center gap-2 transition-colors hover:text-primary"
        >
          <span className={severityColor[match.severity] ?? "text-muted-foreground"}>
            {match.severity.toUpperCase()}
          </span>
          <span className="text-muted-foreground">/</span>
          <span>{match.matchKey}</span>
          <span className="text-muted-foreground">
            ({match.involvedOrgs.length} banks)
          </span>
        </Link>
      ))}
    </div>
  );
}
