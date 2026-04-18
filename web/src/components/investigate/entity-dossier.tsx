import { RiskScore } from "@/components/common/risk-score";
import { DisseminateAction } from "@/components/disseminations/disseminate-action";
import { EntityConnections } from "@/components/investigate/entity-connections";
import { ReportingHistory } from "@/components/investigate/reporting-history";
import { ActivityTimeline } from "@/components/investigate/activity-timeline";
import { NetworkCanvas } from "@/components/investigate/network-canvas";
import type { EntityDossier as EntityDossierType } from "@/types/domain";

function shortId(id: string) {
  if (id.length <= 10) return id;
  return `${id.slice(0, 4)}··${id.slice(-4)}`;
}

export function EntityDossier({ entity }: { entity: EntityDossierType }) {
  return (
    <div className="space-y-6">
      <section className="border border-border">
        <div className="flex flex-col gap-6 border-b border-border px-6 py-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-3">
            <p className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
              <span aria-hidden className="leading-none text-accent">┼</span>
              Subject · {entity.entityType} · {shortId(entity.id)}
            </p>
            <h2 className="font-mono text-2xl text-foreground">{entity.displayValue}</h2>
            {entity.displayName ? (
              <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">
                {entity.displayName}
              </p>
            ) : null}
          </div>
          <div className="flex flex-col items-start gap-3 lg:items-end">
            <RiskScore score={entity.riskScore} severity={entity.severity} />
            <DisseminateAction
              linkedEntityId={entity.id}
              defaultSubject={`Subject: ${entity.displayName ?? entity.displayValue}\nEntity ID: ${entity.id}\nRisk: ${entity.riskScore}`}
              variant="outline"
            />
          </div>
        </div>
        <div className="grid grid-cols-2 divide-x divide-y divide-border border-t-0 lg:grid-cols-4 lg:divide-y-0">
          <Meta label="Reports">
            <span className="font-mono text-2xl tabular-nums text-foreground">{entity.reportCount}</span>
          </Meta>
          <Meta label="Reporting orgs">
            <span className="font-mono text-2xl tabular-nums text-foreground">
              {entity.reportingOrgs.length}
            </span>
          </Meta>
          <Meta label="Exposure">
            <span className="font-mono text-2xl tabular-nums text-foreground">
              ৳ {entity.totalExposure.toLocaleString()}
            </span>
          </Meta>
          <Meta label="Confidence">
            <span className="font-mono text-2xl tabular-nums text-foreground">
              {Math.round(entity.confidence * 100)}%
            </span>
          </Meta>
        </div>
      </section>
      <NetworkCanvas graph={entity.graph} />
      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <EntityConnections entities={entity.connections} />
        <ActivityTimeline events={entity.timeline} />
      </div>
      <ReportingHistory history={entity.reportingHistory} />
    </div>
  );
}

function Meta({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-3 p-5">
      <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">{label}</span>
      {children}
    </div>
  );
}
