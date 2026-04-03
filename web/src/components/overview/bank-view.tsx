import { KpiCard } from "@/components/overview/kpi-card";
import { MatchList } from "@/components/intelligence/match-list";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchCrossBankMatches } from "@/lib/investigation";
import type { KpiStat } from "@/types/domain";

const stats: KpiStat[] = [
  { label: "Accounts above threshold", value: "32", delta: "+5 from last scan", detail: "ready for manual review" },
  { label: "Peer-network signals", value: "11", delta: "3 urgent", detail: "anonymized cross-bank indicators exposed" },
  { label: "Submission posture", value: "84/100", delta: "+4 month on month", detail: "above peer median" },
];

export async function BankView() {
  const matches = await fetchCrossBankMatches();

  return (
    <div className="space-y-6">
      <div className="grid gap-4 xl:grid-cols-3">
        {stats.map((stat) => (
          <KpiCard key={stat.label} stat={stat} />
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-[1.3fr_0.9fr]">
        <MatchList compact matches={matches} />
        <Card>
          <CardHeader>
            <CardTitle>Network threat guidance</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-muted-foreground">
            <div className="rounded-xl border border-border/70 bg-background/50 p-4">
              MFS-linked merchant accounts remain the highest-growth typology this week.
            </div>
            <div className="rounded-xl border border-border/70 bg-background/50 p-4">
              Review beneficiaries with two-hop proximity to known bad before next bulk filing cycle.
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
