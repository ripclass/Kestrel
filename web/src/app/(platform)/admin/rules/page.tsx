import { PageFrame } from "@/components/common/page-frame";
import { DataTable } from "@/components/common/data-table";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { fetchAdminRules } from "@/lib/admin";
import { requireRole } from "@/lib/auth";
import { Badge } from "@/components/ui/badge";

export default async function RulesPage() {
  await requireRole("manager", "admin", "superadmin");
  let errorMessage: string | null = null;
  let rules: Awaited<ReturnType<typeof fetchAdminRules>> = [];

  try {
    rules = await fetchAdminRules();
  } catch (error) {
    errorMessage = error instanceof Error ? error.message : "Unable to load rule definitions.";
  }

  return (
    <PageFrame
      eyebrow="Administration"
      title="Detection rules"
      description="Configure YAML-backed rules, weights, and institution-specific overlays."
    >
      {errorMessage ? (
        <ErrorState title="Rule catalog unavailable" description={errorMessage} />
      ) : rules.length === 0 ? (
        <EmptyState
          title="No rule catalog available"
          description="Rules will appear here once the system registry or organization overlays are available."
        />
      ) : (
        <DataTable
          columns={["Rule", "Category", "Source", "Weight", "Threshold", "Status"]}
          rows={rules.map((rule) => [
            <div key={`${rule.code}-name`} className="space-y-1">
              <p className="font-medium text-foreground">{rule.name}</p>
              <p className="text-xs text-muted-foreground">{rule.code}</p>
              <p className="text-xs text-muted-foreground">{rule.description}</p>
            </div>,
            rule.category,
            <Badge key={`${rule.code}-source`} className={rule.isSystem ? "" : "border-primary/30 bg-primary/15 text-primary"}>
              {rule.source}
            </Badge>,
            rule.weight.toFixed(2),
            rule.threshold ? `${rule.threshold}` : "Inherited",
            <Badge
              key={`${rule.code}-status`}
              className={
                rule.isActive
                  ? "border-emerald-400/30 bg-emerald-500/15 text-emerald-100"
                  : "border-slate-400/30 bg-slate-500/15 text-slate-200"
              }
            >
              {rule.isActive ? `live v${rule.version}` : `inactive v${rule.version}`}
            </Badge>,
          ])}
        />
      )}
    </PageFrame>
  );
}
