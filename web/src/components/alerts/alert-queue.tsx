import { alerts } from "@/lib/demo";
import { AlertCard } from "@/components/alerts/alert-card";

export function AlertQueue({ alertsToShow }: { alertsToShow?: number }) {
  const queue = alertsToShow ? alerts.slice(0, alertsToShow) : alerts;

  return (
    <div className="space-y-4">
      {queue.map((alert) => (
        <AlertCard key={alert.id} alert={alert} />
      ))}
    </div>
  );
}
