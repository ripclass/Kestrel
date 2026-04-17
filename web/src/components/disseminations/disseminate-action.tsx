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
  linkedReportId?: string;
  linkedEntityId?: string;
  linkedCaseId?: string;
  defaultSubject?: string;
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
          className="fixed inset-0 z-50 flex items-center justify-center bg-background/85 p-4 backdrop-blur-sm"
          role="dialog"
          aria-modal="true"
          onClick={(event) => {
            if (event.target === event.currentTarget) setOpen(false);
          }}
        >
          <div className="w-full max-w-3xl border border-border bg-card">
            <div className="flex items-start justify-between gap-4 border-b border-border px-6 py-5">
              <div className="space-y-2">
                <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-accent">
                  <span aria-hidden className="mr-2">┼</span>
                  Dialog · Record dissemination
                </p>
                <h2 className="text-xl font-semibold text-foreground">Hand off intelligence</h2>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  Transmit to law enforcement, a regulator, or a foreign FIU. The dissemination reference
                  and audit log are generated automatically.
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

            <div className="grid gap-5 px-6 py-5 md:grid-cols-2">
              <Field label="Recipient agency">
                <Input
                  value={recipientAgency}
                  onChange={(event) => setRecipientAgency(event.target.value)}
                  placeholder="Bangladesh Police — CID"
                />
              </Field>
              <Field label="Recipient type">
                <select
                  className="h-11 w-full rounded-none border border-input bg-card px-4 text-sm outline-none focus:border-foreground"
                  value={recipientType}
                  onChange={(event) => setRecipientType(event.target.value as RecipientType)}
                >
                  {RECIPIENT_TYPES.map((type) => (
                    <option key={type.value} value={type.value}>
                      {type.label}
                    </option>
                  ))}
                </select>
              </Field>
              <div className="md:col-span-2">
                <Field label="Subject summary">
                  <Textarea
                    value={subjectSummary}
                    onChange={(event) => setSubjectSummary(event.target.value)}
                    placeholder="One to three sentences describing what is being disseminated and why."
                  />
                </Field>
              </div>
              <Field label="Classification">
                <select
                  className="h-11 w-full rounded-none border border-input bg-card px-4 text-sm uppercase outline-none focus:border-foreground"
                  value={classification}
                  onChange={(event) => setClassification(event.target.value as Classification)}
                >
                  {CLASSIFICATIONS.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Linked context">
                <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                  {linkedCaseId
                    ? "Linked to the current case"
                    : linkedReportId
                      ? "Linked to the current STR"
                      : linkedEntityId
                        ? "Linked to the current entity"
                        : "No linked record (standalone)"}
                </p>
              </Field>
            </div>

            {error ? (
              <p className="px-6 pb-2 font-mono text-xs uppercase tracking-[0.18em] text-destructive">
                <span aria-hidden className="mr-2">┼</span>ERROR · {error}
              </p>
            ) : null}

            <div className="flex justify-end gap-2 border-t border-border px-6 py-4">
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

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-2">
      <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
        {label}
      </span>
      {children}
    </label>
  );
}
