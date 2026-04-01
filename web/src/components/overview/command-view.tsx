import { AlertTicker } from "@/components/overview/alert-ticker";
import { KpiCard } from "@/components/overview/kpi-card";
import { ThreatMap } from "@/components/overview/threat-map";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { complianceScores } from "@/lib/demo";
import type { KpiStat } from "@/types/domain";

const stats: KpiStat[] = [
  { label: "High-severity networks", value: "18", delta: "+3 this week", detail: "cross-bank clusters with regulator visibility" },
  { label: "Peer banks lagging", value: "2", delta: "attention required", detail: "timeliness and conversion below national baseline" },
  { label: "Mutual-evaluation ready packs", value: "5", delta: "up to date", detail: "typology and compliance narratives assembled" },
];

export function CommandView() {
  return (
    <div className="space-y-6">
      <AlertTicker />
      <div className="grid gap-4 xl:grid-cols-3">
        {stats.map((stat) => (
          <KpiCard key={stat.label} stat={stat} />
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-[1.3fr_0.9fr]">
        <ThreatMap />
        <Card>
          <CardHeader>
            <CardTitle>Bank compliance posture</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {complianceScores.map((bank) => (
              <div key={bank.orgName} className="rounded-xl border border-border/70 bg-background/50 p-4">
                <div className="flex items-center justify-between">
                  <p className="font-medium">{bank.orgName}</p>
                  <span className="text-xl font-semibold">{bank.score}</span>
                </div>
                <p className="mt-2 text-sm text-muted-foreground">
                  Timeliness {bank.submissionTimeliness}, conversion {bank.alertConversion}, peer coverage {bank.peerCoverage}
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
