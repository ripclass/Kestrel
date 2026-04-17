import { Currency } from "@/components/common/currency";
import type { ThreatMapRow } from "@/types/domain";

const levelTone: Record<string, string> = {
  "Very high": "text-accent",
  High: "text-accent",
  Elevated: "text-foreground",
  Monitoring: "text-muted-foreground",
};

export function ThreatMap({ rows }: { rows: ThreatMapRow[] }) {
  return (
    <section className="border border-border">
      <div className="border-b border-border px-6 py-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Section · National threat heatmap
        </p>
      </div>
      <ul className="divide-y divide-border">
        {rows.map((row) => (
          <li key={row.channel} className="grid grid-cols-[1fr_auto] items-start gap-4 px-6 py-4">
            <div>
              <div className="flex items-baseline gap-3">
                <p className="font-mono text-sm uppercase tracking-[0.18em] text-foreground">
                  {row.channel}
                </p>
                <span
                  className={`font-mono text-[10px] uppercase tracking-[0.22em] ${levelTone[row.level] ?? "text-muted-foreground"}`}
                >
                  {row.level}
                </span>
              </div>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{row.detail}</p>
            </div>
            <div className="text-right font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
              <p className="tabular-nums">{row.signalCount} signals</p>
              <p className="mt-1 tabular-nums text-foreground">
                <Currency amount={row.totalExposure} />
              </p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
