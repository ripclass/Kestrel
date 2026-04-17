import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { AiExplanation as AiExplanationModel } from "@/types/domain";

export function AiExplanation({
  explanation,
  isLoading,
  error,
}: {
  explanation: AiExplanationModel | null;
  isLoading: boolean;
  error: string | null;
}) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            <span aria-hidden className="mr-2 text-accent">┼</span>Section · AI Analysis
          </p>
          <CardTitle className="font-mono uppercase tracking-[0.12em]">Generating explanation</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">
            Transmitting…
          </p>
        </CardContent>
      </Card>
    );
  }

  if (error || !explanation) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>Section · AI Analysis
        </p>
        <CardTitle className="font-mono uppercase tracking-[0.12em]">Analyst briefing</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <section>
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            Summary
          </p>
          <p className="mt-2 text-sm leading-relaxed text-foreground">{explanation.summary}</p>
        </section>
        <section>
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            Why it matters
          </p>
          <p className="mt-2 text-sm leading-relaxed text-foreground">{explanation.whyItMatters}</p>
        </section>
        {explanation.recommendedActions.length > 0 ? (
          <section>
            <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
              Recommended actions
            </p>
            <ul className="mt-3 space-y-2">
              {explanation.recommendedActions.map((action) => (
                <li key={action} className="flex items-start gap-3 text-sm leading-relaxed text-foreground">
                  <span aria-hidden className="pt-1 font-mono leading-none text-accent">┼</span>
                  <span>{action}</span>
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </CardContent>
    </Card>
  );
}
