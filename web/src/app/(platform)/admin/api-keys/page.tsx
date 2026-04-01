import { PageFrame } from "@/components/common/page-frame";
import { DataTable } from "@/components/common/data-table";
import { apiKeys } from "@/lib/demo";

export default function ApiKeysPage() {
  return (
    <PageFrame
      eyebrow="Administration"
      title="API access"
      description="Manage service integrations and scoped credentials for downstream systems."
    >
      <DataTable
        columns={["Name", "Last used", "Scopes"]}
        rows={apiKeys.map((key) => [key.name, key.lastUsedAt, key.scope.join(", ")])}
      />
    </PageFrame>
  );
}
