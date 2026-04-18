"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { AiExplanation } from "@/components/alerts/ai-explanation";
import { AlertActions } from "@/components/alerts/alert-actions";
import { Explainability } from "@/components/alerts/explainability";
import { DisseminateAction } from "@/components/disseminations/disseminate-action";
import { EmptyState } from "@/components/common/empty-state";
import { LoadingState } from "@/components/common/loading";
import { StatusBadge } from "@/components/common/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { NetworkCanvas } from "@/components/investigate/network-canvas";
import { RiskScore } from "@/components/common/risk-score";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { AiExplanation as AiExplanationModel, AlertDetail as AlertDetailModel } from "@/types/domain";
import type {
  AiExplanationResponse,
  AiStrNarrativeResponse,
  AlertDetailResponse,
  AlertMutationPayload,
  AlertMutationResponse,
  STRMutationResponse,
} from "@/types/api";

function actionLabel(action: AlertMutationPayload["action"]) {
  switch (action) {
    case "start_review":
      return "Review started.";
    case "assign_to_me":
      return "Alert assigned to you.";
    case "escalate":
      return "Alert escalated.";
    case "mark_true_positive":
      return "Alert marked true positive.";
    case "mark_false_positive":
      return "Alert marked false positive.";
    case "create_case":
      return "Case created from alert.";
  }
}

function shortId(id: string) {
  if (id.length <= 10) return id;
  return `${id.slice(0, 4)}··${id.slice(-4)}`;
}

