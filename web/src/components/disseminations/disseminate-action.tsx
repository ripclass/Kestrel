"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type {
  DisseminationCreatePayload,
  DisseminationMutationResponse,
} from "@/types/api";
import type { Classification, RecipientType } from "@/types/domain";

type DisseminateActionProps = {
  /** Preset link context — carries the originating record into the new dissemination. */
  linkedReportId?: string;
  linkedEntityId?: string;
  linkedCaseId?: string;
  /** Optional pre-filled subject summary so the analyst only needs to append context. */
  defaultSubject?: string;
  /** Called after a successful dissemination — use to refresh surrounding data. */
  onCompleted?: (dissemId: string) => void;
  triggerLabel?: string;
  variant?: "default" | "secondary" | "outline" | "ghost";
};

const RECIPIENT_TYPES: { value: RecipientType; label: string }[] = [
  { value: "law_enforcement", label: "Law enforcement (Police, ACC, NBR, DGFI)" },
  { value: "regulator", label: "Regulator (Bangladesh Bank, etc.)" },
  { value: "foreign_fiu", label: "Foreign FIU (Egmont)" },
  { value: "prosecutor", label: "Prosecutor" },
  { value: "other", label: "Other" },
];

const CLASSIFICATIONS: Classification[] = [
  "public",
  "internal",
  "confidential",
  "restricted",
  "secret",
];

export function DisseminateAction({
  linkedReportId,
  linkedEntityId,
  linkedCaseId,
  defaultSubject,
  onCompleted,
  triggerLabel = "Disseminate",
  variant = "secondary",
}: DisseminateActionProps) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [recipientAgency, setRecipientAgency] = useState("");
  const [recipientType, setRecipientType] = useState<RecipientType>("law_enforcement");
  const [subjectSummary, setSubjectSummary] = useState(defaultSubject ?? "");
  const [classification, setClassification] = useState<Classification>("confidential");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setError(null);
    }
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
    setError(null);
    if (!recipientAgency.trim() || !subjectSummary.trim()) {
      setError("Recipient agency and subject summary are required.");
      return;
    }
    setSubmitting(true);
    try {
      const payload: DisseminationCreatePayload = {
        recipientAgency: recipientAgency.trim(),
        recipientType,
        subjectSummary: subjectSummary.trim(),
        classification,
        linkedReportIds: linkedReportId ? [linkedReportId] : [],
        linkedEntityIds: linkedEntityId ? [linkedEntityId] : [],
        linkedCaseIds: linkedCaseId ? [linkedCaseId] : [],
      };
      const response = await fetch("/api/disseminations", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = (await readResponsePayload<DisseminationMutationResponse>(response)) as
        | DisseminationMutationResponse
        | { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(result, "Unable to record dissemination."));
        return;
      }
      const { dissemination } = result as DisseminationMutationResponse;
      setOpen(false);
      setRecipientAgency("");
      setSubjectSummary(defaultSubject ?? "");
      onCompleted?.(dissemination.id);
      router.refresh();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Unable to record dissemination.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <Button type="button" variant={variant} onClick={() => setOpen(true)}>
        {triggerLabel}
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
                <h2 className="text-xl font-semibold">Record a dissemination</h2>
                <p className="text-sm text-muted-foreground">
                  Hand off to law enforcement, a regulator, or a foreign FIU. The dissemination ref and audit log are generated automatically.
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

            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Recipient agency</label>
                <Input
                  value={recipientAgency}
                  onChange={(event) => setRecipientAgency(event.target.value)}
                  placeholder="Bangladesh Police — CID"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Recipient type</label>
                <select
                  className="h-11 w-full rounded-xl border border-input bg-background/60 px-4 text-sm outline-none focus:border-primary"
                  value={recipientType}
                  onChange={(event) => setRecipientType(event.target.value as RecipientType)}
                >
                  {RECIPIENT_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2 md:col-span-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Subject summary</label>
                <Textarea
                  value={subjectSummary}
                  onChange={(event) => setSubjectSummary(event.target.value)}
                  placeholder="One to three sentences describing what is being disseminated and why."
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Classification</label>
                <select
                  className="h-11 w-full rounded-xl border border-input bg-background/60 px-4 text-sm outline-none focus:border-primary"
                  value={classification}
                  onChange={(event) => setClassification(event.target.value as Classification)}
                >
                  {CLASSIFICATIONS.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Linked context</label>
                <p className="text-sm text-muted-foreground">
                  {linkedCaseId
                    ? "Linked to the current case."
                    : linkedReportId
                      ? "Linked to the current STR."
                      : linkedEntityId
                        ? "Linked to the current entity."
                        : "No linked record (standalone)."}
                </p>
              </div>
            </div>

            {error ? <p className="text-sm text-red-300">{error}</p> : null}

            <div className="flex justify-end gap-3">
              <Button type="button" variant="ghost" onClick={() => setOpen(false)} disabled={submitting}>
                Cancel
              </Button>
              <Button type="button" onClick={() => void submit()} disabled={submitting}>
                {submitting ? "Recording…" : "Record dissemination"}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}
