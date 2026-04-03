"use client";

import { useEffect, useState } from "react";

import { CaseTimeline } from "@/components/cases/case-timeline";
import { CaseNotes } from "@/components/cases/case-notes";
import { CaseEvidence } from "@/components/cases/case-evidence";
import { CaseExport } from "@/components/cases/case-export";
import { Currency } from "@/components/common/currency";
import { EmptyState } from "@/components/common/empty-state";
import { LoadingState } from "@/components/common/loading";
import { StatusBadge } from "@/components/common/status-badge";
import { NetworkCanvas } from "@/components/investigate/network-canvas";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { CaseMutationPayload, CaseMutationResponse, CaseWorkspaceResponse } from "@/types/api";
import type { CaseWorkspace as CaseWorkspaceModel } from "@/types/domain";

function actionLabel(payload: CaseMutationPayload) {
  if (payload.action === "add_note") {
    return "Case note added.";
  }
  if (payload.action === "assign_to_me") {
    return "Case assigned to you.";
  }
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

  if (isLoading) {
    return <LoadingState label="Loading case workspace..." />;
  }

  if (!workspace) {
    return <EmptyState title="Case not found" description={error ?? "This case is unavailable in the current scope."} />;
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-2">
              <CardTitle>{workspace.caseRef}</CardTitle>
              <p className="text-sm text-muted-foreground">{workspace.title}</p>
              <p className="text-sm text-muted-foreground">{workspace.summary}</p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <StatusBadge status={workspace.status} />
              <span className="text-sm text-muted-foreground">
                Exposure: <Currency amount={workspace.totalExposure} />
              </span>
              {workspace.assignedTo ? <span className="text-sm text-muted-foreground">Assigned: {workspace.assignedTo}</span> : null}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
            <span>{workspace.linkedEntityIds.length} linked entities</span>
            <span>{workspace.linkedAlertIds.length} linked alerts</span>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button
              type="button"
              variant="outline"
              disabled={pendingAction !== null}
              onClick={() => void runAction({ action: "assign_to_me" })}
            >
              {pendingAction === "assign_to_me" ? "Assigning..." : "Assign to me"}
            </Button>
            <select
              className="h-10 rounded-lg border border-input bg-background/60 px-3 text-sm outline-none focus:border-primary"
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
              {pendingAction === "update_status" ? "Updating..." : "Update status"}
            </Button>
          </div>
          {notice ? <p className="text-sm text-primary/80">{notice}</p> : null}
          {error ? <p className="text-sm text-red-300">{error}</p> : null}
        </CardContent>
      </Card>
      <CaseExport />
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
