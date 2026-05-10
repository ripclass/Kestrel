"use client";

import { useEffect, useState } from "react";

import { AiShimmer } from "@/components/common/ai-shimmer";
import { TypedReveal } from "@/components/common/typed-reveal";
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
  // Reveal recommended-actions one at a time once the summary + why
  // text has been on screen for ~200ms. Reset whenever the explanation
  // itself changes (e.g. analyst re-runs the AI on the same alert).
  const [revealedActions, setRevealedActions] = useState(0);

  useEffect(() => {
    if (!explanation || explanation.recommendedActions.length === 0) {
      setRevealedActions(0);
      return;
    }
    setRevealedActions(0);
    const handles: number[] = [];
    explanation.recommendedActions.forEach((_, i) => {
      handles.push(
        window.setTimeout(
          () => setRevealedActions((current) => Math.max(current, i + 1)),
          800 + i * 350,
        ),
      );
    });
    return () => {
      handles.forEach((h) => window.clearTimeout(h));
    };
  }, [explanation]);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            <span aria-hidden className="mr-2 text-accent">┼</span>Section · AI Analysis
          </p>
          <CardTitle className="font-mono uppercase tracking-[0.12em]">
            Generating explanation
          </CardTitle>
        </CardHeader>
        <CardContent>
          <AiShimmer lines={3} withActions />
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
          <p className="mt-2 text-sm leading-relaxed text-foreground">
            <TypedReveal text={explanation.summary} speed={75} />
          </p>
        </section>
        <section>
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            Why it matters
          </p>
          <p className="mt-2 text-sm leading-relaxed text-foreground">
            <TypedReveal text={explanation.whyItMatters} speed={75} />
          </p>
        </section>
        {explanation.recommendedActions.length > 0 ? (
          <section>
            <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
              Recommended actions
            </p>
            <ul className="mt-3 space-y-2">
              {explanation.recommendedActions.map((action, i) =>
                i < revealedActions ? (
                  <li
                    key={action}
                    className="flex items-start gap-3 text-sm leading-relaxed text-foreground motion-safe:animate-[fadeIn_300ms_ease-out]"
                  >
                    <span aria-hidden className="pt-1 font-mono leading-none text-accent">
                      ┼
                    </span>
                    <span>{action}</span>
                  </li>
                ) : null,
              )}
            </ul>
          </section>
        ) : null}
      </CardContent>
    </Card>
  );
}
