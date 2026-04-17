"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { STRMutationResponse } from "@/types/api";
import type { STRReportDetail } from "@/types/domain";

type Props = {
  parent: STRReportDetail;
  onCreated?: () => void;
};

export function SupplementAction({ parent, onCreated }: Props) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [narrative, setNarrative] = useState("");
  const [subjectAccount, setSubjectAccount] = useState(parent.subjectAccount ?? "");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) setError(null);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  async function submit() {
    if (!narrative.trim()) {
      setError("A narrative is required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const response = await fetch(`/api/str-reports/${parent.id}/supplements`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subjectName: parent.subjectName ?? null,
          subjectAccount: subjectAccount || null,
          subjectBank: parent.subjectBank ?? null,
          totalAmount: 0,
          currency: parent.currency ?? "BDT",
          transactionCount: 0,
          category: parent.category ?? "other",
          narrative,
          channels: [],
          metadata: { source: "supplement", parent_report_id: parent.id },
        }),
      });
      const result = (await readResponsePayload<STRMutationResponse>(response)) as
        | STRMutationResponse
        | { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(result, "Unable to create supplement."));
        return;
      }
      const { report } = result as STRMutationResponse;
      setOpen(false);
      setNarrative("");
      onCreated?.();
      router.push(`/strs/${report.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create supplement.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <Button type="button" variant="outline" onClick={() => setOpen(true)}>
        Supplement this report
      </Button>
      {open ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-4 backdrop-blur"
          role="dialog"
          aria-modal="true"
          onClick={(event) => {
            if (event.target === event.currentTarget) setOpen(false);
          }}
        >
          <div className="w-full max-w-2xl space-y-4 rounded-2xl border border-border bg-card p-6 shadow-xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold">Supplement {parent.reportRef}</h2>
                <p className="text-sm text-muted-foreground">
                  Add additional information to this report — a new Additional Information File is created and linked to the parent.
                  Subject identity carries over; you can override the subject account if the supplement is about a different account on the same case.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="text-sm text-muted-foreground hover:text-primary"
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Subject account (optional override)</label>
              <Input
                value={subjectAccount}
                onChange={(event) => setSubjectAccount(event.target.value)}
                placeholder={parent.subjectAccount ?? ""}
              />
            </div>

            <div className="space-y-2">
              <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Additional narrative</label>
              <Textarea
                value={narrative}
                onChange={(event) => setNarrative(event.target.value)}
                placeholder="New facts, observations, or evidence gathered since the parent report was filed."
              />
            </div>

            {error ? <p className="text-sm text-red-300">{error}</p> : null}

            <div className="flex justify-end gap-3">
              <Button type="button" variant="ghost" onClick={() => setOpen(false)} disabled={submitting}>
                Cancel
              </Button>
              <Button type="button" onClick={() => void submit()} disabled={submitting}>
                {submitting ? "Creating…" : "Create supplement"}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
