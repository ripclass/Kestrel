import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { RiskScore } from "@/components/common/risk-score";
import { EntityConnections } from "@/components/investigate/entity-connections";
import { ReportingHistory } from "@/components/investigate/reporting-history";
import { ActivityTimeline } from "@/components/investigate/activity-timeline";
import { NetworkCanvas } from "@/components/investigate/network-canvas";
import type { EntityDossier as EntityDossierType } from "@/types/domain";

export function EntityDossier({ entity }: { entity: EntityDossierType }) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-2">
              <CardTitle className="text-2xl">{entity.displayValue}</CardTitle>
              <CardDescription>{entity.displayName}</CardDescription>
            </div>
            <RiskScore score={entity.riskScore} severity={entity.severity} />
          </div>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-4">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Reports</p>
            <p className="mt-2 text-2xl font-semibold">{entity.reportCount}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Reporting orgs</p>
            <p className="mt-2 text-2xl font-semibold">{entity.reportingOrgs.length}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Exposure</p>
            <p className="mt-2 text-2xl font-semibold">BDT {entity.totalExposure.toLocaleString()}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Confidence</p>
            <p className="mt-2 text-2xl font-semibold">{Math.round(entity.confidence * 100)}%</p>
          </div>
        </CardContent>
      </Card>
      <NetworkCanvas graph={entity.graph} />
      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <EntityConnections entities={entity.connections} />
        <ActivityTimeline events={entity.timeline} />
      </div>
      <ReportingHistory history={entity.reportingHistory} />
    </div>
  );
}
