"use client";

import { useEffect, useState } from "react";

import { CaseTimeline } from "@/components/cases/case-timeline";
import { CaseNotes } from "@/components/cases/case-notes";
import { CaseEvidence } from "@/components/cases/case-evidence";
import { CaseExport } from "@/components/cases/case-export";
import { ProposalDecisionPanel } from "@/components/cases/proposal-decision-panel";
import { Currency } from "@/components/common/currency";
import { DisseminateAction } from "@/components/disseminations/disseminate-action";
import { EmptyState } from "@/components/common/empty-state";
import { LoadingState } from "@/components/common/loading";
import { StatusBadge } from "@/components/common/status-badge";
import { NetworkCanvas } from "@/components/investigate/network-canvas";
import { Button } from "@/components/ui/button";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { CaseMutationPayload, CaseMutationResponse, CaseWorkspaceResponse } from "@/types/api";
import type { CaseWorkspace as CaseWorkspaceModel } from "@/types/domain";

function actionLabel(payload: CaseMutationPayload) {
  if (payload.action === "add_note") return "Case note added.";
  if (payload.action === "assign_to_me") return "Case assigned to you.";
  return `Case status updated to ${payload.status?.replaceAll("_", " ") ?? "the requested state"}.`;
}

const caseStatuses: NonNullable<CaseMutationPayload["status"]>[] = [
  "open",
  "investigating",
  "escalated",
  "pending_action",
  "closed_confirmed",
  "closed_false_positive",
];

function shortId(id: string) {
  if (id.length <= 10) return id;
  return `${id.slice(0, 4)}··${id.slice(-4)}`;
}

