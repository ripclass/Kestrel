"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { IERDetail, IERDirection } from "@/types/domain";

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

export function IERCreateForm() {
  const router = useRouter();
  const [direction, setDirection] = useState<IERDirection>("outbound");
  const [counterpartyFiu, setCounterpartyFiu] = useState("");
  const [counterpartyCountry, setCounterpartyCountry] = useState("");
  const [egmontRef, setEgmontRef] = useState("");
  const [requestNarrative, setRequestNarrative] = useState("");
  const [deadline, setDeadline] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setError(null);
    if (!counterpartyFiu.trim() || !requestNarrative.trim()) {
      setError("Counterparty FIU and request narrative are required.");
      return;
    }
    if (direction === "inbound" && !egmontRef.trim()) {
      setError("Inbound exchanges require an Egmont reference.");
      return;
    }
    setSubmitting(true);
    try {
      const payload = {
        counterpartyFiu: counterpartyFiu.trim(),
        counterpartyCountry: counterpartyCountry.trim() || null,
        egmontRef: egmontRef.trim() || null,
        requestNarrative: requestNarrative.trim(),
        deadline: deadline || null,
        linkedEntityIds: [],
      };
      const response = await fetch(`/api/iers/${direction}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = (await readResponsePayload<{ ier: IERDetail }>(response)) as
        | { ier: IERDetail }
        | { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(result, "Unable to open exchange."));
        return;
      }
      const { ier } = result as { ier: IERDetail };
      router.push(`/iers/${ier.id}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="border border-border">
      <div className="border-b border-border px-6 py-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Section · Open exchange
        </p>
        <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
          Choose direction, identify the counterparty FIU, and describe what is being exchanged. Kestrel
          records this as an IER report with its own ref and audit trail.
        </p>
      </div>
      <div className="space-y-5 p-6">
        <div className="flex flex-wrap gap-0 border border-border">
          {(["outbound", "inbound"] as IERDirection[]).map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setDirection(value)}
              className={`border-r border-border px-5 py-2 font-mono text-[11px] uppercase tracking-[0.22em] transition last:border-r-0 ${
                direction === value
                  ? "bg-foreground text-background"
                  : "text-muted-foreground hover:bg-foreground/[0.04] hover:text-foreground"
              }`}
            >
              {value === "outbound" ? "Outbound · BFIU requesting" : "Inbound · Foreign FIU requesting"}
            </button>
          ))}
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Field label="Counterparty FIU">
            <Input
              value={counterpartyFiu}
              onChange={(event) => setCounterpartyFiu(event.target.value)}
              placeholder="FINTRAC (Canada)"
            />
          </Field>
          <Field label="Counterparty country">
            <Input
              value={counterpartyCountry}
              onChange={(event) => setCounterpartyCountry(event.target.value)}
              placeholder="Canada"
            />
          </Field>
          <Field label={`Egmont reference${direction === "inbound" ? " (required)" : ""}`}>
            <Input
              value={egmontRef}
              onChange={(event) => setEgmontRef(event.target.value)}
              placeholder="EG-2026-0419"
            />
          </Field>
          <Field label="Response deadline">
            <Input type="date" value={deadline} onChange={(event) => setDeadline(event.target.value)} />
          </Field>
        </div>
        <Field label="Request narrative">
          <Textarea
            value={requestNarrative}
            onChange={(event) => setRequestNarrative(event.target.value)}
            placeholder="What information is being requested and why."
          />
        </Field>
        {error ? (
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
            <span aria-hidden className="mr-2">┼</span>ERROR · {error}
          </p>
        ) : null}
        <div className="flex justify-end border-t border-border pt-4">
          <Button type="button" disabled={submitting} onClick={() => void submit()}>
            {submitting ? "Opening…" : "Open exchange"}
          </Button>
        </div>
      </div>
    </section>
  );
}
