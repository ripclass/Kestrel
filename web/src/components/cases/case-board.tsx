"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Currency } from "@/components/common/currency";
import { EmptyState } from "@/components/common/empty-state";
import { LoadingState } from "@/components/common/loading";
import { StatusBadge } from "@/components/common/status-badge";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { CaseListResponse } from "@/types/api";
import type { CaseSummary, CaseVariant, ProposalDecision } from "@/types/domain";

const VARIANTS: CaseVariant[] = [
  "standard",
  "proposal",
  "rfi",
  "operation",
  "project",
  "escalated",
  "complaint",
  "adverse_media",
];

const variantLabel: Record<CaseVariant, string> = {
  standard: "Standard",
  proposal: "Proposals",
  rfi: "RFI",
  operation: "Operations",
  project: "Projects",
  escalated: "Escalated",
  complaint: "Complaints",
  adverse_media: "Adverse Media",
};

const variantBadgeClass: Record<CaseVariant, string> = {
  standard: "bg-slate-500/20 text-slate-300 border-slate-500/30",
  proposal: "bg-amber-500/20 text-amber-300 border-amber-500/30",
  rfi: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30",
  operation: "bg-purple-500/20 text-purple-300 border-purple-500/30",
  project: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  escalated: "bg-red-500/20 text-red-300 border-red-500/30",
  complaint: "bg-rose-500/20 text-rose-300 border-rose-500/30",
  adverse_media: "bg-orange-500/20 text-orange-300 border-orange-500/30",
};

type VariantFilter = "all" | CaseVariant;

const PROPOSAL_COLUMNS: { id: ProposalDecision; label: string }[] = [
  { id: "pending", label: "Pending" },
  { id: "approved", label: "Approved" },
  { id: "rejected", label: "Rejected" },
];

function CaseTile({ item }: { item: CaseSummary }) {
  return (
    <Link
      href={`/cases/${item.id}`}
      className="block rounded-xl border border-border/70 bg-background/50 p-4 transition hover:border-primary/50"
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-3">
            <p className="font-medium">{item.caseRef}</p>
            <StatusBadge status={item.status} />
            <span
              className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold tracking-widest ${variantBadgeClass[item.variant]}`}
            >
              {variantLabel[item.variant]}
            </span>
          </div>
          <p className="text-sm">{item.title}</p>
          <p className="text-sm text-muted-foreground">{item.summary}</p>
          {item.variant === "rfi" ? (
            <p className="text-xs text-muted-foreground">
              {item.requestedBy ? `From ${item.requestedBy}` : ""}
              {item.requestedBy && item.requestedFrom ? " → " : ""}
              {item.requestedFrom ? `To ${item.requestedFrom}` : ""}
            </p>
          ) : null}
        </div>
        <div className="space-y-1 text-sm text-muted-foreground">
          <p>Exposure: <Currency amount={item.totalExposure} /></p>
          <p>{item.linkedEntityIds.length} linked entities</p>
          {item.assignedTo ? <p>Assigned: {item.assignedTo}</p> : null}
        </div>
      </div>
    </Link>
  );
}

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
  const [filter, setFilter] = useState<VariantFilter>("all");

  useEffect(() => {
    setIsLoading(true);
    void (async () => {
      try {
        const url = filter === "all" ? "/api/cases" : `/api/cases?variant=${filter}`;
        const response = await fetch(url, { cache: "no-store" });
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
  }, [filter]);

  const visibleCases = casesToShow ? cases.slice(0, casesToShow) : cases;

  const proposalsByDecision = useMemo(() => {
    const groups: Record<ProposalDecision, CaseSummary[]> = {
      pending: [],
      approved: [],
      rejected: [],
    };
    for (const c of visibleCases) {
      const decision = c.proposalDecision ?? "pending";
      groups[decision].push(c);
    }
    return groups;
  }, [visibleCases]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {!casesToShow ? (
          <div className="flex flex-wrap gap-2">
            {(["all", ...VARIANTS] as VariantFilter[]).map((type) => (
              <button
                key={type}
                type="button"
                onClick={() => setFilter(type)}
                className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
                  filter === type
                    ? "border-primary bg-primary/15 text-primary"
                    : "border-border text-muted-foreground hover:border-primary/40"
                }`}
              >
                {type === "all" ? "All" : variantLabel[type]}
              </button>
            ))}
          </div>
        ) : null}

        {isLoading ? (
          <LoadingState label="Loading case board..." />
        ) : error ? (
          <EmptyState title="Case board unavailable" description={error} />
        ) : visibleCases.length === 0 ? (
          <EmptyState title="No cases in this view" description="Adjust the variant filter or start a new proposal / RFI." />
        ) : filter === "proposal" ? (
          <div className="grid gap-4 md:grid-cols-3">
            {PROPOSAL_COLUMNS.map((col) => (
              <div key={col.id} className="space-y-3 rounded-xl border border-border/70 bg-background/40 p-3">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                    {col.label}
                  </p>
                  <span className="text-xs text-muted-foreground">{proposalsByDecision[col.id].length}</span>
                </div>
                {proposalsByDecision[col.id].length === 0 ? (
                  <p className="text-xs text-muted-foreground">No cases.</p>
                ) : (
                  proposalsByDecision[col.id].map((item) => <CaseTile key={item.id} item={item} />)
                )}
              </div>
            ))}
          </div>
        ) : (
          visibleCases.map((item) => <CaseTile key={item.id} item={item} />)
        )}
      </CardContent>
    </Card>
  );
}