export function CaseWorkspace({ caseId }: { caseId: string }) {
  const [workspace, setWorkspace] = useState<CaseWorkspaceModel | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [status, setStatus] = useState<NonNullable<CaseMutationPayload["status"]>>("investigating");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    void (async () => {
      try {
        const response = await fetch(`/api/cases/${caseId}`, { cache: "no-store" });
        const payload = (await readResponsePayload<CaseWorkspaceResponse>(response)) as
          | CaseWorkspaceResponse
          | { detail?: string };
        if (!response.ok) {
          setError(detailFromPayload(payload, "Unable to load case workspace."));
          return;
        }
        const nextCase = (payload as CaseWorkspaceResponse).case;
        setWorkspace(nextCase);
        setStatus(nextCase.status);
        setError(null);
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "Unable to load case workspace.");
      } finally {
        setIsLoading(false);
      }
    })();
  }, [caseId]);

  async function runAction(payload: CaseMutationPayload) {
    setPendingAction(payload.action);
    setError(null);
    setNotice(null);
    try {
      const response = await fetch(`/api/cases/${caseId}/actions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = (await readResponsePayload<CaseMutationResponse>(response)) as
        | CaseMutationResponse
        | { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(result, "Unable to update case."));
        return;
      }
      const mutation = result as CaseMutationResponse;
      setWorkspace(mutation.case);
      setStatus(mutation.case.status);
      setNotice(actionLabel(payload));
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to update case.");
    } finally {
      setPendingAction(null);
    }
  }

  if (isLoading) return <LoadingState label="Loading case workspace…" />;

  if (!workspace) {
    return (
      <EmptyState
        title="Case not found"
        description={error ?? "This case is unavailable in the current scope."}
      />
    );
  }

  return (
    <div className="space-y-6">
      <section className="border border-border">
        <div className="flex flex-col gap-6 border-b border-border px-6 py-6 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-3">
            <p className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
              <span aria-hidden className="leading-none text-accent">┼</span>
              Case · {workspace.caseRef} · {shortId(caseId)}
            </p>
            <h2 className="text-2xl font-semibold tracking-tight text-foreground">
              {workspace.title}
            </h2>
            <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">
              {workspace.summary}
            </p>
          </div>
          <div className="flex flex-col items-start gap-2 lg:items-end">
            <StatusBadge status={workspace.status} />
            <span className="border border-border px-3 py-1 font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
              Variant · {workspace.variant.replaceAll("_", " ")}
            </span>
          </div>
        </div>
        <div className="grid grid-cols-2 divide-x divide-y divide-border lg:grid-cols-4 lg:divide-y-0">
          <Meta label="Exposure">
            <span className="font-mono text-lg tabular-nums text-foreground">
              <Currency amount={workspace.totalExposure} />
            </span>
          </Meta>
          <Meta label="Linked entities">
            <span className="font-mono text-lg tabular-nums text-foreground">
              {workspace.linkedEntityIds.length}
            </span>
          </Meta>
          <Meta label="Linked alerts">
            <span className="font-mono text-lg tabular-nums text-foreground">
              {workspace.linkedAlertIds.length}
            </span>
          </Meta>
          <Meta label="Assigned">
            <span className="text-sm text-foreground">{workspace.assignedTo ?? "—"}</span>
          </Meta>
        </div>

        <div className="space-y-5 px-6 py-5">
          <div className="flex flex-wrap items-center gap-3">
            {workspace.parentCaseId ? (
              <a
                href={`/cases/${workspace.parentCaseId}`}
                className="font-mono text-[11px] uppercase tracking-[0.22em] text-accent transition hover:text-foreground"
              >
                ↖ Parent case
              </a>
            ) : null}
            {workspace.variant === "rfi" && workspace.requestedBy ? (
              <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                From · {workspace.requestedBy}
              </span>
            ) : null}
            {workspace.variant === "rfi" && workspace.requestedFrom ? (
              <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                To · {workspace.requestedFrom}
              </span>
            ) : null}
          </div>

          {workspace.variant === "proposal" ? (
            <ProposalDecisionPanel
              caseId={caseId}
              decision={workspace.proposalDecision ?? "pending"}
              decidedBy={workspace.proposalDecidedBy}
              decidedAt={workspace.proposalDecidedAt}
              disabled={pendingAction !== null}
              onDecided={(nextCase) => {
                setWorkspace(nextCase);
                setStatus(nextCase.status);
                setNotice(`Proposal ${nextCase.proposalDecision}.`);
              }}
              onError={(message) => setError(message)}
            />
          ) : null}

          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              variant="outline"
              disabled={pendingAction !== null}
              onClick={() => void runAction({ action: "assign_to_me" })}
            >
              {pendingAction === "assign_to_me" ? "Assigning…" : "Assign to me"}
            </Button>
            <select
              className="h-10 border border-input bg-card px-3 font-mono text-[11px] uppercase tracking-[0.2em] text-foreground outline-none focus:border-foreground"
              value={status}
              onChange={(event) => setStatus(event.target.value as NonNullable<CaseMutationPayload["status"]>)}
            >
              {caseStatuses.map((value) => (
                <option key={value} value={value}>
                  {value.replaceAll("_", " ")}
                </option>
              ))}
            </select>
            <Button
              type="button"
              disabled={pendingAction !== null}
              onClick={() => void runAction({ action: "update_status", status })}
            >
              {pendingAction === "update_status" ? "Updating…" : "Update status"}
            </Button>
            <DisseminateAction
              linkedCaseId={caseId}
              defaultSubject={`Case ${workspace.caseRef}: ${workspace.title}\n\n${workspace.summary}`}
              variant="outline"
            />
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
        </div>
      </section>

      <CaseExport caseId={caseId} caseRef={workspace.caseRef} />

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <CaseTimeline events={workspace.timeline} />
        <CaseNotes
          notes={workspace.notes}
          isSubmitting={pendingAction === "add_note"}
          onAddNote={(note) => runAction({ action: "add_note", note })}
        />
      </div>
      {workspace.graph ? <NetworkCanvas graph={workspace.graph} /> : null}
      <CaseEvidence entities={workspace.evidenceEntities} />
    </div>
  );
}

function Meta({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-3 p-5">
      <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
        {label}
      </span>
      {children}
    </div>
  );
}
