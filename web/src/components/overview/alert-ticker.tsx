"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { AlertListResponse } from "@/types/api";
import type { AlertSummary } from "@/types/domain";

const severityTone: Record<string, string> = {
  critical: "text-accent",
  high: "text-accent",
  medium: "text-foreground",
  low: "text-muted-foreground",
};

export function AlertTicker() {
  const [alerts, setAlerts] = useState<AlertSummary[]>([]);
  const [fallbackMessage, setFallbackMessage] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      const response = await fetch("/api/alerts", { cache: "no-store" });
      const payload = (await readResponsePayload<AlertListResponse>(response)) as
        | AlertListResponse
        | { detail?: string };
      if (!response.ok) {
        setFallbackMessage(detailFromPayload(payload, "Alert wire offline."));
        return;
      }
      setAlerts((payload as AlertListResponse).alerts.slice(0, 5));
    })();
  }, []);

  return (
    <div className="flex items-center gap-0 overflow-x-auto border border-border bg-card">
      <span className="flex items-center gap-2 whitespace-nowrap border-r border-border px-4 py-3 font-mono text-[10px] uppercase tracking-[0.28em] text-accent">
        <span aria-hidden className="leading-none">┼</span>
        Live wire · Alerts
      </span>
      {fallbackMessage ? (
        <span className="whitespace-nowrap px-4 py-3 font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">
          {fallbackMessage}
        </span>
      ) : alerts.length === 0 ? (
        <span className="whitespace-nowrap px-4 py-3 font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground">
          No alerts on the wire
        </span>
      ) : (
        alerts.map((alert) => (
          <Link
            key={alert.id}
            href={`/alerts/${alert.id}`}
            className="flex min-w-max items-center gap-3 border-r border-border px-4 py-3 text-sm last:border-r-0 hover:bg-foreground/[0.03]"
          >
            <span
              className={`font-mono text-[10px] uppercase tracking-[0.22em] ${severityTone[alert.severity] ?? "text-muted-foreground"}`}
            >
              {alert.severity}
            </span>
            <span className="text-foreground">{alert.title}</span>
          </Link>
        ))
      )}
    </div>
  );
}
