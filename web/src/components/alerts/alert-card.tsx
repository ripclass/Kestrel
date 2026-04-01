import Link from "next/link";

import { RiskScore } from "@/components/common/risk-score";
import { StatusBadge } from "@/components/common/status-badge";
import { Card, CardContent } from "@/components/ui/card";
import type { AlertSummary } from "@/types/domain";

export function AlertCard({ alert }: { alert: AlertSummary }) {
  return (
    <Link href={`/alerts/${alert.id}`}>
      <Card className="transition hover:border-primary/40">
        <CardContent className="space-y-3 p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="font-semibold">{alert.title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{alert.description}</p>
            </div>
            <RiskScore score={alert.riskScore} severity={alert.severity} />
          </div>
          <div className="flex items-center gap-3 text-sm">
            <StatusBadge status={alert.status} />
            <span className="text-muted-foreground">{alert.alertType}</span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
