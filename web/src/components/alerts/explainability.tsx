import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AlertReason } from "@/types/domain";

export function Explainability({ reasons }: { reasons: AlertReason[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Why Kestrel flagged this</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {reasons.map((reason) => (
          <div key={reason.rule} className="rounded-xl border border-border/70 bg-background/50 p-4">
            <div className="flex items-center justify-between gap-4">
              <p className="font-medium">{reason.rule}</p>
              <p className="text-sm text-primary">
                score {reason.score} x weight {reason.weight}
              </p>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">{reason.explanation}</p>
            {reason.recommendedAction ? (
              <p className="mt-2 text-sm text-primary">{reason.recommendedAction}</p>
            ) : null}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
