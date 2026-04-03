import { Badge } from "@/components/ui/badge";
import type { DeploymentReadiness } from "@/types/domain";

function statusTone(status: string) {
  switch (status) {
    case "ok":
    case "ready":
      return "border-emerald-400/30 bg-emerald-500/15 text-emerald-100";
    case "missing_config":
    case "pending":
      return "border-amber-400/30 bg-amber-500/15 text-amber-100";
    default:
      return "border-rose-400/30 bg-rose-500/15 text-rose-100";
  }
}

export function DeploymentReadinessPanel({
  readiness,
  compact = false,
}: {
  readiness: DeploymentReadiness | null;
  compact?: boolean;
}) {
  if (!readiness) {
    return (
      <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6 text-sm text-slate-300 backdrop-blur">
        Live readiness telemetry is unavailable from the engine right now.
      </div>
    );
  }

  const requiredChecks = readiness.checks.filter((check) => check.required);
  const healthyRequiredChecks = requiredChecks.filter((check) => check.status === "ok");

  return (
    <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6 text-slate-100 backdrop-blur">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-2">
          <p className="text-xs uppercase tracking-[0.26em] text-primary">Deployment posture</p>
          <h2 className="text-2xl font-semibold">
            {readiness.status === "ready" ? "Production stack is responding." : "Production stack needs attention."}
          </h2>
          <p className="max-w-2xl text-sm text-slate-300">
            Environment <span className="font-medium text-white">{readiness.environment}</span>, engine version{" "}
            <span className="font-medium text-white">{readiness.version}</span>, required services healthy{" "}
            <span className="font-medium text-white">
              {healthyRequiredChecks.length}/{requiredChecks.length}
            </span>
            .
          </p>
        </div>
        <Badge className={statusTone(readiness.status)}>
          {readiness.status === "ready" ? "Ready" : "Needs review"}
        </Badge>
      </div>
      <div className={`mt-6 grid gap-3 ${compact ? "md:grid-cols-2" : "xl:grid-cols-3"}`}>
        {readiness.checks.map((check) => (
          <div key={check.name} className="rounded-2xl border border-white/10 bg-slate-950/35 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-white">{check.name}</p>
                <p className="mt-1 text-xs text-slate-400">{check.required ? "Required service" : "Optional signal"}</p>
              </div>
              <Badge className={statusTone(check.status)}>{check.status.replace("_", " ")}</Badge>
            </div>
            <p className="mt-3 text-sm text-slate-300">{check.detail}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
