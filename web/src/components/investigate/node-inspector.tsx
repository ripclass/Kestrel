import type { NetworkNode } from "@/types/domain";

function shortId(id: string) {
  if (id.length <= 10) return id;
  return `${id.slice(0, 4)}··${id.slice(-4)}`;
}

export function NodeInspector({ node }: { node: NetworkNode }) {
  const severity = node.riskScore >= 90 ? "critical" : node.riskScore >= 70 ? "high" : node.riskScore >= 50 ? "medium" : "low";
  const scoreTone =
    severity === "critical"
      ? "text-accent"
      : severity === "high"
        ? "text-accent"
        : severity === "medium"
          ? "text-foreground"
          : "text-muted-foreground";
  return (
    <section className="border border-border">
      <div className="border-b border-border px-5 py-4">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Section · Node inspector
        </p>
      </div>
      <div className="space-y-5 px-5 py-5">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">Node</p>
          <p className="mt-1 font-mono text-sm text-foreground">{shortId(node.id)}</p>
        </div>
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">Label</p>
          <p className="mt-1 text-sm text-foreground">{node.label}</p>
          {node.subtitle ? (
            <p className="mt-1 text-sm text-muted-foreground">{node.subtitle}</p>
          ) : null}
        </div>
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">Risk score</p>
          <p className={`mt-1 font-mono text-3xl tabular-nums ${scoreTone}`}>{node.riskScore}</p>
          <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
            {severity}
          </p>
        </div>
      </div>
    </section>
  );
}
