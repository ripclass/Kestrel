"use client";

import { useEffect, useState } from "react";

import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { AlertListResponse } from "@/types/api";
import type { AlertSummary } from "@/types/domain";

export function AlertTicker() {
  const [alerts, setAlerts] = useState<AlertSummary[]>([]);

  useEffect(() => {
    void (async () => {
      const response = await fetch("/api/alerts", { cache: "no-store" });
      const payload = (await readResponsePayload<AlertListResponse>(response)) as AlertListResponse | { detail?: string };
      if (!response.ok) {
        setAlerts([
          {
            id: "fallback",
            title: detailFromPayload(payload, "Unable to load alert ticker."),
            description: "",
            alertType: "system",
            riskScore: 0,
            severity: "low",
            status: "open",
            createdAt: new Date().toISOString(),
            orgName: "Kestrel",
            entityId: "",
            reasons: [],
          },
        ]);
        return;
      }
      setAlerts((payload as AlertListResponse).alerts.slice(0, 5));
    })();
  }, []);

  return (
    <div className="flex gap-4 overflow-x-auto rounded-2xl border border-border/80 bg-card/80 px-4 py-3 text-sm">
      {alerts.map((alert) => (
        <div key={alert.id} className="min-w-max">
          <span className="font-medium text-primary">{alert.severity.toUpperCase()}</span>
          <span className="mx-2 text-muted-foreground">/</span>
          <span>{alert.title}</span>
        </div>
      ))}
    </div>
  );
}
