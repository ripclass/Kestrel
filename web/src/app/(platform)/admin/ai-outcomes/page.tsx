import { PageFrame } from "@/components/common/page-frame";
import { AIOutcomesDashboard } from "@/components/admin/ai-outcomes-dashboard";
import { requireRole } from "@/lib/auth";

export default async function AIOutcomesPage() {
  await requireRole("admin", "superadmin", "manager", "analyst");
  return (
    <PageFrame
      eyebrow="Admin · AI outcomes"
      title="AI training corpus"
      description="Every AI call writes one row to ai_outcome_log. The V3 sovereign-AI track will fine-tune a Bangladesh-trained model on the analyst corrections captured here. Per-task accuracy proxy is the correction rate; lower is better."
    >
      <AIOutcomesDashboard />
    </PageFrame>
  );
}