export function AlertDetail({ alertId }: { alertId: string }) {
  const router = useRouter();
  const [alert, setAlert] = useState<AlertDetailModel | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [aiExplanation, setAiExplanation] = useState<AiExplanationModel | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const [strDrafting, setStrDrafting] = useState(false);

  useEffect(() => {
    void (async () => {
      try {
        const response = await fetch(`/api/alerts/${alertId}`, { cache: "no-store" });
        const payload = (await readResponsePayload<AlertDetailResponse>(response)) as
          | AlertDetailResponse
          | { detail?: string };
        if (!response.ok) {
          setError(detailFromPayload(payload, "Unable to load alert detail."));
          return;
        }
        setAlert((payload as AlertDetailResponse).alert);
        setError(null);
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "Unable to load alert detail.");
      } finally {
        setIsLoading(false);
      }
    })();
  }, [alertId]);

  useEffect(() => {
    if (!alert) return;
    setAiLoading(true);
    void (async () => {
      try {
        const response = await fetch(`/api/ai/alerts/${alertId}/explanation`, {
          method: "POST",
        });
        if (!response.ok) {
          setAiError("AI analysis unavailable.");
          return;
        }
        const payload = (await readResponsePayload<AiExplanationResponse>(response)) as AiExplanationResponse;
        setAiExplanation(payload.result);
      } catch {
        setAiError("AI analysis unavailable.");
      } finally {
        setAiLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [alertId, isLoading]);

  async function runAction(payload: AlertMutationPayload) {
    setPendingAction(payload.action);
    setError(null);
    setNotice(null);
    try {
      const response = await fetch(`/api/alerts/${alertId}/actions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = (await readResponsePayload<AlertMutationResponse>(response)) as
        | AlertMutationResponse
        | { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(result, "Unable to update alert."));
        return;
      }
      const mutation = result as AlertMutationResponse;
      setAlert(mutation.alert);
      setNotice(actionLabel(payload.action));
      if (payload.action === "create_case" && mutation.case) {
        router.push(`/cases/${mutation.case.id}`);
      }
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to update alert.");
    } finally {
      setPendingAction(null);
    }
  }

  async function draftStr() {
    if (!alert?.entity) return;
    setStrDrafting(true);
    setError(null);
    try {
      const narrativeRes = await fetch("/api/ai/str-narrative", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subjectName: alert.entity.displayName ?? alert.entity.displayValue,
          subjectAccount: alert.entity.entityType === "account" ? alert.entity.canonicalValue : undefined,
          category: alert.alertType,
          triggerFacts: alert.reasons.map((r) => r.explanation),
        }),
      });
      let narrative = "";
      let category = alert.alertType || "fraud";
      if (narrativeRes.ok) {
        const narrativePayload = (await readResponsePayload<AiStrNarrativeResponse>(
          narrativeRes,
        )) as AiStrNarrativeResponse;
        narrative = narrativePayload.result.narrative;
        category = narrativePayload.result.categorySuggestion || category;
      }

      const strRes = await fetch("/api/str-reports", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subjectName: alert.entity.displayName ?? alert.entity.displayValue,
          subjectAccount: alert.entity.entityType === "account"
            ? alert.entity.canonicalValue
            : alert.entity.displayValue,
          totalAmount: alert.entity.totalExposure ?? 0,
          currency: "BDT",
          transactionCount: 0,
          category,
          channels: [],
          narrative,
          metadata: { source_alert_id: alert.id, ai_generated: true },
        }),
      });
      if (!strRes.ok) {
        const strPayload = await readResponsePayload<{ detail?: string }>(strRes);
        setError(detailFromPayload(strPayload, "Failed to create STR draft."));
        return;
      }
      const strPayload = (await readResponsePayload<STRMutationResponse>(strRes)) as STRMutationResponse;
      router.push(`/strs/${strPayload.report.id}`);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Failed to draft STR.");
    } finally {
      setStrDrafting(false);
    }
  }

  if (isLoading) {
    return <LoadingState label="Loading alert detail…" />;
  }

  if (!alert) {
    return (
      <EmptyState
        title="Alert not found"
        description={error ?? "This alert is unavailable in the current scope."}
      />
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-6 lg:flex-row lg:items-start lg:justify-between">
            <div className="space-y-3">
              <p className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
                <span aria-hidden className="leading-none text-accent">┼</span>
                Alert · {shortId(alert.id)} · {alert.alertType}
              </p>
              <h2 className="text-2xl font-semibold tracking-tight text-foreground">{alert.title}</h2>
              <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">{alert.description}</p>
            </div>
            <RiskScore score={alert.riskScore} severity={alert.severity} />
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 gap-0 border border-border md:grid-cols-4">
            <Meta label="Status">
              <StatusBadge status={alert.status} />
            </Meta>
            <Meta label="Org">
              <span className="text-sm text-foreground">{alert.orgName}</span>
            </Meta>
            <Meta label="Assigned">
              <span className="text-sm text-foreground">{alert.assignedTo ?? "—"}</span>
            </Meta>
            <Meta label="Linked case">
              {alert.caseId ? (
                <Link
                  href={`/cases/${alert.caseId}`}
                  className="font-mono text-sm text-foreground underline decoration-accent decoration-2 underline-offset-4 transition hover:text-accent"
                >
                  Open case
                </Link>
              ) : (
                <span className="text-sm text-muted-foreground">—</span>
              )}
            </Meta>
          </div>

          {alert.entity ? (
            <div className="flex items-center justify-between border border-border bg-white/[0.02] px-4 py-3">
              <div className="flex items-center gap-3 text-sm">
                <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
                  Subject
                </span>
                <span className="font-mono text-foreground">
                  {alert.entity.entityType}
                </span>
                <span className="text-muted-foreground">·</span>
                <span className="font-mono text-foreground">
                  {alert.entity.displayName ?? alert.entity.displayValue}
                </span>
              </div>
              <Link
                href={`/investigate/entity/${alert.entity.id}`}
                className="font-mono text-[11px] uppercase tracking-[0.22em] text-accent transition hover:text-foreground"
              >
                Open dossier →
              </Link>
            </div>
          ) : null}

          <AlertActions
            alert={alert}
            pendingAction={pendingAction}
            notice={notice}
            error={error}
            onAction={runAction}
          />

          <div className="flex flex-wrap gap-3 border-t border-border pt-4">
            {alert.entity && !alert.caseId ? (
              <Button
                type="button"
                variant="outline"
                disabled={strDrafting || pendingAction !== null}
                onClick={() => void draftStr()}
              >
                {strDrafting ? "Drafting STR…" : "Draft STR from alert"}
              </Button>
            ) : null}
            <DisseminateAction
              linkedEntityId={alert.entity?.id}
              linkedCaseId={alert.caseId ?? undefined}
              defaultSubject={`${alert.title}\n\n${alert.description}`}
              variant="outline"
            />
          </div>
        </CardContent>
      </Card>
      <AiExplanation explanation={aiExplanation} isLoading={aiLoading} error={aiError} />
      <Explainability reasons={alert.reasons} />
      <NetworkCanvas graph={alert.graph} />
    </div>
  );
}

function Meta({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-2 border-b border-border p-4 last:border-b-0 md:border-b-0 md:border-r md:last:border-r-0">
      <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">{label}</span>
      {children}
    </div>
  );
}
