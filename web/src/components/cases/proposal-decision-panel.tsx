"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { CaseMutationResponse } from "@/types/api";
import type { CaseWorkspace, ProposalDecision } from "@/types/domain";

type Props = {
  caseId: string;
  decision: ProposalDecision;
  decidedBy?: string | null;
  decidedAt?: string | null;
  disabled?: boolean;
  onDecided: (next: CaseWorkspace) => void;
  onError: (message: string) => void;
};

export function ProposalDecisionPanel({
  caseId,
  decision,
  decidedBy,
  decidedAt,
  disabled,
  onDecided,
  onError,
}: Props) {
  const [note, setNote] = useState("");
  const [pending, setPending] = useState<ProposalDecision | null>(null);

  async function decide(target: "approved" | "rejected") {
    setPending(target);
    try {
      const response = await fetch(`/api/cases/${caseId}/decide`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision: target, note: note || undefined }),
      });
      const result = (await readResponsePayload<CaseMutationResponse>(response)) as
        | CaseMutationResponse
        | { detail?: string };
      if (!response.ok) {
        onError(detailFromPayload(result, "Unable to decide proposal."));
        return;
      }
      const { case: nextCase } = result as CaseMutationResponse;
      onDecided(nextCase);
      setNote("");
    } catch (err) {
      onError(err instanceof Error ? err.message : "Unable to decide proposal.");
    } finally {
      setPending(null);
    }
  }

  const alreadyDecided = decision !== "pending";

  return (
    <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-sm font-semibold">Case proposal</p>
          <p className="text-xs text-muted-foreground">
            {alreadyDecided
              ? `This proposal was ${decision}${decidedBy ? ` by ${decidedBy}` : ""}${
                  decidedAt ? ` on ${new Date(decidedAt).toLocaleString()}` : ""
                }.`
              : "Decide whether to promote this proposal into a standard case, or reject it outright."}
          </p>
        </div>
      </div>
      {!alreadyDecided ? (
        <div className="mt-4 space-y-3">
          <Textarea
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Optional note — captured on the case timeline."
          />
          <div className="flex flex-wrap gap-3">
            <Button
              type="button"
              disabled={disabled || pending !== null}
              onClick={() => void decide("approved")}
            >
              {pending === "approved" ? "Approving..." : "Approve (open as case)"}
            </Button>
            <Button
              type="button"
              variant="outline"
              disabled={disabled || pending !== null}
              onClick={() => void decide("rejected")}
            >
              {pending === "rejected" ? "Rejecting..." : "Reject"}
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
