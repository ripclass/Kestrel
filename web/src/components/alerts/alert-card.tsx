import Link from "next/link";

import { RiskScore } from "@/components/common/risk-score";
import { StatusBadge } from "@/components/common/status-badge";
import type { AlertSummary } from "@/types/domain";

function shortId(id: string) {
  if (id.length <= 10) return id;
  return `${id.slice(0, 4)}··${id.slice(-4)}`;
}

export function AlertCard({ alert }: { alert: AlertSummary }) {
  return (
    <Link
      href={`/alerts/${alert.id}`}
      className="flex items-start gap-6 border border-border bg-card px-5 py-4 transition hover:bg-foreground/[0.03]"
    >
      <div className="flex-1 space-y-2">
        <p className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="leading-none text-accent">┼</span>
          <span>Alert · {shortId(alert.id)}</span>
          <span>· {alert.alertType}</span>
        </p>
        <h3 className="text-base font-semibold text-foreground">{alert.title}</h3>
        <p className="text-sm leading-relaxed text-muted-foreground">{alert.description}</p>
        <div className="flex flex-wrap items-center gap-3 pt-1">
          <StatusBadge status={alert.status} />
          <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
            {alert.orgName}
          </span>
        </div>
      </div>
      <RiskScore score={alert.riskScore} severity={alert.severity} />
    </Link>
  );
}
