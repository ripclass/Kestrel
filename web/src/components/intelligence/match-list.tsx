import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
    <Card>
      <CardHeader>
        <CardTitle>Cross-bank matches</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {list.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border/70 bg-background/40 p-4 text-sm text-muted-foreground">
            No cross-bank overlaps are available for this view yet.
          </div>
        ) : null}
        {list.map((match) => (
          <Link
            key={match.id}
            href={match.entityId ? `/investigate/entity/${match.entityId}` : "/intelligence/matches"}
            className="block rounded-xl border border-border/70 bg-background/50 p-4"
          >
            <div className="flex items-center justify-between gap-4">
              <p className="font-medium">{match.matchKey}</p>
              <span className="text-sm text-primary">{match.matchCount} hits</span>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">{match.involvedOrgs.join(", ")}</p>
          </Link>
        ))}
      </CardContent>
    </Card>
  );
}
