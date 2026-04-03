import { PageFrame } from "@/components/common/page-frame";
import { DataTable } from "@/components/common/data-table";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { fetchAdminIntegrations } from "@/lib/admin";
import { requireRole } from "@/lib/auth";
import { Badge } from "@/components/ui/badge";

export default async function ApiKeysPage() {
  await requireRole("manager", "admin", "superadmin");
  let errorMessage: string | null = null;
  let integrations: Awaited<ReturnType<typeof fetchAdminIntegrations>> = [];

  try {
    integrations = await fetchAdminIntegrations();
  } catch (error) {
    errorMessage = error instanceof Error ? error.message : "Unable to load integration status.";
  }

  return (
    <PageFrame
      eyebrow="Administration"
      title="API access"
      description="Manage service integrations and scoped credentials for downstream systems."
    >
      {errorMessage ? (
        <ErrorState title="Integration posture unavailable" description={errorMessage} />
      ) : integrations.length === 0 ? (
        <EmptyState
          title="No integrations available"
          description="Integration posture will appear here once runtime services are configured."
        />
      ) : (
        <DataTable
          columns={["Integration", "Status", "Last observed", "Scopes"]}
          rows={integrations.map((integration) => [
            <div key={`${integration.id}-name`} className="space-y-1">
              <p className="font-medium text-foreground">{integration.name}</p>
              <p className="text-xs text-muted-foreground">{integration.detail}</p>
            </div>,
            <Badge
              key={`${integration.id}-status`}
              className={
                integration.status === "active" || integration.status === "available"
                  ? "border-emerald-400/30 bg-emerald-500/15 text-emerald-100"
                  : "border-amber-400/30 bg-amber-500/15 text-amber-100"
              }
            >
              {integration.status}
            </Badge>,
            integration.lastUsedAt ? new Date(integration.lastUsedAt).toLocaleString() : "Not observed",
            integration.scope.join(", "),
          ])}
        />
      )}
    </PageFrame>
  );
}
