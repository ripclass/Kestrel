"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { SyntheticBackfillApplyResponse } from "@/types/api";
import type { SyntheticBackfillPlan, SyntheticBackfillResult } from "@/types/domain";

export function SyntheticBackfillCard({
  initialPlan,
}: {
  initialPlan: SyntheticBackfillPlan | null;
}) {
  const router = useRouter();
  const [isRunning, setIsRunning] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [result, setResult] = useState<SyntheticBackfillResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function runBackfill() {
    setIsRunning(true);
    setNotice(null);
    setError(null);
    const response = await fetch("/api/admin/synthetic-backfill", {
      method: "POST",
    });
    const payload = await readResponsePayload<SyntheticBackfillApplyResponse>(response);

    if (!response.ok) {
      setError(detailFromPayload(payload, "Unable to run synthetic backfill."));
      setIsRunning(false);
      return;
    }

    const nextResult = (payload as SyntheticBackfillApplyResponse).result;
    setResult(nextResult);
    setNotice(`Synthetic backfill applied: ${nextResult.entities} entities and ${nextResult.strReports} STRs refreshed.`);
    setIsRunning(false);
    router.refresh();
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Synthetic intelligence backfill</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm text-muted-foreground">
        <p>
          Regulator admins can reapply the sanitized DBBL-derived synthetic dataset into shared intelligence tables from the live environment.
        </p>
        {initialPlan ? (
          <div className="grid gap-3 sm:grid-cols-2">
            {[
              ["Statements", initialPlan.statements],
              ["Entities", initialPlan.entities],
              ["Matches", initialPlan.matches],
              ["Transactions", initialPlan.transactions],
              ["Connections", initialPlan.connections],
            ].map(([label, value]) => (
              <div key={String(label)} className="rounded-2xl border border-border/70 bg-background/50 p-4">
                <p className="text-xs uppercase tracking-[0.24em] text-primary">{label}</p>
                <p className="mt-2 text-xl font-semibold text-foreground">{value}</p>
              </div>
            ))}
          </div>
        ) : (
          <p>The synthetic dataset plan is unavailable on this deployment.</p>
        )}
        <div className="flex gap-3">
          <Button type="button" disabled={isRunning || !initialPlan} onClick={() => void runBackfill()}>
            {isRunning ? "Running..." : "Run backfill"}
          </Button>
        </div>
        {notice ? <p className="text-primary">{notice}</p> : null}
        {error ? <p className="text-destructive">{error}</p> : null}
        {result ? (
          <div className="rounded-2xl border border-border/70 bg-background/50 p-4">
            <p className="text-xs uppercase tracking-[0.24em] text-primary">Latest result</p>
            <p className="mt-2 text-foreground">
              {result.organizations} orgs, {result.entities} entities, {result.matches} matches, {result.alerts} alerts, {result.cases} cases.
            </p>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
