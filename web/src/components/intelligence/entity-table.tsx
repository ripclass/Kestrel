import Link from "next/link";

import { DataTable } from "@/components/common/data-table";
import { RiskScore } from "@/components/common/risk-score";
import { entities } from "@/lib/demo";

export function EntityTable() {
  return (
    <DataTable
      columns={["Entity", "Type", "Reporting orgs", "Risk"]}
      rows={entities.map((entity) => [
        <Link key={entity.id} href={`/investigate/entity/${entity.id}`} className="font-medium text-primary">
          {entity.displayValue}
        </Link>,
        entity.entityType,
        entity.reportingOrgs.join(", "),
        <RiskScore key={`${entity.id}-risk`} score={entity.riskScore} severity={entity.severity} />,
      ])}
    />
  );
}
