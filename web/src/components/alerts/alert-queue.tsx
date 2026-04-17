"use client";

import { useEffect, useState } from "react";

import { AlertCard } from "@/components/alerts/alert-card";
import { EmptyState } from "@/components/common/empty-state";
import { LoadingState } from "@/components/common/loading";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { AlertListResponse } from "@/types/api";
import type { AlertSummary } from "@/types/domain";

export function AlertQueue({ alertsToShow }: { alertsToShow?: number }) {
  const [alerts, setAlerts] = useState<AlertSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    void (async () => {
      try {
        const response = await fetch("/api/alerts", { cache: "no-store" });
        const payload = (await readResponsePayload<AlertListResponse>(response)) as
          | AlertListResponse
          | { detail?: string };
        if (!response.ok) {
          setError(detailFromPayload(payload, "Unable to load alert queue."));
          return;
        }
        setAlerts((payload as AlertListResponse).alerts);
        setError(null);
      } catch (caughtError) {
        setError(caughtError instanceof Error ? caughtError.message : "Unable to load alert queue.");
      } finally {
        setIsLoading(false);
      }
    })();
  }, []);

  if (isLoading) return <LoadingState label="Loading alert queue…" />;

  if (error) {
    return <EmptyState title="Alert queue unavailable" description={error} />;
  }

  const queue = alertsToShow ? alerts.slice(0, alertsToShow) : alerts;

  if (queue.length === 0) {
    return (
      <EmptyState
        title="No active alerts"
        description="Kestrel has not generated any live alerts for this scope yet."
      />
    );
  }

  return (
    <div className="space-y-3">
      {queue.map((alert) => (
        <AlertCard key={alert.id} alert={alert} />
      ))}
    </div>
  );
}
