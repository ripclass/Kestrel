"use client";

import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { AlertMutationPayload } from "@/types/api";
import type { AlertDetail } from "@/types/domain";

export function AlertActions({
  alert,
  pendingAction,
  notice,
  error,
  onAction,
}: {
  alert: AlertDetail;
  pendingAction: string | null;
  notice: string | null;
  error: string | null;
  onAction: (payload: AlertMutationPayload) => Promise<void>;
}) {
  const [caseTitle, setCaseTitle] = useState("");
  const [note, setNote] = useState("");

  return (
    <div className="space-y-5">
      <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
        <div className="space-y-2">
          <label className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            Case title
          </label>
          <Input
            value={caseTitle}
            onChange={(event) => setCaseTitle(event.target.value)}
            placeholder="Escalation title for case creation"
          />
        </div>
        <div className="space-y-2">
          <label className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            Action note
          </label>
          <Textarea
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Optional analyst note recorded alongside the action."
          />
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          variant="secondary"
          disabled={pendingAction !== null}
          onClick={() => void onAction({ action: "start_review", note })}
        >
          {pendingAction === "start_review" ? "Starting…" : "Start review"}
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={pendingAction !== null}
          onClick={() => void onAction({ action: "assign_to_me", note })}
        >
          {pendingAction === "assign_to_me" ? "Assigning…" : "Assign to me"}
        </Button>
        <Button
          type="button"
          variant="ghost"
          disabled={pendingAction !== null}
          onClick={() => void onAction({ action: "escalate", note })}
        >
          {pendingAction === "escalate" ? "Escalating…" : "Escalate"}
        </Button>
        {!alert.caseId ? (
          <Button
            type="button"
            disabled={pendingAction !== null}
            onClick={() => void onAction({ action: "create_case", note, caseTitle })}
          >
            {pendingAction === "create_case" ? "Creating case…" : "Create case"}
          </Button>
        ) : (
          <Link href={`/cases/${alert.caseId}`} className="inline-flex">
            <Button type="button">Open case</Button>
          </Link>
        )}
        <Button
          type="button"
          variant="outline"
          disabled={pendingAction !== null}
          onClick={() => void onAction({ action: "mark_true_positive", note })}
        >
          {pendingAction === "mark_true_positive" ? "Confirming…" : "Mark true positive"}
        </Button>
        <Button
          type="button"
          variant="destructive"
          disabled={pendingAction !== null}
          onClick={() => void onAction({ action: "mark_false_positive", note })}
        >
          {pendingAction === "mark_false_positive" ? "Closing…" : "Mark false positive"}
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
          <span aria-hidden className="mr-2">┼</span>
          ERROR · {error}
        </p>
      ) : null}
    </div>
  );
}
