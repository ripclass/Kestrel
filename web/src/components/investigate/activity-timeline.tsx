import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ActivityEvent } from "@/types/domain";

export function ActivityTimeline({ events }: { events: ActivityEvent[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Activity timeline</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {events.map((event) => (
          <div key={event.id} className="rounded-xl border border-border/70 bg-background/50 p-4">
            <div className="flex items-center justify-between gap-4">
              <p className="font-medium">{event.title}</p>
              <span className="text-xs uppercase tracking-[0.2em] text-muted-foreground">{event.actor}</span>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">{event.description}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
