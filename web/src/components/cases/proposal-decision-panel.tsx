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
    <section className="border border-accent/40 bg-accent/[0.04]">
      <div className="border-b border-accent/30 px-5 py-3">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-accent">
          <span aria-hidden className="mr-2">┼</span>
          Proposal decision {alreadyDecided ? `· ${decision}` : "· pending"}
        </p>
      </div>
      <div className="space-y-4 px-5 py-5">
        <p className="text-sm leading-relaxed text-foreground">
          {alreadyDecided
            ? `This proposal was ${decision}${decidedBy ? ` by ${decidedBy}` : ""}${
                decidedAt ? ` on ${new Date(decidedAt).toLocaleString()}` : ""
              }.`
            : "Decide whether to promote this proposal into a standard case, or reject it outright."}
        </p>
        {!alreadyDecided ? (
          <>
            <Textarea
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder="Optional note — captured on the case timeline."
            />
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                disabled={disabled || pending !== null}
                onClick={() => void decide("approved")}
              >
                {pending === "approved" ? "Approving…" : "Approve — open as case"}
              </Button>
              <Button
                type="button"
                variant="outline"
                disabled={disabled || pending !== null}
                onClick={() => void decide("rejected")}
              >
                {pending === "rejected" ? "Rejecting…" : "Reject"}
              </Button>
            </div>
          </>
        ) : null}
      </div>
    </section>
  );
}
