import { alerts } from "@/lib/demo";

export function AlertTicker() {
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
