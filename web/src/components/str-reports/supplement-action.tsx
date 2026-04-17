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
          className="fixed inset-0 z-50 flex items-center justify-center bg-background/85 p-4 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          onClick={(event) => {
            if (event.target === event.currentTarget) setOpen(false);
          }}
        >
          <div className="w-full max-w-2xl border border-border bg-card">
            <div className="flex items-start justify-between gap-4 border-b border-border px-6 py-5">
              <div className="space-y-2">
                <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-accent">
                  <span aria-hidden className="mr-2">┼</span>
                  Dialog · Additional Information File
                </p>
                <h2 className="text-xl font-semibold text-foreground">Supplement {parent.reportRef}</h2>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  Add additional information to this report — a new Additional Information File is created
                  and linked to the parent. Subject identity carries over; override the subject account if
                  the supplement concerns a different account on the same case.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setOpen(false)}
                className="font-mono text-sm text-muted-foreground transition hover:text-accent"
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            <div className="space-y-5 px-6 py-5">
              <div className="space-y-2">
                <label className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
                  Subject account (optional override)
                </label>
                <Input
                  value={subjectAccount}
                  onChange={(event) => setSubjectAccount(event.target.value)}
                  placeholder={parent.subjectAccount ?? ""}
                />
              </div>

              <div className="space-y-2">
                <label className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
                  Additional narrative
                </label>
                <Textarea
                  value={narrative}
                  onChange={(event) => setNarrative(event.target.value)}
                  placeholder="New facts, observations, or evidence gathered since the parent report was filed."
                />
              </div>

              {error ? (
                <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
                  <span aria-hidden className="mr-2">┼</span>ERROR · {error}
                </p>
              ) : null}
            </div>

            <div className="flex justify-end gap-2 border-t border-border px-6 py-4">
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
