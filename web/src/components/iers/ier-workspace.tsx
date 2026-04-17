"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { IERDetail } from "@/types/domain";

export function IERWorkspace({ ierId }: { ierId: string }) {
  const [ier, setIer] = useState<IERDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [responseNarrative, setResponseNarrative] = useState("");
  const [closeNote, setCloseNote] = useState("");
  const [pending, setPending] = useState<string | null>(null);

  async function load() {
    try {
      const response = await fetch(`/api/iers/${ierId}`, { cache: "no-store" });
      const payload = (await readResponsePayload<IERDetail>(response)) as
        | IERDetail
        | { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(payload, "Unable to load IER."));
        return;
      }
      setIer(payload as IERDetail);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load IER.");
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ierId]);

  async function respond() {
    if (!responseNarrative.trim()) {
      setError("Response narrative is required.");
      return;
    }
    setPending("respond");
    setError(null);
    try {
      const response = await fetch(`/api/iers/${ierId}/respond`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ responseNarrative }),
      });
      const payload = (await readResponsePayload<{ ier: IERDetail }>(response)) as
        | { ier: IERDetail }
        | { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(payload, "Unable to record response."));
        return;
      }
      setIer((payload as { ier: IERDetail }).ier);
      setResponseNarrative("");
      setNotice("Response recorded.");
    } finally {
      setPending(null);
    }
  }

  async function close() {
    setPending("close");
    setError(null);
    try {
      const response = await fetch(`/api/iers/${ierId}/close`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ note: closeNote || null }),
      });
      const payload = (await readResponsePayload<{ ier: IERDetail }>(response)) as
        | { ier: IERDetail }
        | { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(payload, "Unable to close IER."));
        return;
      }
      setIer((payload as { ier: IERDetail }).ier);
      setCloseNote("");
      setNotice("Exchange closed.");
    } finally {
      setPending(null);
    }
  }

  if (error && !ier) {
    return (
      <Card>
        <CardContent className="py-10 text-sm text-red-300">{error}</CardContent>
      </Card>
    );
  }
  if (!ier) {
    return (
      <Card>
        <CardContent className="py-10 text-sm text-muted-foreground">Loading exchange…</CardContent>
      </Card>
    );
  }

  const isClosed = ier.status === "confirmed" || ier.status === "dismissed";

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <CardTitle>{ier.reportRef}</CardTitle>
              <CardDescription>
                {ier.counterpartyFiu}
                {ier.counterpartyCountry ? ` · ${ier.counterpartyCountry}` : ""} · {ier.direction}
              </CardDescription>
            </div>
            <Link href="/iers" className="text-sm text-muted-foreground hover:text-primary">
              ← Back to exchanges
            </Link>
          </div>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Direction</p>
            <p className="mt-1 text-sm font-medium">{ier.direction}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Status</p>
            <p className="mt-1 text-sm font-medium">{ier.status.replaceAll("_", " ")}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Egmont ref</p>
            <p className="mt-1 text-sm font-medium">{ier.egmontRef || "—"}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground">Deadline</p>
            <p className="mt-1 text-sm font-medium">
              {ier.deadline ? new Date(ier.deadline).toLocaleDateString() : "—"}
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Request narrative</CardTitle>
          <CardDescription>Captured at open.</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="whitespace-pre-wrap text-sm">{ier.requestNarrative || ier.narrative || "(no narrative captured)"}</p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Response</CardTitle>
          <CardDescription>
            {ier.responseNarrative
              ? "Captured response from the counterparty — add more or close the exchange below."
              : "Record the response once the counterparty replies."}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {ier.responseNarrative ? (
            <p className="whitespace-pre-wrap rounded-xl border border-border/70 bg-background/60 p-3 text-sm">
              {ier.responseNarrative}
            </p>
          ) : null}
          {!isClosed ? (
            <>
              <Textarea
                value={responseNarrative}
                onChange={(event) => setResponseNarrative(event.target.value)}
                placeholder="Summary of the counterparty's response, relevant identifiers, any attachments you received."
              />
              <div className="flex justify-end">
                <Button type="button" disabled={pending !== null} onClick={() => void respond()}>
                  {pending === "respond" ? "Recording…" : "Record response"}
                </Button>
              </div>
            </>
          ) : null}
        </CardContent>
      </Card>

      {!isClosed ? (
        <Card>
          <CardHeader>
            <CardTitle>Close exchange</CardTitle>
            <CardDescription>Mark the IER as confirmed once the exchange is fully complete.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Textarea
              value={closeNote}
              onChange={(event) => setCloseNote(event.target.value)}
              placeholder="Optional closing note — outcome, follow-ups, onwards disposition."
            />
            <div className="flex justify-end">
              <Button type="button" variant="outline" disabled={pending !== null} onClick={() => void close()}>
                {pending === "close" ? "Closing…" : "Close exchange"}
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      {notice ? <p className="text-sm text-primary/80">{notice}</p> : null}
      {error ? <p className="text-sm text-red-300">{error}</p> : null}
    </div>
  );
}
