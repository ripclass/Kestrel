import Link from "next/link";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { matches } from "@/lib/demo";

export function MatchList({ compact = false }: { compact?: boolean }) {
  const list = compact ? matches.slice(0, 2) : matches;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Cross-bank matches</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {list.map((match) => (
          <Link
            key={match.id}
            href={`/investigate/entity/${match.entityId}`}
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
