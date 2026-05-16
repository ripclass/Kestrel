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
import type {
  Classification,
  MlpaSection,
  RecipientAuthority,
  RecipientType,
} from "@/types/domain";

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

// Named Bangladesh recipient authority under MLPA 2012 §23 + §24 + BFIU
// Circular 22. Each row also carries the sensible default for recipient_type
// and the typical MLPA enabling clause used by BFIU for that authority.
const RECIPIENT_AUTHORITIES: {
  value: RecipientAuthority;
  label: string;
  defaultType: RecipientType;
  defaultSection: MlpaSection;
}[] = [
  { value: "bangladesh_police_cid", label: "Bangladesh Police — CID", defaultType: "law_enforcement", defaultSection: "mlpa_24_3" },
  { value: "anti_corruption_commission", label: "Anti-Corruption Commission (ACC)", defaultType: "law_enforcement", defaultSection: "mlpa_24_3" },
  { value: "national_board_of_revenue", label: "National Board of Revenue (NBR) — Tax + Customs", defaultType: "regulator", defaultSection: "mlpa_24_3" },
  { value: "dept_narcotics_control", label: "Department of Narcotics Control (DNC)", defaultType: "law_enforcement", defaultSection: "mlpa_24_3" },
  { value: "bangladesh_securities_exchange_commission", label: "Bangladesh Securities & Exchange Commission (BSEC)", defaultType: "regulator", defaultSection: "mlpa_24_3" },
  { value: "insurance_dev_regulatory_authority", label: "Insurance Development & Regulatory Authority (IDRA)", defaultType: "regulator", defaultSection: "mlpa_24_3" },
  { value: "microcredit_regulatory_authority", label: "Microcredit Regulatory Authority (MRA)", defaultType: "regulator", defaultSection: "mlpa_24_3" },
  { value: "dgfi", label: "Directorate General of Forces Intelligence (DGFI)", defaultType: "law_enforcement", defaultSection: "mlpa_24_3" },
  { value: "nsi", label: "National Security Intelligence (NSI)", defaultType: "law_enforcement", defaultSection: "mlpa_24_3" },
  { value: "court_or_investigating_officer", label: "Court / MLPA §12 Investigating Officer", defaultType: "prosecutor", defaultSection: "mlpa_23_1_a" },
  { value: "foreign_fiu_egmont", label: "Foreign FIU (Egmont Group)", defaultType: "foreign_fiu", defaultSection: "mlpa_24_4" },
  { value: "bb_internal_dept", label: "Bangladesh Bank — Internal Department", defaultType: "regulator", defaultSection: "mlpa_23_1_d" },
  { value: "peer_reporting_org_circular_22", label: "Peer Reporting Org (bank-to-bank, Circular 22)", defaultType: "other", defaultSection: "mlpa_23_1_d" },
];

const MLPA_SECTIONS: { value: MlpaSection; label: string }[] = [
  { value: "mlpa_23_1_a", label: "MLPA §23(1)(a) — analyse + provide to LEA" },
  { value: "mlpa_23_1_b", label: "MLPA §23(1)(b) — demand info / report" },
  { value: "mlpa_23_1_c", label: "MLPA §23(1)(c) — suspend / freeze (30d, extendable)" },
  { value: "mlpa_23_1_d", label: "MLPA §23(1)(d) — issue directions (incl. Circular 22 + 24)" },
  { value: "mlpa_23_1_e", label: "MLPA §23(1)(e) — monitor + on-site inspection" },
  { value: "mlpa_23_1_f", label: "MLPA §23(1)(f) — training / capacity-building" },
  { value: "mlpa_23_1_g", label: "MLPA §23(1)(g) — other functions" },
  { value: "mlpa_24_3", label: "MLPA §24(3) — spontaneous dissemination to LEA" },
  { value: "mlpa_24_4", label: "MLPA §24(4) — cross-border via agreement (Egmont)" },
  { value: "ata_15_1_a", label: "ATA §15(1)(a) — TF analyse + provide to LEA" },
  { value: "ata_15_1_b", label: "ATA §15(1)(b) — TF demand info" },
  { value: "ata_15_1_c", label: "ATA §15(1)(c) — TF suspend / freeze" },
  { value: "ata_15_1_d", label: "ATA §15(1)(d) — TF directions" },
  { value: "ata_15_1_e", label: "ATA §15(1)(e) — TF monitor" },
  { value: "ata_15_1_f", label: "ATA §15(1)(f) — TF training" },
  { value: "ata_15_1_g", label: "ATA §15(1)(g) — TF other" },
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
  const [recipientAuthority, setRecipientAuthority] = useState<RecipientAuthority | "">("");
  const [mlpaSection, setMlpaSection] = useState<MlpaSection | "">("");
  const [circular22Exchange, setCircular22Exchange] = useState(false);
  const [subjectSummary, setSubjectSummary] = useState(defaultSubject ?? "");
  const [classification, setClassification] = useState<Classification>("confidential");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // When the user picks a typed authority, auto-populate the related fields to
  // sensible defaults. They can still override before submitting. This is the
  // affordance that makes BFIU-aligned dissemination one click instead of three.
  function selectAuthority(value: RecipientAuthority | "") {
    setRecipientAuthority(value);
    if (!value) return;
    const meta = RECIPIENT_AUTHORITIES.find((row) => row.value === value);
    if (!meta) return;
    setRecipientType(meta.defaultType);
    setMlpaSection(meta.defaultSection);
    setCircular22Exchange(value === "peer_reporting_org_circular_22");
  }

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
        recipientAuthority: recipientAuthority || null,
        mlpaSection: mlpaSection || null,
        circular22Exchange,
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
      setRecipientAuthority("");
      setMlpaSection("");
      setCircular22Exchange(false);
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
                <Field label="Recipient authority (MLPA §23 + §24 + Circular 22)">
                  <select
                    className="h-11 w-full rounded-none border border-input bg-card px-4 text-sm outline-none focus:border-foreground"
                    value={recipientAuthority}
                    onChange={(event) => selectAuthority(event.target.value as RecipientAuthority | "")}
                  >
                    <option value="">— Select the named Bangladesh authority —</option>
                    {RECIPIENT_AUTHORITIES.map((row) => (
                      <option key={row.value} value={row.value}>
                        {row.label}
                      </option>
                    ))}
                  </select>
                </Field>
              </div>
              <Field label="Enabling clause">
                <select
                  className="h-11 w-full rounded-none border border-input bg-card px-4 text-sm outline-none focus:border-foreground"
                  value={mlpaSection}
                  onChange={(event) => setMlpaSection(event.target.value as MlpaSection | "")}
                >
                  <option value="">— Optional, pre-filled from authority —</option>
                  {MLPA_SECTIONS.map((row) => (
                    <option key={row.value} value={row.value}>
                      {row.label}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Circular 22 bank-to-bank exchange">
                <label className="flex h-11 items-center gap-3 border border-input bg-card px-4">
                  <input
                    type="checkbox"
                    checked={circular22Exchange}
                    onChange={(event) => setCircular22Exchange(event.target.checked)}
                  />
                  <span className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                    {circular22Exchange ? "Circular 22 exchange · §23(1)(d)" : "Not a Circular 22 exchange"}
                  </span>
                </label>
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
