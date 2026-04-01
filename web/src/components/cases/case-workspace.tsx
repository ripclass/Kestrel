import { CaseTimeline } from "@/components/cases/case-timeline";
import { CaseNotes } from "@/components/cases/case-notes";
import { CaseEvidence } from "@/components/cases/case-evidence";
import { CaseExport } from "@/components/cases/case-export";

export function CaseWorkspace() {
  return (
    <div className="space-y-6">
      <CaseExport />
      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <CaseTimeline />
        <CaseNotes />
      </div>
      <CaseEvidence />
    </div>
  );
}
