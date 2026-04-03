import { AlertTicker } from "@/components/overview/alert-ticker";
import { KpiCard } from "@/components/overview/kpi-card";
import { AlertQueue } from "@/components/alerts/alert-queue";
import { CaseBoard } from "@/components/cases/case-board";
import type { KpiStat } from "@/types/domain";

const stats: KpiStat[] = [
  { label: "Open priority alerts", value: "18", delta: "6 critical", detail: "triage within today" },
  { label: "Cross-bank matches", value: "7", delta: "+2 overnight", detail: "new overlaps ready for validation" },
  { label: "Cases in motion", value: "4", delta: "1 escalated", detail: "shared evidence workspace active" },
];

export function AnalystView() {
  return (
    <div className="space-y-6">
      <AlertTicker />
      <div className="grid gap-4 xl:grid-cols-3">
        {stats.map((stat) => (
          <KpiCard key={stat.label} stat={stat} />
        ))}
      </div>
      <div className="grid gap-6 xl:grid-cols-[1.3fr_0.9fr]">
        <AlertQueue alertsToShow={3} />
        <CaseBoard title="Recent cases" casesToShow={3} />
      </div>
    </div>
  );
}
