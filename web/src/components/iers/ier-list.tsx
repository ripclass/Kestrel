"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { IERDirection, IERSummary } from "@/types/domain";

type Tab = "all" | IERDirection;

const directionTone: Record<IERDirection, string> = {
  outbound: "border-foreground/30 text-foreground",
  inbound: "border-accent/40 text-accent",
};

export function IERList() {
  const [records, setRecords] = useState<IERSummary[]>([]);
  const [tab, setTab] = useState<Tab>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const url = tab === "all" ? "/api/iers" : `/api/iers?direction=${tab}`;
      const response = await fetch(url, { cache: "no-store" });
      const payload = (await readResponsePayload<{ iers: IERSummary[] }>(response)) as
        | { iers: IERSummary[] }
        | { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(payload, "Unable to load exchanges."));
        return;
      }
      setRecords((payload as { iers: IERSummary[] }).iers);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load exchanges.");
    } finally {
      setLoading(false);
    }
  }, [tab]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <section className="border border-border">
      <div className="flex flex-col gap-3 border-b border-border px-6 py-5 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            <span aria-hidden className="mr-2 text-accent">┼</span>
            Section · Exchange ledger
          </p>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Every outbound request and inbound handoff is tracked as an IER. Use the tabs to focus on
            one direction.
          </p>
        </div>
        <Link
          href="/iers/new"
          className="inline-flex items-center justify-center bg-foreground px-5 py-2 font-mono text-[11px] uppercase tracking-[0.22em] text-background transition hover:opacity-90"
        >
          Open a new exchange
        </Link>
      </div>
      <div className="space-y-4 p-6">
        <div className="flex flex-wrap gap-0 border border-border">
          {(["all", "outbound", "inbound"] as Tab[]).map((value) => (
            <button
              key={value}
              type="button"
              onClick={() => setTab(value)}
              className={`border-r border-border px-5 py-2 font-mono text-[11px] uppercase tracking-[0.22em] transition last:border-r-0 ${
                tab === value
                  ? "bg-foreground text-background"
                  : "text-muted-foreground hover:bg-foreground/[0.04] hover:text-foreground"
              }`}
            >
              {value === "all" ? "All" : value === "outbound" ? "Outbound" : "Inbound"}
            </button>
          ))}
        </div>
        {error ? (
          <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
            <span aria-hidden className="mr-2">┼</span>ERROR · {error}
          </p>
        ) : null}
        {loading ? (
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
            Loading exchanges…
          </p>
        ) : records.length === 0 ? (
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
            No exchanges recorded yet for this tab
          </p>
        ) : (
          <div className="space-y-3">
            {records.map((record) => (
              <Link
                key={record.id}
                href={`/iers/${record.id}`}
                className="block border border-border bg-card px-5 py-4 transition hover:bg-foreground/[0.03]"
              >
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-3">
                      <p className="font-mono text-sm text-foreground">{record.reportRef}</p>
                      <span
                        className={`inline-flex items-center border px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.22em] ${directionTone[record.direction]}`}
                      >
                        {record.direction}
                      </span>
                      <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                        {record.status.replaceAll("_", " ")}
                      </span>
                      {record.hasResponse ? (
                        <span className="border border-accent/40 bg-accent/10 px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.22em] text-accent">
                          response logged
                        </span>
                      ) : null}
                    </div>
                    <p className="text-sm text-foreground">
                      {record.counterpartyFiu}
                      {record.counterpartyCountry ? ` · ${record.counterpartyCountry}` : ""}
                    </p>
                    {record.egmontRef ? (
                      <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                        {record.egmontRef}
                      </p>
                    ) : null}
                  </div>
                  <div className="space-y-1 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                    {record.deadline ? (
                      <p>
                        Deadline ·{" "}
                        <span className="text-foreground">
                          {new Date(record.deadline).toLocaleDateString()}
                        </span>
                      </p>
                    ) : null}
                    <p>
                      Opened ·{" "}
                      <span className="text-foreground">
                        {new Date(record.createdAt).toLocaleString()}
                      </span>
                    </p>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
