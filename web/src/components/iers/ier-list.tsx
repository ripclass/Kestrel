"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { IERDirection, IERSummary } from "@/types/domain";

type Tab = "all" | IERDirection;

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
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <CardTitle>Exchange ledger</CardTitle>
              <CardDescription>
                Every outbound request and inbound handoff is tracked as an IER. Use the tabs to focus on one direction.
              </CardDescription>
            </div>
            <Link
              href="/iers/new"
              className="inline-flex items-center justify-center rounded-xl border border-primary bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:bg-primary/90"
            >
              Open a new exchange
            </Link>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {(["all", "outbound", "inbound"] as Tab[]).map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setTab(value)}
                className={`rounded-full border px-3 py-1 text-xs font-medium transition ${
                  tab === value
                    ? "border-primary bg-primary/15 text-primary"
                    : "border-border text-muted-foreground hover:border-primary/40"
                }`}
              >
                {value === "all" ? "All" : value === "outbound" ? "Outbound" : "Inbound"}
              </button>
            ))}
          </div>
          {error ? <p className="text-sm text-red-300">{error}</p> : null}
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading exchanges…</p>
          ) : records.length === 0 ? (
            <p className="text-sm text-muted-foreground">No exchanges recorded yet for this tab.</p>
          ) : (
            records.map((record) => (
              <Link
                key={record.id}
                href={`/iers/${record.id}`}
                className="block rounded-2xl border border-border/80 bg-background/50 p-4 transition hover:border-primary/60 hover:bg-background/70"
              >
                <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-3">
                      <p className="font-semibold">{record.reportRef}</p>
                      <span
                        className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest ${
                          record.direction === "outbound"
                            ? "border-cyan-500/40 bg-cyan-500/10 text-cyan-300"
                            : "border-amber-500/40 bg-amber-500/10 text-amber-300"
                        }`}
                      >
                        {record.direction}
                      </span>
                      <span className="text-xs uppercase tracking-widest text-muted-foreground">
                        {record.status.replaceAll("_", " ")}
                      </span>
                      {record.hasResponse ? (
                        <span className="inline-flex items-center rounded-full border border-primary/40 bg-primary/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-widest text-primary">
                          response logged
                        </span>
                      ) : null}
                    </div>
                    <p className="text-sm">{record.counterpartyFiu}{record.counterpartyCountry ? ` · ${record.counterpartyCountry}` : ""}</p>
                    {record.egmontRef ? (
                      <p className="text-xs text-muted-foreground font-mono">{record.egmontRef}</p>
                    ) : null}
                  </div>
                  <div className="space-y-1 text-sm text-muted-foreground">
                    {record.deadline ? <p>Deadline: {new Date(record.deadline).toLocaleDateString()}</p> : null}
                    <p>Opened: {new Date(record.createdAt).toLocaleString()}</p>
                  </div>
                </div>
              </Link>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
