import { TrendingUp } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { KpiStat } from "@/types/domain";

export function KpiCard({ stat }: { stat: KpiStat }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-4">
          <CardTitle className="text-sm text-muted-foreground">{stat.label}</CardTitle>
          <div className="rounded-full bg-primary/15 p-2 text-primary">
            <TrendingUp className="h-4 w-4" />
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-1">
        <div className="text-3xl font-semibold tracking-tight">{stat.value}</div>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-primary">{stat.delta}</span>
          <span className="text-muted-foreground">{stat.detail}</span>
        </div>
      </CardContent>
    </Card>
  );
}
