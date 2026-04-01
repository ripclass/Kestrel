import { AlertTicker } from "@/components/overview/alert-ticker";
import { KpiCard } from "@/components/overview/kpi-card";
import { AlertQueue } from "@/components/alerts/alert-queue";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cases } from "@/lib/demo";
import type { KpiStat } from "@/types/domain";

const stats: KpiStat[] = [
  { label: "Open priority alerts", value: "18", delta: "6 critical", detail: "triage within today" },
  { label: "Cross-bank matches", value: "7", delta: "+2 overnight", detail: "new overlaps ready for validation" },
  { label: "Cases in motion", value: "4", delta: "1 escalated", detail: "shared evidence workspace active" },
];

export function AnalystView() {
  return (
    <div className="space-y-6">
      <AlertTicker />
      <div className="grid gap-4 xl:grid-cols-3">
        {stats.map((stat) => (
          <KpiCard key={stat.label} stat={stat} />
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-[1.3fr_0.9fr]">
        <AlertQueue alertsToShow={3} />
        <Card>
          <CardHeader>
            <CardTitle>Recent cases</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {cases.map((item) => (
              <div key={item.id} className="rounded-xl border border-border/70 bg-background/50 p-4">
                <p className="font-medium">{item.caseRef}</p>
                <p className="mt-1 text-sm">{item.title}</p>
                <p className="mt-2 text-sm text-muted-foreground">{item.summary}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
