import type { ActivityEvent } from "@/types/domain";

export function ActivityTimeline({ events }: { events: ActivityEvent[] }) {
  return (
    <section className="border border-border">
      <div className="border-b border-border px-6 py-5">
        <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-muted-foreground">
          <span aria-hidden className="mr-2 text-accent">┼</span>
          Section · Activity timeline
        </p>
      </div>
      {events.length === 0 ? (
        <p className="px-6 py-6 font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
          No activity recorded
        </p>
      ) : (
        <ol className="divide-y divide-border">
          {events.map((event, i) => (
            <li key={event.id} className="flex items-start gap-5 px-6 py-4">
              <span className="font-mono text-[10px] tabular-nums text-muted-foreground">
                {String(i + 1).padStart(2, "0")}
              </span>
              <div className="flex-1">
                <div className="flex flex-wrap items-baseline justify-between gap-3">
                  <p className="text-sm font-semibold text-foreground">{event.title}</p>
                  <span className="font-mono text-[10px] uppercase tracking-[0.22em] text-muted-foreground">
                    {event.actor}
                  </span>
                </div>
                <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{event.description}</p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
