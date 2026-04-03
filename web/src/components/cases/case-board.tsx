"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Currency } from "@/components/common/currency";
import { EmptyState } from "@/components/common/empty-state";
import { LoadingState } from "@/components/common/loading";
import { StatusBadge } from "@/components/common/status-badge";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { CaseListResponse } from "@/types/api";
import type { CaseSummary } from "@/types/domain";

export function CaseBoard({
  casesToShow,
  title = "Case board",
}: {
  casesToShow?: number;
  title?: string;
}) {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    void (async () => {
      try {
        const response = await fetch("/api/cases", { cache: "no-store" });
        const payload = (await readResponsePayload<CaseListResponse>(response)) as
          | CaseListResponse
          | { detail?: string };
        if (!response.ok) {
          setError(detailFromPayload(payload, "Unable to load cases."));
          return;
        }
        setCases((payload as CaseListResponse).cases);
        setError(null);
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "Unable to load cases.");
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  const visibleCases = casesToShow ? cases.slice(0, casesToShow) : cases;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading ? (
          <LoadingState label="Loading case board..." />
        ) : error ? (
          <EmptyState title="Case board unavailable" description={error} />
        ) : visibleCases.length === 0 ? (
          <EmptyState title="No cases yet" description="Escalated alerts will begin to appear here as active workspaces." />
        ) : (
          visibleCases.map((item) => (
            <Link
              key={item.id}
              href={`/cases/${item.id}`}
              className="block rounded-xl border border-border/70 bg-background/50 p-4 transition hover:border-primary/50"
            >
              <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-3">
                    <p className="font-medium">{item.caseRef}</p>
                    <StatusBadge status={item.status} />
                  </div>
                  <p className="text-sm">{item.title}</p>
                  <p className="text-sm text-muted-foreground">{item.summary}</p>
                </div>
                <div className="space-y-1 text-sm text-muted-foreground">
                  <p>Exposure: <Currency amount={item.totalExposure} /></p>
                  <p>{item.linkedEntityIds.length} linked entities</p>
                  {item.assignedTo ? <p>Assigned: {item.assignedTo}</p> : null}
                </div>
              </div>
            </Link>
          ))
        )}
      </CardContent>
    </Card>
  );
}
