import type { Severity } from "@/types/domain";

const severityTone: Record<Severity, string> = {
  low: "border-border text-muted-foreground",
  medium: "border-foreground/30 text-foreground",
  high: "border-accent/40 text-accent",
  critical: "border-accent bg-accent text-accent-foreground",
};

const severityLabel: Record<Severity, string> = {
  low: "LOW",
  medium: "MED",
  high: "HIGH",
  critical: "CRIT",
};

export function RiskScore({ score, severity }: { score: number; severity: Severity }) {
  return (
    <div
      className={`inline-flex items-baseline gap-3 border px-4 py-2 font-mono uppercase tracking-[0.14em] ${severityTone[severity]}`}
    >
      <span className="text-[10px]">{severityLabel[severity]}</span>
      <span className="text-2xl leading-none tracking-tight">{score}</span>
      <span className="text-[10px] opacity-60">/100</span>
    </div>
  );
}
