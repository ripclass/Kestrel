import { getEntityDossier } from "@/lib/demo";
import type { AlertSummary } from "@/types/domain";
import { AlertActions } from "@/components/alerts/alert-actions";
import { Explainability } from "@/components/alerts/explainability";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { NetworkCanvas } from "@/components/investigate/network-canvas";
import { RiskScore } from "@/components/common/risk-score";

export function AlertDetail({ alert }: { alert: AlertSummary }) {
  const entity = getEntityDossier(alert.entityId);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-2">
              <CardTitle>{alert.title}</CardTitle>
              <p className="text-sm text-muted-foreground">{alert.description}</p>
            </div>
            <RiskScore score={alert.riskScore} severity={alert.severity} />
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <AlertActions />
        </CardContent>
      </Card>
      <Explainability reasons={alert.reasons} />
      <NetworkCanvas graph={entity.graph} />
    </div>
  );
}
