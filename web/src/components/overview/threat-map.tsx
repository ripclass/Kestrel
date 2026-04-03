import { Currency } from "@/components/common/currency";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ThreatMapRow } from "@/types/domain";

export function ThreatMap({ rows }: { rows: ThreatMapRow[] }) {
  return (
    <Card className="grid-surface">
      <CardHeader>
        <CardTitle>National threat heatmap</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {rows.map((row) => (
          <div key={row.channel} className="rounded-xl border border-border/70 bg-background/50 p-4">
            <div className="flex items-center justify-between gap-4">
              <p className="font-medium">{row.channel}</p>
              <span className="text-sm text-primary">{row.level}</span>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">{row.detail}</p>
            <p className="mt-2 text-xs uppercase tracking-[0.18em] text-muted-foreground">
              {row.signalCount} signals · <Currency amount={row.totalExposure} />
            </p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
