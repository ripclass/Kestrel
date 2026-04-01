import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { MatchSummary } from "@/types/domain";

export function MatchDetail({ match }: { match: MatchSummary }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{match.matchKey}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm text-muted-foreground">
        <p>{match.matchType} overlap across {match.involvedOrgs.length} institutions.</p>
        <p>{match.involvedOrgs.join(", ")}</p>
      </CardContent>
    </Card>
  );
}
