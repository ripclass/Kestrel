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
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-[1fr_1.2fr]">
        <div className="space-y-2">
          <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Case title</label>
          <Input
            value={caseTitle}
            onChange={(event) => setCaseTitle(event.target.value)}
            placeholder="Escalation title for case creation"
          />
        </div>
        <div className="space-y-2">
          <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Action note</label>
          <Textarea
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Optional analyst note recorded alongside the action."
          />
        </div>
      </div>
      <div className="flex flex-wrap gap-3">
        <Button
          type="button"
          variant="secondary"
          disabled={pendingAction !== null}
          onClick={() => void onAction({ action: "start_review", note })}
        >
          {pendingAction === "start_review" ? "Starting..." : "Start review"}
        </Button>
        <Button
          type="button"
          variant="outline"
          disabled={pendingAction !== null}
          onClick={() => void onAction({ action: "assign_to_me", note })}
        >
          {pendingAction === "assign_to_me" ? "Assigning..." : "Assign to me"}
        </Button>
        <Button
          type="button"
          variant="ghost"
          disabled={pendingAction !== null}
          onClick={() => void onAction({ action: "escalate", note })}
        >
          {pendingAction === "escalate" ? "Escalating..." : "Escalate"}
        </Button>
        {!alert.caseId ? (
          <Button
            type="button"
            disabled={pendingAction !== null}
            onClick={() => void onAction({ action: "create_case", note, caseTitle })}
          >
            {pendingAction === "create_case" ? "Creating case..." : "Create case"}
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
          {pendingAction === "mark_true_positive" ? "Confirming..." : "Mark true positive"}
        </Button>
        <Button
          type="button"
          variant="destructive"
          disabled={pendingAction !== null}
          onClick={() => void onAction({ action: "mark_false_positive", note })}
        >
          {pendingAction === "mark_false_positive" ? "Closing..." : "Mark false positive"}
        </Button>
      </div>
      {notice ? <p className="text-sm text-primary/80">{notice}</p> : null}
      {error ? <p className="text-sm text-red-300">{error}</p> : null}
    </div>
  );
}
