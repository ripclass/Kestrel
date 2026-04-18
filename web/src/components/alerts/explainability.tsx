import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AlertReason } from "@/types/domain";

export function Explainability({ reasons }: { reasons: AlertReason[] }) {
  const totalContribution = reasons.reduce((sum, r) => sum + r.score * r.weight, 0) || 1;

  return (
    <Card>
      <CardHeader>
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>Section · Rule trace
        </p>
        <CardTitle className="font-mono uppercase tracking-[0.12em]">Why Kestrel flagged this</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="border border-border">
          <div className="grid grid-cols-[1fr_auto_auto] items-center gap-4 border-b border-border bg-white/[0.02] px-4 py-2 font-mono text-[10px] uppercase tracking-[0.24em] text-muted-foreground">
            <span>Rule</span>
            <span className="text-right">Score × Wt</span>
            <span className="w-32 text-right">Contribution</span>
          </div>
          {reasons.map((reason) => {
            const contribution = (reason.score * reason.weight) / totalContribution;
            return (
              <div
                key={reason.rule}
                className="grid grid-cols-[1fr_auto_auto] items-center gap-4 border-b border-border px-4 py-4 last:border-b-0"
              >
                <div>
                  <p className="font-mono text-sm text-foreground">{reason.rule}</p>
                  <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                    {reason.explanation}
                  </p>
                  {reason.recommendedAction ? (
                    <p className="mt-2 font-mono text-[11px] uppercase tracking-[0.18em] text-accent">
                      <span aria-hidden className="mr-2">┼</span>
                      {reason.recommendedAction}
                    </p>
                  ) : null}
                </div>
                <p className="font-mono text-sm tabular-nums text-foreground">
                  {reason.score}
                  <span className="px-1 text-muted-foreground">×</span>
                  {reason.weight}
                </p>
                <div className="w-32">
                  <div className="h-1.5 w-full bg-white/[0.05]">
                    <div
                      className="h-full bg-accent"
                      style={{ width: `${Math.round(contribution * 100)}%` }}
                    />
                  </div>
                  <p className="mt-1 text-right font-mono text-[10px] tabular-nums text-muted-foreground">
                    {Math.round(contribution * 100)}%
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
