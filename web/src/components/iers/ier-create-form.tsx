"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { IERDetail, IERDirection } from "@/types/domain";

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
    <Card>
      <CardHeader>
        <CardTitle>Open exchange</CardTitle>
        <CardDescription>
          Choose direction, identify the counterparty FIU, and describe what is being exchanged. Kestrel records this as an IER
          report with its own ref and audit trail.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          {(["outbound", "inbound"] as IERDirection[]).map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setDirection(value)}
              className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
                direction === value
                  ? "border-primary bg-primary/15 text-primary"
                  : "border-border text-muted-foreground hover:border-primary/40"
              }`}
            >
              {value === "outbound" ? "Outbound (BFIU requesting)" : "Inbound (foreign FIU requesting)"}
            </button>
          ))}
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="space-y-2">
            <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Counterparty FIU</label>
            <Input
              value={counterpartyFiu}
              onChange={(event) => setCounterpartyFiu(event.target.value)}
              placeholder="FINTRAC (Canada)"
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Counterparty country</label>
            <Input
              value={counterpartyCountry}
              onChange={(event) => setCounterpartyCountry(event.target.value)}
              placeholder="Canada"
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">
              Egmont reference{direction === "inbound" ? " (required)" : ""}
            </label>
            <Input
              value={egmontRef}
              onChange={(event) => setEgmontRef(event.target.value)}
              placeholder="EG-2026-0419"
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Response deadline</label>
            <Input type="date" value={deadline} onChange={(event) => setDeadline(event.target.value)} />
          </div>
        </div>
        <div className="space-y-2">
          <label className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Request narrative</label>
          <Textarea
            value={requestNarrative}
            onChange={(event) => setRequestNarrative(event.target.value)}
            placeholder="What information is being requested and why."
          />
        </div>
        {error ? <p className="text-sm text-red-300">{error}</p> : null}
        <div className="flex justify-end">
          <Button type="button" disabled={submitting} onClick={() => void submit()}>
            {submitting ? "Opening…" : "Open exchange"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
