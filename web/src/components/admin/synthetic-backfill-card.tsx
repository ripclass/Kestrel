"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { SyntheticBackfillApplyResponse } from "@/types/api";
import type { SyntheticBackfillPlan, SyntheticBackfillResult } from "@/types/domain";

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex flex-col gap-3 border-r border-b border-border p-5 last:border-r-0">
      <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
        {label}
      </span>
      <span className="font-mono text-2xl tabular-nums text-foreground">{value.toLocaleString()}</span>
    </div>
  );
}

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
    const response = await fetch("/api/admin/synthetic-backfill", { method: "POST" });
    const payload = await readResponsePayload<SyntheticBackfillApplyResponse>(response);

    if (!response.ok) {
      setError(detailFromPayload(payload, "Unable to run synthetic backfill."));
      setIsRunning(false);
      return;
    }

    const nextResult = (payload as SyntheticBackfillApplyResponse).result;
    setResult(nextResult);
    setNotice(
      `Synthetic backfill applied · ${nextResult.entities} entities and ${nextResult.strReports} STRs refreshed.`,
    );
    setIsRunning(false);
    router.refresh();
  }

  return (
    <section className="border border-border">
      <div className="border-b border-border px-6 py-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Section · Synthetic intelligence backfill
        </p>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          Regulator admins can reapply the sanitised DBBL-derived synthetic dataset into shared
          intelligence tables from the live environment.
        </p>
      </div>
      <div className="space-y-5 p-6">
        {initialPlan ? (
          <div className="grid grid-cols-2 border-l border-t border-border sm:grid-cols-3 lg:grid-cols-5">
            <Stat label="Statements" value={initialPlan.statements} />
            <Stat label="Entities" value={initialPlan.entities} />
            <Stat label="Matches" value={initialPlan.matches} />
            <Stat label="Transactions" value={initialPlan.transactions} />
            <Stat label="Connections" value={initialPlan.connections} />
          </div>
        ) : (
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
            The synthetic dataset plan is unavailable on this deployment
          </p>
        )}
        <div className="flex gap-2 border-t border-border pt-4">
          <Button type="button" disabled={isRunning || !initialPlan} onClick={() => void runBackfill()}>
            {isRunning ? "Running…" : "Run backfill"}
          </Button>
        </div>
        {notice ? (
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-accent">
            <span aria-hidden className="mr-2">┼</span>
            {notice}
          </p>
        ) : null}
        {error ? (
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
            <span aria-hidden className="mr-2">┼</span>ERROR · {error}
          </p>
        ) : null}
        {result ? (
          <div className="border border-border bg-card p-4">
            <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
              <span aria-hidden className="mr-2 text-accent">┼</span>
              Latest result
            </p>
            <p className="mt-2 text-sm leading-relaxed text-foreground">
              <span className="font-mono tabular-nums">{result.organizations}</span> orgs ·{" "}
              <span className="font-mono tabular-nums">{result.entities}</span> entities ·{" "}
              <span className="font-mono tabular-nums">{result.matches}</span> matches ·{" "}
              <span className="font-mono tabular-nums">{result.alerts}</span> alerts ·{" "}
              <span className="font-mono tabular-nums">{result.cases}</span> cases.
            </p>
          </div>
        ) : null}
      </div>
    </section>
  );
}
