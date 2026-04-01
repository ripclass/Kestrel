import Link from "next/link";

import { SeverityPill } from "@/components/common/severity-pill";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { EntitySummary } from "@/types/domain";

export function EntityConnections({ entities }: { entities: EntitySummary[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Connected entities</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {entities.map((entity) => (
          <Link
            key={entity.id}
            href={`/investigate/entity/${entity.id}`}
            className="flex items-center justify-between rounded-xl border border-border/70 bg-background/40 px-4 py-3"
          >
            <div>
              <p className="font-medium">{entity.displayValue}</p>
              <p className="text-sm text-muted-foreground">{entity.displayName}</p>
            </div>
            <SeverityPill severity={entity.severity} />
          </Link>
        ))}
      </CardContent>
    </Card>
  );
}
