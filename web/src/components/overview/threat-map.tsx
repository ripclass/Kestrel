import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const rows = [
  ["MFS wallets", "Very high", "Merchant front networks and rapid beneficiary cashout"],
  ["RTGS", "High", "Large-value clearing used as staging leg before wallet dispersion"],
  ["NPSB", "Elevated", "Consumer account fan-out rings crossing peer banks"],
];

export function ThreatMap() {
  return (
    <Card className="grid-surface">
      <CardHeader>
        <CardTitle>National threat heatmap</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {rows.map(([channel, level, detail]) => (
          <div key={channel} className="rounded-xl border border-border/70 bg-background/50 p-4">
            <div className="flex items-center justify-between gap-4">
              <p className="font-medium">{channel}</p>
              <span className="text-sm text-primary">{level}</span>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">{detail}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
