import { RuleCatalogManager } from "@/components/admin/rule-catalog-manager";
import { PageFrame } from "@/components/common/page-frame";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { fetchAdminRules } from "@/lib/admin";
import { requireRole } from "@/lib/auth";

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
        <RuleCatalogManager initialRules={rules} />
      )}
    </PageFrame>
  );
}
