import Link from "next/link";

import { Currency } from "@/components/common/currency";
import { RiskScore } from "@/components/common/risk-score";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import type { FlaggedAccount } from "@/types/domain";

export function FlaggedAccountCard({ account }: { account: FlaggedAccount }) {
  return (
    <Card>
      <CardContent className="space-y-4 p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div className="space-y-1">
            <p className="font-medium">{account.accountName}</p>
            <p className="font-mono text-sm text-muted-foreground">{account.accountNumber}</p>
          </div>
          <RiskScore score={account.score} severity={account.severity} />
        </div>
        <p className="text-sm text-muted-foreground">{account.summary}</p>
        <div className="flex flex-wrap gap-2">
          <Badge>{account.matchedBanks} banks</Badge>
          <Badge>Exposure <Currency amount={account.totalExposure} /></Badge>
          {account.tags.slice(0, 3).map((tag) => (
            <Badge key={tag}>{tag.replaceAll("_", " ")}</Badge>
          ))}
        </div>
        <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
          <Link href={`/investigate/entity/${account.entityId}`} className="text-primary transition hover:opacity-80">
            Open entity
          </Link>
          {account.linkedAlertId ? (
            <Link href={`/alerts/${account.linkedAlertId}`} className="text-primary transition hover:opacity-80">
              Open alert
            </Link>
          ) : null}
          {account.linkedCaseId ? (
            <Link href={`/cases/${account.linkedCaseId}`} className="text-primary transition hover:opacity-80">
              Open case
            </Link>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
