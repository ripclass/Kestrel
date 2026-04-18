"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

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

// Collapsed to Sovereign Ledger's three tones. Escalated = alarm; most
// others sit in foreground/neutral; RFI reads as in-flight.
const variantTone: Record<CaseVariant, string> = {
  standard: "border-border text-muted-foreground",
  proposal: "border-foreground/30 text-foreground",
  rfi: "border-foreground/30 text-foreground",
  operation: "border-foreground/30 text-foreground",
  project: "border-border text-muted-foreground",
  escalated: "border-accent/50 text-accent",
  complaint: "border-foreground/30 text-foreground",
  adverse_media: "border-accent/40 text-accent",
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
      className="block border border-border bg-card px-5 py-4 transition hover:bg-foreground/[0.03]"
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-3">
            <p className="font-mono text-sm text-foreground">{item.caseRef}</p>
            <StatusBadge status={item.status} />
            <span
              className={`inline-flex items-center border px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.22em] ${variantTone[item.variant]}`}
            >
              {variantLabel[item.variant]}
            </span>
          </div>
          <p className="text-sm text-foreground">{item.title}</p>
          <p className="text-sm leading-relaxed text-muted-foreground">{item.summary}</p>
          {item.variant === "rfi" ? (
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              {item.requestedBy ? `From ${item.requestedBy}` : ""}
              {item.requestedBy && item.requestedFrom ? " → " : ""}
              {item.requestedFrom ? `To ${item.requestedFrom}` : ""}
            </p>
          ) : null}
        </div>
        <div className="space-y-1 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          <p>
            Exposure · <span className="tabular-nums text-foreground"><Currency amount={item.totalExposure} /></span>
          </p>
          <p>
            <span className="tabular-nums">{item.linkedEntityIds.length}</span> linked entities
          </p>
          {item.assignedTo ? <p>Assigned · {item.assignedTo}</p> : null}
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
    <section className="border border-border">
      <div className="border-b border-border px-6 py-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Section · {title}
        </p>
      </div>
      <div className="space-y-5 p-6">
        {!casesToShow ? (
          <div className="flex flex-wrap gap-0 border border-border">
            {(["all", ...VARIANTS] as VariantFilter[]).map((type) => (
              <button
                key={type}
                type="button"
                onClick={() => setFilter(type)}
                className={`border-r border-border px-4 py-2 font-mono text-[11px] uppercase tracking-[0.22em] transition last:border-r-0 ${
                  filter === type
                    ? "bg-foreground text-background"
                    : "text-muted-foreground hover:bg-foreground/[0.04] hover:text-foreground"
                }`}
              >
                {type === "all" ? "All" : variantLabel[type]}
              </button>
            ))}
          </div>
        ) : null}

        {isLoading ? (
          <LoadingState label="Loading case board…" />
        ) : error ? (
          <EmptyState title="Case board unavailable" description={error} />
        ) : visibleCases.length === 0 ? (
          <EmptyState
            title="No cases in this view"
            description="Adjust the variant filter or start a new proposal / RFI."
          />
        ) : filter === "proposal" ? (
          <div className="grid gap-4 md:grid-cols-3">
            {PROPOSAL_COLUMNS.map((col) => (
              <div key={col.id} className="border border-border bg-card/40">
                <div className="flex items-center justify-between border-b border-border px-4 py-2">
                  <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
                    {col.label}
                  </p>
                  <span className="font-mono text-xs tabular-nums text-foreground">
                    {String(proposalsByDecision[col.id].length).padStart(2, "0")}
                  </span>
                </div>
                <div className="space-y-3 p-3">
                  {proposalsByDecision[col.id].length === 0 ? (
                    <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                      No cases
                    </p>
                  ) : (
                    proposalsByDecision[col.id].map((item) => <CaseTile key={item.id} item={item} />)
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            {visibleCases.map((item) => (
              <CaseTile key={item.id} item={item} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
