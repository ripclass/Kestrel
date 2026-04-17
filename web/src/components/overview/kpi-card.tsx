import type { KpiStat } from "@/types/domain";

export function KpiCard({ stat }: { stat: KpiStat }) {
  return (
    <div className="flex flex-col gap-3 border border-border bg-card p-6">
      <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
        {stat.label}
      </p>
      <p className="font-mono text-4xl leading-none tracking-tight text-foreground">
        {stat.value}
      </p>
      <div className="flex flex-wrap items-baseline gap-3 border-t border-border pt-3">
        <span className="font-mono text-xs uppercase tracking-[0.22em] text-accent">
          {stat.delta}
        </span>
        <span className="text-sm text-muted-foreground">{stat.detail}</span>
      </div>
    </div>
  );
}
