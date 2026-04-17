"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { IERDetail } from "@/types/domain";

function Meta({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-3 p-5">
      <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
        {label}
      </span>
      {children}
    </div>
  );
}

function Section({ label, description, children }: { label: string; description?: string; children: React.ReactNode }) {
  return (
    <section className="border border-border">
      <div className="border-b border-border px-6 py-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Section · {label}
        </p>
        {description ? (
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{description}</p>
        ) : null}
      </div>
      <div className="space-y-4 p-6">{children}</div>
    </section>
  );
}

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
      <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
        <span aria-hidden className="mr-2">┼</span>ERROR · {error}
      </p>
    );
  }
  if (!ier) {
    return (
      <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
        <span aria-hidden className="mr-2 text-accent">┼</span>Loading exchange…
      </p>
    );
  }

  const isClosed = ier.status === "confirmed" || ier.status === "dismissed";

  return (
    <div className="space-y-6">
      <section className="border border-border">
        <div className="flex flex-col gap-3 border-b border-border px-6 py-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-3">
            <p className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
              <span aria-hidden className="leading-none text-accent">┼</span>
              IER · {ier.reportRef} · {ier.direction}
            </p>
            <h2 className="font-mono text-2xl text-foreground">{ier.reportRef}</h2>
            <p className="text-sm leading-relaxed text-muted-foreground">
              {ier.counterpartyFiu}
              {ier.counterpartyCountry ? ` · ${ier.counterpartyCountry}` : ""}
            </p>
          </div>
          <Link
            href="/iers"
            className="font-mono text-[11px] uppercase tracking-[0.22em] text-accent transition hover:text-foreground"
          >
            ← Back to exchanges
          </Link>
        </div>
        <div className="grid grid-cols-2 divide-x divide-y divide-border lg:grid-cols-4 lg:divide-y-0">
          <Meta label="Direction">
            <span className="font-mono text-sm uppercase tracking-[0.18em] text-foreground">
              {ier.direction}
            </span>
          </Meta>
          <Meta label="Status">
            <span className="font-mono text-sm uppercase tracking-[0.18em] text-foreground">
              {ier.status.replaceAll("_", " ")}
            </span>
          </Meta>
          <Meta label="Egmont ref">
            <span className="font-mono text-sm text-foreground">{ier.egmontRef || "—"}</span>
          </Meta>
          <Meta label="Deadline">
            <span className="font-mono text-sm text-foreground">
              {ier.deadline ? new Date(ier.deadline).toLocaleDateString() : "—"}
            </span>
          </Meta>
        </div>
      </section>

      <Section label="Request narrative" description="Captured at open.">
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
          {ier.requestNarrative || ier.narrative || "(no narrative captured)"}
        </p>
      </Section>

      <Section
        label="Response"
        description={
          ier.responseNarrative
            ? "Captured response from the counterparty — add more or close the exchange below."
            : "Record the response once the counterparty replies."
        }
      >
        {ier.responseNarrative ? (
          <p className="whitespace-pre-wrap border border-border bg-card/50 p-4 text-sm leading-relaxed text-foreground">
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
            <div className="flex justify-end border-t border-border pt-4">
              <Button type="button" disabled={pending !== null} onClick={() => void respond()}>
                {pending === "respond" ? "Recording…" : "Record response"}
              </Button>
            </div>
          </>
        ) : null}
      </Section>

      {!isClosed ? (
        <Section
          label="Close exchange"
          description="Mark the IER as confirmed once the exchange is fully complete."
        >
          <Textarea
            value={closeNote}
            onChange={(event) => setCloseNote(event.target.value)}
            placeholder="Optional closing note — outcome, follow-ups, onwards disposition."
          />
          <div className="flex justify-end border-t border-border pt-4">
            <Button
              type="button"
              variant="outline"
              disabled={pending !== null}
              onClick={() => void close()}
            >
              {pending === "close" ? "Closing…" : "Close exchange"}
            </Button>
          </div>
        </Section>
      ) : null}

      {notice ? (
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-accent">
          <span aria-hidden className="mr-2">┼</span>
          {notice}
        </p>
      ) : null}
      {error ? (
        <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
          <span aria-hidden className="mr-2">┼</span>ERROR · {error}
        </p>
      ) : null}
    </div>
  );
}
