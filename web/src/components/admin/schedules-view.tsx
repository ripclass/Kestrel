"use client";

import { useEffect, useState } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { detailFromPayload, readResponsePayload } from "@/lib/http";
import type { ScheduleList } from "@/types/domain";

export function SchedulesView() {
  const [data, setData] = useState<ScheduleList | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      const response = await fetch("/api/admin/schedules", { cache: "no-store" });
      const payload = (await readResponsePayload<ScheduleList>(response)) as
        | ScheduleList
        | { detail?: string };
      if (!response.ok) {
        setError(detailFromPayload(payload, "Unable to load schedules."));
        return;
      }
      setData(payload as ScheduleList);
    })();
  }, []);

  if (error) {
    return (
      <Card>
        <CardContent className="py-10 text-sm text-red-300">{error}</CardContent>
      </Card>
    );
  }
  if (!data) {
    return (
      <Card>
        <CardContent className="py-10 text-sm text-muted-foreground">Loading schedule status…</CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Declared schedules</CardTitle>
          <CardDescription>
            These jobs are declared in the engine. Operators wire them into the Celery beat schedule when ready;
            until then the status is <span className="font-semibold">not_configured</span>.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {data.schedules.length === 0 ? (
            <p className="text-sm text-muted-foreground">No schedules declared.</p>
          ) : (
            data.schedules.map((schedule) => (
              <div key={schedule.name} className="rounded-2xl border border-border/80 bg-background/60 p-4">
                <div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
                  <div className="space-y-1">
                    <p className="font-medium">{schedule.name}</p>
                    <p className="text-sm text-muted-foreground">{schedule.description}</p>
                    <p className="text-xs font-mono text-muted-foreground">
                      {schedule.cron} · {schedule.task}
                    </p>
                  </div>
                  <span
                    className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-widest ${
                      schedule.status === "running"
                        ? "border-primary/40 bg-primary/10 text-primary"
                        : "border-border text-muted-foreground"
                    }`}
                  >
                    {schedule.status.replaceAll("_", " ")}
                  </span>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Active workers</CardTitle>
          <CardDescription>Celery workers currently attached to the broker.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {data.workers.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No live workers responded to ping. Check `celery -A app.tasks.celery_app.celery_app worker` on the worker service.
            </p>
          ) : (
            data.workers.map((worker) => (
              <div key={worker.hostname} className="rounded-xl border border-border/70 bg-background/60 p-3">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm">{worker.hostname}</span>
                  <span
                    className={`text-xs uppercase tracking-widest ${
                      worker.alive ? "text-primary" : "text-muted-foreground"
                    }`}
                  >
                    {worker.alive ? "alive" : "silent"}
                  </span>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground">
        Generated {new Date(data.generatedAt).toLocaleString()}
      </p>
    </div>
  );
}
