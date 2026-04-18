"use client";

import { useEffect, useState } from "react";

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
      <p className="font-mono text-xs uppercase tracking-[0.18em] text-destructive">
        <span aria-hidden className="mr-2">┼</span>ERROR · {error}
      </p>
    );
  }
  if (!data) {
    return (
      <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
        <span aria-hidden className="mr-2 text-accent">┼</span>Loading schedule status…
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <section className="border border-border">
        <div className="border-b border-border px-6 py-5">
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            <span aria-hidden className="mr-2 text-accent">┼</span>
            Section · Declared schedules
          </p>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            These jobs are declared in the engine. Operators wire them into the Celery beat schedule
            when ready; until then the status is{" "}
            <span className="font-mono uppercase tracking-[0.18em] text-accent">not_configured</span>.
          </p>
        </div>
        <div className="p-6">
          {data.schedules.length === 0 ? (
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              No schedules declared
            </p>
          ) : (
            <ul className="divide-y divide-border border border-border">
              {data.schedules.map((schedule) => (
                <li key={schedule.name} className="flex flex-col gap-2 px-4 py-3 lg:flex-row lg:items-start lg:justify-between">
                  <div className="space-y-1">
                    <p className="text-sm font-semibold text-foreground">{schedule.name}</p>
                    <p className="text-sm leading-relaxed text-muted-foreground">
                      {schedule.description}
                    </p>
                    <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
                      {schedule.cron} · {schedule.task}
                    </p>
                  </div>
                  <span
                    className={`border px-3 py-1 font-mono text-[10px] uppercase tracking-[0.22em] ${
                      schedule.status === "running"
                        ? "border-accent/40 bg-accent/10 text-accent"
                        : "border-border text-muted-foreground"
                    }`}
                  >
                    {schedule.status.replaceAll("_", " ")}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <section className="border border-border">
        <div className="border-b border-border px-6 py-5">
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
            <span aria-hidden className="mr-2 text-accent">┼</span>
            Section · Active workers
          </p>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
            Celery workers currently attached to the broker.
          </p>
        </div>
        <div className="p-6">
          {data.workers.length === 0 ? (
            <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
              No live workers responded to ping · check{" "}
              <span className="text-foreground">
                celery -A app.tasks.celery_app.celery_app worker
              </span>{" "}
              on the worker service
            </p>
          ) : (
            <ul className="divide-y divide-border border border-border">
              {data.workers.map((worker) => (
                <li key={worker.hostname} className="flex items-center justify-between px-4 py-3">
                  <span className="font-mono text-sm text-foreground">{worker.hostname}</span>
                  <span
                    className={`font-mono text-[10px] uppercase tracking-[0.22em] ${
                      worker.alive ? "text-accent" : "text-muted-foreground"
                    }`}
                  >
                    {worker.alive ? "alive" : "silent"}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
        Generated {new Date(data.generatedAt).toLocaleString()}
      </p>
    </div>
  );
}
