import type { Severity } from "@/types/domain";

const toneClass: Record<Severity, string> = {
  low: "border-border bg-transparent text-muted-foreground",
  medium: "border-foreground/30 bg-foreground/5 text-foreground",
  high: "border-accent/40 bg-accent/10 text-accent",
  critical: "border-accent bg-accent text-accent-foreground",
};

export function SeverityPill({ severity }: { severity: Severity }) {
  return (
    <span
      className={`inline-flex items-center border px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.22em] ${toneClass[severity]}`}
    >
      {severity}
    </span>
  );
}
